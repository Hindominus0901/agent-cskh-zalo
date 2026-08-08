"""Bo dem han muc Zalo — rang buoc lon nhat cua he thong.

Goi Basic: 3.000 tin/thang, 50 nguoi dung/bot. Dem CA HAI CHIEU cho an toan
vi tai lieu Zalo khong noi ro chieu nao duoc tinh.

Nguong:
  80%  -> canh bao chu bot mot lan
  95%  -> chi phuc vu staff/owner; khach la nhan cau xin loi tinh
  100% -> dung han
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from agent_cskh.config import Settings
from agent_cskh.logging_setup import get_logger
from agent_cskh.store import Database

log = get_logger(__name__)

MSG_HET_QUOTA = (
    "Dạ em xin lỗi, hệ thống đang tạm quá tải. Anh/chị vui lòng nhắn lại sau ít phút giúp em ạ."
)


def _period() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m")


@dataclass(frozen=True, slots=True)
class QuotaStatus:
    used: int
    limit: int
    period: str

    @property
    def pct(self) -> float:
        return 100.0 * self.used / self.limit if self.limit else 0.0

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)


class QuotaGuard:
    def __init__(self, settings: Settings, db: Database) -> None:
        self._s = settings
        self._db = db
        self._limit = settings.zalo_monthly_quota

    async def _ensure_row(self, period: str) -> None:
        await self._db.execute(
            "INSERT OR IGNORE INTO zalo_quota (period, sent, received) VALUES (?, 0, 0)",
            (period,),
        )

    async def count_sent(self, n: int = 1) -> None:
        """CHI duoc goi tu ZaloClient qua callback `on_sent`. Khong goi o noi khac.

        Moi tin di deu qua ZaloClient, ke ca nhung duong ta quen — nen do la cho
        dem duy nhat dung. Ngay 07/08/2026 phat hien bo dem doc gap ~2 lan thuc
        te (sent=29 trong khi chi gui 13 tin) vi bon noi goi tu dem them mot lan.
        Hau qua: phanh quota 80% dap o ~40% that, va moi phep tinh ngan sach gui
        chu dong sai mot nua.
        """
        period = _period()
        await self._ensure_row(period)
        await self._db.execute(
            "UPDATE zalo_quota SET sent = sent + ? WHERE period = ?", (n, period)
        )

    async def count_received(self, n: int = 1) -> None:
        period = _period()
        await self._ensure_row(period)
        await self._db.execute(
            "UPDATE zalo_quota SET received = received + ? WHERE period = ?", (n, period)
        )

    async def status(self) -> QuotaStatus:
        period = _period()
        row = await self._db.fetch_one(
            "SELECT sent, received FROM zalo_quota WHERE period = ?", (period,)
        )
        used = (row["sent"] + row["received"]) if row else 0
        return QuotaStatus(used=used, limit=self._limit, period=period)

    async def allows(self, *, is_internal: bool) -> bool:
        """False -> tu choi mem luot nay."""
        st = await self.status()
        if st.pct >= 100:
            log.error("het_quota_thang", used=st.used, limit=st.limit)
            return False
        if st.pct >= self._s.quota_hard_pct and not is_internal:
            log.warning("quota_gan_het_chi_phuc_vu_noi_bo", pct=round(st.pct, 1))
            return False
        return True

    async def should_warn_owner(self) -> QuotaStatus | None:
        """Tra ve status neu vua vuot nguong canh bao va chua canh bao thang nay."""
        st = await self.status()
        if st.pct < self._s.quota_warn_pct:
            return None
        row = await self._db.fetch_one(
            "SELECT warned_at FROM zalo_quota WHERE period = ?", (st.period,)
        )
        if row and row["warned_at"]:
            return None
        await self._db.execute(
            "UPDATE zalo_quota SET warned_at = ? WHERE period = ?",
            (datetime.now(tz=UTC).isoformat(), st.period),
        )
        return st
