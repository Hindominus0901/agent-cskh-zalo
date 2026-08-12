"""Ba cong cu don hang, va luat quan trong nhat cua chung: TU TAT KHI THIEU DU LIEU.

Bot khong bao gio duoc hua mot nang luc he thong khong co. Dang ky cong cu roi
tra "chua cau hinh" thi model se noi voi khach "de em tra don giup anh/chi" roi
moi phat hien khong tra duoc — luc do khach da tin roi.
"""

from __future__ import annotations

import pytest

from agent_cskh.config import Settings
from agent_cskh.tools import default_registry
from agent_cskh.tools.don_hang import co_du_lieu, duong_dan

CSV_DU = (
    "ma_don,sdt,trang_thai,mat_hang\n"
    "DH1001,0912345678,Đang giao,Áo thun\n"
    "DH1002,0912 345 678,Đã giao,Quần jean\n"
    "DH1003,0987654321,Chờ xác nhận,Mũ vải\n"
)


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(Settings, "data_dir", property(lambda _s: tmp_path), raising=False)
    return Settings(_env_file=None)


def _ghi(s, noi_dung: str) -> None:
    duong_dan(s).write_text(noi_dung, encoding="utf-8")


class TestTuTatKhiThieuDuLieu:
    def test_khong_co_file_thi_KHONG_dang_ky(self, s) -> None:
        ten = {t.name for t in default_registry(s).specs("stranger")}
        assert "tra_don_hang" not in ten
        assert "ghi_don_tam" not in ten
        assert "kiem_ton_kho" not in ten

    def test_co_file_thi_dang_ky(self, s) -> None:
        _ghi(s, CSV_DU)
        ten = {t.name for t in default_registry(s).specs("stranger")}
        assert {"tra_don_hang", "ghi_don_tam", "kiem_ton_kho"} <= ten

    def test_file_THIEU_COT_thi_coi_nhu_khong_co(self, s) -> None:
        """File sai cau truc con nguy hiem hon khong co file: no lam bot tuong
        minh tra duoc don."""
        _ghi(s, "ma_don,ten_khach\nDH1,An\n")
        assert not co_du_lieu(s)
        assert "tra_don_hang" not in {t.name for t in default_registry(s).specs("stranger")}

    def test_cac_cong_cu_khac_khong_bi_anh_huong(self, s) -> None:
        ten = {t.name for t in default_registry(s).specs("stranger")}
        assert "doc_trang" in ten
        assert "chuyen_nguoi_that" in ten


class TestTraDon:
    async def _chay(self, s, args):
        from agent_cskh.tools.don_hang import TRA_DON_HANG

        class Ctx:
            settings = s

        return await TRA_DON_HANG.handler(Ctx(), args)  # type: ignore[arg-type]

    async def test_tra_theo_ma_don(self, s) -> None:
        _ghi(s, CSV_DU)
        out = await self._chay(s, {"ma_don": "DH1001"})
        assert "Đang giao" in out

    async def test_ma_don_khong_phan_biet_hoa_thuong(self, s) -> None:
        _ghi(s, CSV_DU)
        assert "Đang giao" in await self._chay(s, {"ma_don": "dh1001"})

    async def test_tra_theo_sdt_bo_qua_dau_cach_va_dau_cham(self, s) -> None:
        """Khach go "0912 345 678", he thong luu "0912345678" — phai la mot."""
        _ghi(s, CSV_DU)
        out = await self._chay(s, {"sdt": "0912.345.678"})
        assert "DH1001" in out and "DH1002" in out

    async def test_khong_thay_thi_BAO_MODEL_DUNG_DOAN(self, s) -> None:
        _ghi(s, CSV_DU)
        out = await self._chay(s, {"ma_don": "DH9999"})
        assert "ĐỪNG đoán" in out

    async def test_thieu_ca_hai_tham_so(self, s) -> None:
        _ghi(s, CSV_DU)
        assert "Thiếu" in await self._chay(s, {})


class TestGhiDonKhongPhaiChotDon:
    """Bot doc sai mot chu trong dia chi hoac so luong thi thanh mot don sai
    duoc giao di that. Nguoi that xac nhan la buoc re nhat trong ca chuoi."""

    def test_mo_ta_cong_cu_noi_ro_khong_phai_chot_don(self) -> None:
        from agent_cskh.tools.don_hang import GHI_DON_TAM

        assert "KHÔNG phải là chốt đơn" in GHI_DON_TAM.description

    def test_kiem_ton_kho_khong_tu_khang_dinh_con_hang(self) -> None:
        """Chua noi duoc du lieu ton kho that thi tuyet doi khong doan."""
        from agent_cskh.tools.don_hang import KIEM_TON_KHO

        assert KIEM_TON_KHO.tinh_la_lam_viec is False
