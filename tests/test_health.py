"""Nhip tim ket noi.

Bai hoc 07/08/2026: Zalo tra 408 "Request timeout" moi ~30 giay khi khong ai nhan
— do la trang thai BINH THUONG cua long-poll, khong phai loi. Truoc khi sua, moi
lan nhu vay bi dem la loi ket noi, nen sau 10 phut yen ang la watchdog bao dong gia.
Canh bao sai con te hon khong co canh bao: vai lan la nguoi ta bo qua luon.
"""

from __future__ import annotations

from datetime import timedelta

from agent_cskh.health import Health


class TestNhipTim:
    def test_moi_khoi_dong_chua_coi_la_mat_ket_noi(self) -> None:
        h = Health()
        assert not h.mat_ket_noi_lau_hon(timedelta(minutes=10))

    def test_ghi_thanh_cong_xoa_bo_dem_loi(self) -> None:
        h = Health()
        h.ghi_loi()
        h.ghi_loi()
        assert h.so_loi_lien_tiep == 2
        h.ghi_thanh_cong()
        assert h.so_loi_lien_tiep == 0

    def test_ghi_thanh_cong_go_co_da_bao(self) -> None:
        """Zalo song lai thi phai cho phep bao dong lan sau."""
        h = Health()
        h.da_bao_mat_ket_noi = True
        h.ghi_thanh_cong()
        assert not h.da_bao_mat_ket_noi

    def test_ghi_su_kien_cung_tinh_la_thanh_cong(self) -> None:
        h = Health()
        h.ghi_loi()
        h.ghi_su_kien()
        assert h.so_loi_lien_tiep == 0
        assert h.lan_su_kien_cuoi is not None
        assert h.lan_goi_cuoi_thanh_cong is not None

    def test_phat_hien_mat_ket_noi_theo_nguong(self) -> None:
        h = Health()
        h.khoi_dong = h.khoi_dong - timedelta(minutes=30)
        assert h.mat_ket_noi_lau_hon(timedelta(minutes=10))
        h.ghi_thanh_cong()
        assert not h.mat_ket_noi_lau_hon(timedelta(minutes=10))

    def test_tom_tat_doc_duoc_khi_chua_co_gi(self) -> None:
        assert "chưa có" in Health().tom_tat()


class TestPhanBietRongVoiLoi:
    """Ba gia tri tra ve cua get_updates phai duoc phan biet ro."""

    def test_long_poll_rong_khong_tinh_la_loi(self) -> None:
        """dict rong = khong co tin. Nhip tim phai coi la khoe."""
        h = Health()
        for _ in range(50):  # 50 lan long-poll rong lien tiep
            body: dict = {}
            if body is None:
                h.ghi_loi()
            else:
                h.ghi_thanh_cong()
        assert h.so_loi_lien_tiep == 0
        assert not h.mat_ket_noi_lau_hon(timedelta(minutes=10))

    def test_none_moi_tinh_la_loi(self) -> None:
        h = Health()
        for _ in range(3):
            body = None
            if body is None:
                h.ghi_loi()
            else:
                h.ghi_thanh_cong()
        assert h.so_loi_lien_tiep == 3
