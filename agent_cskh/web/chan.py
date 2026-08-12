"""Chan lam dung cho kenh web.

VI SAO KENH WEB CAN LOP RIENG, khong dung lai `security/ratelimit.py`:

`RateLimiter` khoa theo `user_id`. Tren Zalo dieu do vung chac — user_id do Zalo
cap, khach khong tu doi duoc. Tren web, "user_id" chi la mot cookie ta tu phat:
KHACH XOA COOKIE LA CO ID MOI. Nen mot minh no khong chan duoc ai co y pha.

Hai lop o day danh cho dung mot moi lo: o che do `ai`, moi luot chat la tien
that chay ra khoi tai khoan chu shop. Website mo thang ra internet, khong dang
nhap, nen mot con bot cao chay ca dem co the dot sach so du truoc khi ai kip
biet.

    Lop 1 — `NhipIP`:   chan tang suat, theo dia chi IP (khong xoa duoc nhu cookie)
    Lop 2 — `TranNgay`: chan TONG so luot ca site moi ngay — tran cung cuoi cung

Lop 2 moi la thu thuc su cuu tien. Lop 1 chi lam cham ke pha; ai co san mot dan
IP thi van vuot qua duoc, va luc do chi con tran ngay dung lai.

Tinh theo NGAY chu khong theo thang: bi cao thi thiet hai dung lai sau mot ngay,
chu khong keo dai ca thang.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from agent_cskh.config import Settings
from agent_cskh.logging_setup import get_logger
from agent_cskh.store import Database

log = get_logger(__name__)

# Cau tu choi. Noi that la dang ban, KHONG noi "ban da bi chan" — khach that vo
# tinh cham tran (vd ca van phong dung chung mot IP) khong dang bi doi xu nhu ke pha.
MSG_QUA_NHANH = (
    "Dạ anh/chị nhắn nhanh quá, em chưa theo kịp ạ. "
    "Anh/chị chờ em một chút rồi nhắn lại giúp em nhé."
)
MSG_QUA_TAI = (
    "Dạ hôm nay bên em đang quá tải nên trợ lý tạm nghỉ ạ. "
    "Anh/chị để lại số điện thoại hoặc nhắn qua Zalo giúp em, bên em gọi lại ngay ạ."
)


def _hom_nay() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


class NhipIP:
    """Gau token theo IP, giu trong RAM.

    Khong luu xuong CSDL: khoi dong lai may chu la reset sach — chap nhan duoc,
    vi lop that su chan thiet hai la `TranNgay` (co luu). Doi lai, moi luot chat
    khong phai ganh them mot vong ghi dia.
    """

    def __init__(self, moi_phut: int) -> None:
        self._suc_chua = float(moi_phut)
        self._hoi_moi_giay = self._suc_chua / 60.0
        self._gau: dict[str, tuple[float, float]] = {}
        self._khoa = asyncio.Lock()

    async def cho_phep(self, ip: str) -> bool:
        moc = datetime.now(tz=UTC).timestamp()
        async with self._khoa:
            token, truoc = self._gau.get(ip, (self._suc_chua, moc))
            token = min(self._suc_chua, token + max(0.0, moc - truoc) * self._hoi_moi_giay)
            if token < 1.0:
                self._gau[ip] = (token, moc)
                log.info("web_vuot_nhip_ip", ip=ip, token=round(token, 2))
                return False
            self._gau[ip] = (token - 1.0, moc)

            # Don dinh ky de mot tran cao IP khong lam phinh bo nho vo han.
            if len(self._gau) > 10_000:
                nguong = moc - 3600
                self._gau = {k: v for k, v in self._gau.items() if v[1] > nguong}
            return True


@dataclass(frozen=True, slots=True)
class TrangThaiNgay:
    da_dung: int
    tran: int

    @property
    def con_lai(self) -> int:
        return max(0, self.tran - self.da_dung)

    @property
    def phan_tram(self) -> float:
        return 100.0 * self.da_dung / self.tran if self.tran else 0.0


class TranNgay:
    """Tran cung: tong so luot khach web moi ngay, ca site.

    Dem CA luot bi tu choi — neu khong, ke cao bi chan van duoc thu lai vo han
    ma khong bao gio cham tran.
    """

    def __init__(self, settings: Settings, db: Database) -> None:
        self._s = settings
        self._db = db
        self._tran = settings.web_tran_ngay

    async def dem(self, n: int = 1) -> None:
        ngay = _hom_nay()
        await self._db.execute(
            "INSERT INTO web_quota (ngay, so_luot) VALUES (?, ?) "
            "ON CONFLICT(ngay) DO UPDATE SET so_luot = so_luot + ?",
            (ngay, n, n),
        )

    async def trang_thai(self) -> TrangThaiNgay:
        row = await self._db.fetch_one("SELECT so_luot FROM web_quota WHERE ngay = ?", (_hom_nay(),))
        return TrangThaiNgay(da_dung=int(row["so_luot"]) if row else 0, tran=self._tran)

    async def cho_phep(self) -> bool:
        st = await self.trang_thai()
        if st.da_dung >= self._tran:
            log.error("web_het_tran_ngay", da_dung=st.da_dung, tran=self._tran)
            return False
        return True
