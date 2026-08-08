"""Doc/ghi hoi thoai: dedup, phien, lich su tin nhan, trang thai handoff."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from agent_cskh.logging_setup import get_logger
from agent_cskh.store import Database
from agent_cskh.transport.base import InboundEvent

log = get_logger(__name__)

ConvState = Literal["BOT", "HUMAN_PENDING", "HUMAN_ACTIVE"]

# Khong hoat dong qua nguong nay thi coi la phien moi.
SESSION_IDLE = timedelta(minutes=30)
# Giu ban ghi dedup bao lau. Zalo khong replay nen khong can giu lau.
PROCESSED_TTL_DAYS = 7


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class StoredMessage:
    direction: Literal["in", "out"]
    kind: str
    text: str | None
    created_at: str


class ChatRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    # ---------- idempotency ----------
    async def already_processed(self, message_id: str) -> bool:
        row = await self._db.fetch_one(
            "SELECT 1 FROM processed_updates WHERE message_id = ?", (message_id,)
        )
        return row is not None

    async def mark_processed(self, message_id: str, chat_id: str) -> None:
        await self._db.execute(
            "INSERT OR IGNORE INTO processed_updates (message_id, chat_id, processed_at) "
            "VALUES (?, ?, ?)",
            (message_id, chat_id, _now().isoformat()),
        )

    async def prune_processed(self) -> int:
        cutoff = (_now() - timedelta(days=PROCESSED_TTL_DAYS)).isoformat()
        return await self._db.execute(
            "DELETE FROM processed_updates WHERE processed_at < ?", (cutoff,)
        )

    # ---------- hoi thoai & phien ----------
    async def ensure_conversation(self, event: InboundEvent) -> str:
        """Tao hoi thoai neu chua co, tra ve session_id hien hanh."""
        now = _now()
        row = await self._db.fetch_one(
            "SELECT session_id, last_event_at FROM conversations WHERE chat_id = ?",
            (event.chat_id,),
        )

        if row is None:
            session_id = uuid.uuid4().hex[:16]
            await self._db.execute(
                "INSERT INTO conversations "
                "(chat_id, chat_type, session_id, state, last_event_at, created_at) "
                "VALUES (?, ?, ?, 'BOT', ?, ?)",
                (event.chat_id, event.chat_type, session_id, now.isoformat(), now.isoformat()),
            )
            return session_id

        session_id = row["session_id"] or uuid.uuid4().hex[:16]
        try:
            last = datetime.fromisoformat(row["last_event_at"]) if row["last_event_at"] else None
        except (TypeError, ValueError):
            last = None
        if last is None or (now - last) > SESSION_IDLE:
            session_id = uuid.uuid4().hex[:16]
            log.info("phien_moi", chat_id=event.chat_id[:8], session_id=session_id)

        await self._db.execute(
            "UPDATE conversations SET session_id = ?, last_event_at = ?, chat_type = ? "
            "WHERE chat_id = ?",
            (session_id, now.isoformat(), event.chat_type, event.chat_id),
        )
        return session_id

    async def get_state(self, chat_id: str) -> ConvState:
        row = await self._db.fetch_one(
            "SELECT state FROM conversations WHERE chat_id = ?", (chat_id,)
        )
        return row["state"] if row else "BOT"  # type: ignore[return-value]

    async def set_state(self, chat_id: str, state: ConvState) -> None:
        await self._db.execute(
            "UPDATE conversations SET state = ? WHERE chat_id = ?", (state, chat_id)
        )

    # ---------- tin nhan ----------
    async def save_inbound(self, event: InboundEvent, session_id: str) -> None:
        await self._db.execute(
            "INSERT INTO messages "
            "(chat_id, message_id, session_id, user_id, direction, kind, text, media_url, "
            " raw_json, created_at) "
            "VALUES (?, ?, ?, ?, 'in', ?, ?, ?, ?, ?)",
            (
                event.chat_id,
                event.event_id,
                session_id,
                event.user_id,
                event.kind,
                event.text,
                event.photo.url if event.photo else event.voice_url,
                json.dumps(event.raw, ensure_ascii=False),
                _now().isoformat(),
            ),
        )

    async def save_outbound(
        self, chat_id: str, session_id: str, text: str, *, kind: str = "text"
    ) -> None:
        await self._db.execute(
            "INSERT INTO messages (chat_id, session_id, direction, kind, text, created_at) "
            "VALUES (?, ?, 'out', ?, ?, ?)",
            (chat_id, session_id, kind, text, _now().isoformat()),
        )

    async def recent(self, chat_id: str, limit: int = 12) -> list[StoredMessage]:
        """N tin gan nhat, thu tu cu -> moi."""
        rows = await self._db.fetch_all(
            "SELECT direction, kind, text, created_at FROM messages "
            "WHERE chat_id = ? AND text IS NOT NULL "
            "ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        )
        return [
            StoredMessage(
                direction=r["direction"], kind=r["kind"], text=r["text"], created_at=r["created_at"]
            )
            for r in reversed(rows)
        ]

    async def anh_gan_nhat(self, chat_id: str, *, trong_so_tin: int = 12) -> str | None:
        """Duong dan anh HOC VIEN vua gui gan day nhat. None neu khong co.

        Cung rang buoc voi URL trong cham_bai: anh phai THAT SU do chinh nguoi
        nay gui trong cuoc tro chuyen nay. Model khong duoc chon dia chi anh —
        no chi noi "cham anh vua gui", con anh nao thi ham nay quyet.
        """
        row = await self._db.fetch_one(
            "SELECT media_url FROM messages WHERE id IN ("
            "  SELECT id FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?) "
            "  AND direction = 'in' AND kind = 'photo' AND media_url IS NOT NULL "
            "ORDER BY id DESC LIMIT 1",
            (chat_id, trong_so_tin),
        )
        return str(row["media_url"]) if row else None

    async def reset_session(self, chat_id: str) -> None:
        """Bat dau phien moi ngay lap tuc — dung khi test hoac khi khach doi chu de."""
        await self._db.execute(
            "UPDATE conversations SET session_id = ?, last_event_at = ? WHERE chat_id = ?",
            (uuid.uuid4().hex[:16], _now().isoformat(), chat_id),
        )

    # ---------- ban giao nguoi that ----------
    async def open_handoff(self, chat_id: str, *, reason: str, summary: str) -> int:
        """Mo mot yeu cau ban giao. Neu dang co yeu cau mo thi cap nhat, khong tao trung."""
        now = _now().isoformat()
        row = await self._db.fetch_one(
            "SELECT id FROM handoffs WHERE chat_id = ? AND status = 'pending' "
            "ORDER BY id DESC LIMIT 1",
            (chat_id,),
        )
        if row is not None:
            await self._db.execute(
                "UPDATE handoffs SET reason = ?, summary = ?, requested_at = ? WHERE id = ?",
                (reason, summary, now, row["id"]),
            )
            return int(row["id"])
        return await self._db.execute(
            "INSERT INTO handoffs (chat_id, reason, summary, requested_at, status) "
            "VALUES (?, ?, ?, ?, 'pending')",
            (chat_id, reason, summary, now),
        )

    async def pending_handoffs(self, limit: int = 20) -> list[dict[str, str]]:
        rows = await self._db.fetch_all(
            "SELECT chat_id, reason, summary, requested_at, so_lan_nhac, nhac_cuoi_luc "
            "FROM handoffs WHERE status = 'pending' ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    async def ghi_da_nhac_handoff(self, chat_id: str) -> int:
        """Tang bo dem nhac cua yeu cau dang treo. Tra ve so lan sau khi tang.

        Dem trong CSDL chu khong trong bo nho: mot bo dem chet theo tien trinh
        se lam moi lan khoi dong lai sinh ra mot canh bao nua ngay lap tuc — va
        trong mot ngay sua nhieu thi bot khoi dong lai vai lan.
        """
        await self._db.execute(
            "UPDATE handoffs SET so_lan_nhac = so_lan_nhac + 1, nhac_cuoi_luc = ? "
            "WHERE chat_id = ? AND status = 'pending'",
            (_now().isoformat(), chat_id),
        )
        return int(
            await self._db.fetch_val(
                "SELECT so_lan_nhac FROM handoffs WHERE chat_id = ? AND status = 'pending' "
                "ORDER BY id DESC LIMIT 1",
                (chat_id,),
                0,
            )
        )

    async def dong_handoff_qua_han(self, ngay: int = 7) -> int:
        """Dong cac yeu cau treo qua lau. Tra ve so dong da dong.

        Khong phai don dep cho gon: `/baocao` va bang theo doi deu dem "khach
        dang cho nguoi", va mot xac chet ba tuan tuoi nam trong con so do lam
        ca con so mat nghia.
        """
        moc = (_now() - timedelta(days=ngay)).isoformat()
        return await self._db.execute_rowcount(
            "UPDATE handoffs SET status = 'released', released_by = 'het_han', released_at = ? "
            "WHERE status = 'pending' AND requested_at < ?",
            (_now().isoformat(), moc),
        )

    async def claim_handoff(self, chat_id: str, user_id: str, *, reason: str = "thu_cong") -> None:
        now = _now().isoformat()
        row = await self._db.fetch_one(
            "SELECT id FROM handoffs WHERE chat_id = ? AND status != 'released' "
            "ORDER BY id DESC LIMIT 1",
            (chat_id,),
        )
        if row is None:
            await self._db.execute(
                "INSERT INTO handoffs "
                "(chat_id, reason, summary, requested_at, claimed_by, claimed_at, status) "
                "VALUES (?, ?, '', ?, ?, ?, 'active')",
                (chat_id, reason, now, user_id, now),
            )
        else:
            await self._db.execute(
                "UPDATE handoffs SET claimed_by = ?, claimed_at = ?, status = 'active' "
                "WHERE id = ?",
                (user_id, now, row["id"]),
            )

    async def release_handoff(self, chat_id: str, user_id: str) -> None:
        now = _now().isoformat()
        await self._db.execute(
            "UPDATE handoffs SET released_by = ?, released_at = ?, status = 'released' "
            "WHERE chat_id = ? AND status != 'released'",
            (user_id, now, chat_id),
        )

    # ---------- anh chuyen khoan ----------
    async def save_payment_claim(
        self,
        *,
        chat_id: str,
        user_id: str,
        media_url: str | None,
        amount: int | None,
        txn_time: str | None,
        memo: str | None,
        bank: str | None,
        acct_last4: str | None,
    ) -> int:
        """Ghi nhan mot anh chuyen khoan. Luon o trang thai cho doi soat.

        KHONG co ham nao trong codebase ghi vao verified_by / verified_at —
        chi nguoi that dien duoc, va do la co y.
        """
        return await self._db.execute(
            "INSERT INTO payment_claims "
            "(chat_id, user_id, media_url, amount, txn_time, memo, bank, acct_last4, "
            " status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'cho_doi_soat', ?)",
            (
                chat_id,
                user_id,
                media_url,
                amount,
                txn_time,
                memo,
                bank,
                acct_last4,
                _now().isoformat(),
            ),
        )

    async def set_payment_media_path(self, claim_id: int, path: str) -> None:
        await self._db.execute(
            "UPDATE payment_claims SET media_path = ? WHERE id = ?", (path, claim_id)
        )

    async def pending_payment_claims(self, limit: int = 20) -> list[dict[str, str]]:
        rows = await self._db.fetch_all(
            "SELECT id, chat_id, amount, txn_time, memo, media_path, created_at "
            "FROM payment_claims WHERE status = 'cho_doi_soat' ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    # ---------- lead ----------
    async def upsert_lead(
        self,
        *,
        user_id: str,
        chat_id: str,
        name: str | None,
        phone: str | None,
        email: str | None,
        service: str | None,
        budget: str | None,
        stage: str,
    ) -> bool:
        """Tao hoac cap nhat lead cua chinh cuoc tro chuyen nay. True = tao moi.

        Chi ghi de truong nao co gia tri moi — khong xoa thong tin da co bang None.
        """
        now = _now().isoformat()
        row = await self._db.fetch_one(
            "SELECT id FROM leads WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
        )
        if row is None:
            await self._db.execute(
                "INSERT INTO leads "
                "(user_id, chat_id, name, phone, email, service, budget, stage, "
                " created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, chat_id, name, phone, email, service, budget, stage, now, now),
            )
            return True

        await self._db.execute(
            "UPDATE leads SET "
            "  name = COALESCE(?, name), phone = COALESCE(?, phone), "
            "  email = COALESCE(?, email), service = COALESCE(?, service), "
            "  budget = COALESCE(?, budget), stage = ?, updated_at = ? "
            "WHERE id = ?",
            (name, phone, email, service, budget, stage, now, row["id"]),
        )
        return False

    async def recent_leads(self, limit: int = 10) -> list[dict[str, str]]:
        rows = await self._db.fetch_all(
            "SELECT name, phone, email, service, budget, stage, updated_at FROM leads "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    async def count_leads(self, since_iso: str | None = None) -> int:
        if since_iso:
            return int(
                await self._db.fetch_val(
                    "SELECT count(*) FROM leads WHERE created_at >= ?", (since_iso,), 0
                )
            )
        return int(await self._db.fetch_val("SELECT count(*) FROM leads", (), 0))

    # ---------- cau hoi bot khong tra loi duoc ----------
    async def ghi_thieu_trang(
        self, *, chat_id: str, user_id: str, cau_hoi: str, chu_de: str | None
    ) -> int:
        """Ghi mot cau hoi ma kho tri thuc chua co cau tra loi.

        Khong gop trung o day: hai nguoi hoi cung mot y bang hai cach noi khac
        nhau la HAI du kien — chung cho biet cau hoi do pho bien. Viec gom nhom
        de bao cao lo, va no gom de doc chu khong xoa mat.
        """
        return await self._db.execute(
            "INSERT INTO thieu_trang (chat_id, user_id, cau_hoi, chu_de, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (chat_id, user_id, cau_hoi[:500], chu_de, _now().isoformat()),
        )

    async def thieu_trang_gan_day(self, *, ngay: int = 1, limit: int = 30) -> list[dict]:
        """Cac cau chua duoc bo sung trang, moi nhat truoc."""
        moc = (_now() - timedelta(days=ngay)).isoformat()
        rows = await self._db.fetch_all(
            "SELECT cau_hoi, chu_de, chat_id, created_at FROM thieu_trang "
            "WHERE da_xu_ly = 0 AND created_at >= ? ORDER BY id DESC LIMIT ?",
            (moc, limit),
        )
        return [dict(r) for r in rows]

    async def danh_dau_da_bo_sung(self, chu_de: str) -> int:
        return await self._db.execute_rowcount(
            "UPDATE thieu_trang SET da_xu_ly = 1 WHERE da_xu_ly = 0 AND chu_de = ?", (chu_de,)
        )

    # ---------- chi phi model ----------
    async def ghi_chi_phi(
        self,
        *,
        chat_id: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read: int,
        cost_usd: float,
    ) -> None:
        """Ghi chi phi mot lan goi model.

        Bang `llm_usage` co so do tu migration 001 nhung KHONG dong code nao ghi
        vao — phat hien 08/08/2026. Hau qua: `DAILY_COST_LIMIT_USD` trong config
        va ca duong `daily_cost_exceeded -> router tra ve model re` deu la may
        moc day du nhung khong bao gio chay, vi khong ai biet hom nay da tieu
        bao nhieu.

        Mot tran chi tieu khong duoc thuc thi con te hon khong co tran: nguoi ta
        doc config, thay so 5 USD, va yen tam.
        """
        await self._db.execute(
            "INSERT INTO llm_usage "
            "(chat_id, provider, model, input_tokens, output_tokens, cache_read_tokens, "
            " cost_usd, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                chat_id,
                provider,
                model,
                input_tokens,
                output_tokens,
                cache_read,
                cost_usd,
                _now().isoformat(),
            ),
        )

    async def chi_phi_hom_nay(self) -> float:
        """Tong chi phi model tu 00:00 hom nay, theo gio UTC."""
        dau_ngay = _now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        return float(
            await self._db.fetch_val(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_usage WHERE created_at >= ?",
                (dau_ngay,),
                0.0,
            )
            or 0.0
        )

    async def log_tool_call(
        self,
        *,
        chat_id: str,
        user_id: str,
        tool_name: str,
        args_json: str,
        ok: bool,
        error: str | None,
        duration_ms: int,
    ) -> None:
        """Nhat ky moi lan goi cong cu — bang chung khi can truy lai bot da lam gi."""
        await self._db.execute(
            "INSERT INTO tool_audit "
            "(chat_id, user_id, tool_name, args_json, ok, error, duration_ms, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                chat_id,
                user_id,
                tool_name,
                args_json,
                int(ok),
                error,
                duration_ms,
                _now().isoformat(),
            ),
        )

    async def upsert_principal_seen(self, user_id: str, display_name: str | None) -> None:
        """Ghi nhan da gap nguoi nay. Khong nang quyen — mac dinh van la stranger."""
        now = _now().isoformat()
        await self._db.execute(
            "INSERT INTO principals (user_id, display_name, role, created_at, updated_at) "
            "VALUES (?, ?, 'stranger', ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "  display_name = COALESCE(excluded.display_name, principals.display_name), "
            "  updated_at = excluded.updated_at",
            (user_id, display_name, now, now),
        )
