"""Token bucket theo user_id, luu trong SQLite de song sot qua restart."""

from __future__ import annotations

from datetime import UTC, datetime

from agent_cskh.config import Settings
from agent_cskh.logging_setup import get_logger
from agent_cskh.store import Database

log = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(tz=UTC)


class RateLimiter:
    def __init__(self, settings: Settings, db: Database) -> None:
        self._db = db
        self._capacity = float(settings.rate_limit_per_min)
        self._refill_per_sec = self._capacity / 60.0

    async def allow(self, user_id: str, *, cost: float = 1.0) -> bool:
        """True neu duoc phep. Owner/staff van bi gioi han — chong vong lap vo tan."""
        now = _now()
        row = await self._db.fetch_one(
            "SELECT tokens, updated_at FROM rate_limits WHERE user_id = ?", (user_id,)
        )

        if row is None:
            tokens = self._capacity
        else:
            try:
                last = datetime.fromisoformat(row["updated_at"])
            except (TypeError, ValueError):
                last = now
            elapsed = max(0.0, (now - last).total_seconds())
            tokens = min(self._capacity, float(row["tokens"]) + elapsed * self._refill_per_sec)

        if tokens < cost:
            await self._save(user_id, tokens, now)
            log.info("vuot_rate_limit", user_id=user_id[:8], tokens=round(tokens, 2))
            return False

        await self._save(user_id, tokens - cost, now)
        return True

    async def _save(self, user_id: str, tokens: float, now: datetime) -> None:
        await self._db.execute(
            "INSERT INTO rate_limits (user_id, tokens, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET tokens = excluded.tokens, "
            "updated_at = excluded.updated_at",
            (user_id, tokens, now.isoformat()),
        )
