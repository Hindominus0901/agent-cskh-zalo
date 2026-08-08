"""Nhip tim cua cac phu thuoc ben ngoai.

Bai hoc 05/08/2026: Zalo chet 2 tieng ma khong bao ai. Bot van chay, log van
chay, nhung khong mot tin nhan nao den — va neu khong ai ngoi nhin log thi
khong ai biet.

Bai hoc 07/08/2026: y het nhu vay nhung o phia model. Khoa Anthropic bi thu hoi,
moi luot deu 401, khach nao nhan vao cung nhan cau "he thong dang truc trac" —
va chinh cau do con hua "em da bao cho anh/chi phu trach roi" trong khi khong ai
duoc bao. Hong im lang, lai con noi doi khach. Vi vay dung MOT lop Health cho ca
hai phia: `Health(ten="Zalo")` va `Health(ten="Claude")`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(slots=True)
class Health:
    """Trang thai mot phu thuoc ben ngoai. Ben goi cap nhat, scheduler doc."""

    ten: str = "Zalo"
    khoi_dong: datetime = field(default_factory=_now)
    lan_goi_cuoi_thanh_cong: datetime | None = None
    lan_su_kien_cuoi: datetime | None = None
    so_loi_lien_tiep: int = 0
    da_bao_mat_ket_noi: bool = False
    # Loi gan nhat, de canh bao noi duoc NGUYEN NHAN chu khong chi "co loi".
    loi_cuoi: str = ""

    def ghi_thanh_cong(self) -> None:
        self.lan_goi_cuoi_thanh_cong = _now()
        self.so_loi_lien_tiep = 0
        self.loi_cuoi = ""
        if self.da_bao_mat_ket_noi:
            self.da_bao_mat_ket_noi = False

    def ghi_loi(self, mo_ta: str = "") -> None:
        self.so_loi_lien_tiep += 1
        if mo_ta:
            self.loi_cuoi = mo_ta

    def ghi_su_kien(self) -> None:
        self.lan_su_kien_cuoi = _now()
        self.ghi_thanh_cong()

    def mat_ket_noi_lau_hon(self, nguong: timedelta) -> bool:
        moc = self.lan_goi_cuoi_thanh_cong or self.khoi_dong
        return (_now() - moc) > nguong

    def tom_tat(self) -> str:
        def tuoi(t: datetime | None) -> str:
            if t is None:
                return "chưa có"
            giay = int((_now() - t).total_seconds())
            if giay < 60:
                return f"{giay} giây trước"
            if giay < 3600:
                return f"{giay // 60} phút trước"
            return f"{giay // 3600} giờ {giay % 3600 // 60} phút trước"

        dong = [
            f"Chạy từ: {tuoi(self.khoi_dong)}",
            f"Gọi {self.ten} thành công lần cuối: {tuoi(self.lan_goi_cuoi_thanh_cong)}",
            f"Tin nhắn cuối: {tuoi(self.lan_su_kien_cuoi)}",
            f"Lỗi liên tiếp: {self.so_loi_lien_tiep}",
        ]
        if self.loi_cuoi:
            dong.append(f"Lỗi gần nhất: {self.loi_cuoi}")
        return "\n".join(dong)
