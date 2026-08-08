"""Lop SQLite. Mot ket noi, mot writer, WAL.

SQLite khong thich ghi dong thoi — moi lenh ghi di qua mot asyncio.Lock.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import aiosqlite

from agent_cskh.config import Settings
from agent_cskh.logging_setup import get_logger

log = get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_MIGRATION_RE = re.compile(r"^(\d{3})_.+\.sql$")

PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA busy_timeout=5000",
    "PRAGMA foreign_keys=ON",
)


class Database:
    """Bao aiosqlite. Dung nhu async context manager, hoac goi connect()/close()."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._conn: aiosqlite.Connection | None = None
        self._write_lock: Any = None  # asyncio.Lock, tao lazy trong connect()

    # ---------- vong doi ----------
    async def connect(self) -> None:
        import asyncio

        if self._conn is not None:
            return
        self._settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = asyncio.Lock()
        self._conn = await aiosqlite.connect(self._settings.db_path)
        self._conn.row_factory = aiosqlite.Row
        for pragma in PRAGMAS:
            await self._conn.execute(pragma)
        await self._conn.commit()
        await self.migrate()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self) -> Database:
        await self.connect()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database chua connect() — goi await db.connect() truoc")
        return self._conn

    # ---------- migration ----------
    async def migrate(self) -> list[str]:
        """Chay cac file .sql chua ap dung, theo thu tu so hieu. Tra ve danh sach da chay."""
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "  version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        await self.conn.commit()

        cur = await self.conn.execute("SELECT version FROM schema_migrations")
        applied = {r["version"] for r in await cur.fetchall()}

        files = sorted(f for f in MIGRATIONS_DIR.glob("*.sql") if _MIGRATION_RE.match(f.name))
        ran: list[str] = []
        for path in files:
            version = path.name
            if version in applied:
                continue
            sql = path.read_text(encoding="utf-8")
            await self.conn.executescript(sql)
            await self.conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, datetime('now'))",
                (version,),
            )
            await self.conn.commit()
            ran.append(version)
            log.info("migration_applied", version=version)
        return ran

    # ---------- doc ----------
    async def fetch_one(self, sql: str, params: Sequence[Any] = ()) -> aiosqlite.Row | None:
        cur = await self.conn.execute(sql, params)
        return await cur.fetchone()

    async def fetch_all(self, sql: str, params: Sequence[Any] = ()) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(sql, params)
        return list(await cur.fetchall())

    async def fetch_val(self, sql: str, params: Sequence[Any] = (), default: Any = None) -> Any:
        row = await self.fetch_one(sql, params)
        return row[0] if row is not None else default

    # ---------- ghi (qua lock) ----------
    async def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        """Tra ve lastrowid."""
        async with self._write_lock:
            cur = await self.conn.execute(sql, params)
            await self.conn.commit()
            return cur.lastrowid or 0

    async def execute_rowcount(self, sql: str, params: Sequence[Any] = ()) -> int:
        """Nhu execute() nhung tra ve SO DONG bi anh huong.

        Ton tai rieng vi `execute()` tra `lastrowid` — voi UPDATE/DELETE thi gia
        tri do vo nghia, va dung nham no se ra mot con so trong ma nhin qua van
        hop ly. Ham nay lam y dinh ro rang ngay tai cho goi.
        """
        async with self._write_lock:
            cur = await self.conn.execute(sql, params)
            await self.conn.commit()
            return cur.rowcount

    async def execute_many(self, sql: str, rows: Iterable[Sequence[Any]]) -> None:
        async with self._write_lock:
            await self.conn.executemany(sql, rows)
            await self.conn.commit()

    async def health(self) -> dict[str, Any]:
        return {
            "path": str(self._settings.db_path),
            "journal_mode": await self.fetch_val("PRAGMA journal_mode"),
            "foreign_keys": await self.fetch_val("PRAGMA foreign_keys"),
            "tables": await self.fetch_val("SELECT count(*) FROM sqlite_master WHERE type='table'"),
        }
