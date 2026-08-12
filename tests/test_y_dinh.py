"""Noi chuyen thay vi go lenh.

Khach hang that khong bao gio go `/baocao`. Chu shop cung khong — ho la nguoi
ban hang, khong phai nguoi dung terminal.

Hai thu duoc canh o day, va thu hai quan trong hon:

  1. Noi bang loi thi chay dung viec
  2. MA TRAN QUYEN KHONG DOI. Nguoi la noi "bao cao hom nay" khong duoc chay gi
     — y het nhu ho go `/baocao`. Neu lop nay lam thung quyen thi no te hon han
     tien ich no mang lai.
"""

from __future__ import annotations

import pytest

from agent_cskh.y_dinh import doan_y_dinh, la_dong_y, la_nguy_hiem
from tests.conftest import make_event, run_one


class TestDoanYDinh:
    """Ham thuan — khong can rig."""

    @pytest.mark.parametrize(
        ("cau", "lenh"),
        [
            ("báo cáo hôm nay", "baocao"),
            ("hôm nay có việc gì", "baocao"),
            ("còn bao nhiêu tin", "trangthai"),
            ("id của tôi", "whoami"),
            ("nạp lại kho", "nap"),
            ("tôi nhận chat này", "nhan"),
            ("trả lại cho bot", "tha"),
            ("khách mới", "lead"),
            ("có những trang nào", "dstrang"),
            ("gặp người thật", "lienhe"),
        ],
    )
    def test_nhan_ra_cach_noi_thuong(self, cau: str, lenh: str) -> None:
        # Chi kiem TEN LENH. Phan du ("hôm nay") thanh tham so va cac handler
        # khong tham so bo qua no — vo hai, va co gang cat cho sach se lam luat
        # khop phuc tap them ma khong duoc gi.
        doan = doan_y_dinh(cau)
        assert doan is not None, cau
        assert doan[0] == lenh

    def test_lay_duoc_tham_so(self) -> None:
        assert doan_y_dinh("xem trang bang-gia") == ("xemtrang", "bang-gia")

    def test_dich_ten_muc_sang_ten_thu_muc(self) -> None:
        """Chu shop khong phai nho "public/hocvien/internal"."""
        lenh, tham_so = doan_y_dinh("thêm trang công khai bang-gia\nGói cơ bản 5 triệu.")
        assert lenh == "themtrang"
        assert tham_so.startswith("public bang-gia")
        assert "5 triệu" in tham_so

    def test_lenh_that_khong_bi_doan_lai(self) -> None:
        assert doan_y_dinh("/baocao") is None

    def test_cau_dai_khong_bi_bat_nham(self) -> None:
        """Cau dai bat dau bang cum khop thi nhieu kha nang la ke chuyen.

        Tha bo sot con hon bat nham: bat nham mot cau noi binh thuong thanh lenh
        thi bot lam mot viec khong ai yeu cau.
        """
        cau = "báo cáo của bên em tháng trước có nói là doanh thu tăng nhưng em thấy chưa đúng lắm"
        assert doan_y_dinh(cau) is None

    def test_cau_hoi_binh_thuong_cua_khach_khong_khop(self) -> None:
        for cau in (
            "bên mình có giao hàng không",
            "cái này bao nhiêu tiền",
            "shop mở cửa mấy giờ",
            "cho em xin địa chỉ",
        ):
            assert doan_y_dinh(cau) is None, cau


class TestXacNhanDongY:
    def test_nhan_cau_dong_y_ngan_gon(self) -> None:
        for cau in ("đồng ý", "ok", "OK", "được", "ừ", "xác nhận"):
            assert la_dong_y(cau), cau

    def test_khong_nhan_cau_lung_chung(self) -> None:
        """"ok nhung ma khoan da" khong phai dong y. Bat nham cho nay la xoa
        nham du lieu."""
        for cau in ("ok nhưng mà khoan đã", "để em nghĩ thêm", "không", "ừ thì cũng được nhưng"):
            assert not la_dong_y(cau), cau


class TestViecNguyHiemPhaiHoiLai:
    def test_danh_dau_dung_viec_nguy_hiem(self) -> None:
        for lenh in ("datkenhcanhbao", "xoatrang", "suatrang", "xoatuvan"):
            assert la_nguy_hiem(lenh), lenh
        for lenh in ("baocao", "whoami", "nap", "lead"):
            assert not la_nguy_hiem(lenh), lenh


@pytest.fixture
def la_chu(rig):
    rig["dispatcher"]._resolver._owners |= {"u1"}  # noqa: SLF001
    return rig


class TestChayThatQuaDispatcher:
    async def test_chu_shop_noi_bang_loi_thi_ra_bao_cao(self, la_chu) -> None:
        await run_one(la_chu, make_event("báo cáo hôm nay"))
        assert any("BÁO CÁO" in t for t in la_chu["client"].texts)

    async def test_khong_ton_token_model_nao(self, la_chu) -> None:
        """Lenh xu ly trong code — noi bang loi cung phai vay."""
        await run_one(la_chu, make_event("báo cáo hôm nay"))
        assert la_chu["provider"].calls == []

    async def test_lenh_gach_cheo_van_chay_ngam(self, la_chu) -> None:
        """Duong lui. Khong tai lieu nao nhac toi, nhung phai con dung."""
        await run_one(la_chu, make_event("/baocao"))
        assert any("BÁO CÁO" in t for t in la_chu["client"].texts)


class TestQuyenKhongDuocThUNG:
    """Neu lop y dinh lam thung quyen thi no te hon han tien ich no mang lai."""

    async def test_nguoi_la_noi_bao_cao_thi_KHONG_chay(self, rig) -> None:
        await run_one(rig, make_event("báo cáo hôm nay"))
        assert not any("BÁO CÁO" in t for t in rig["client"].texts)

    async def test_nguoi_la_khong_xem_duoc_lead(self, rig) -> None:
        await run_one(rig, make_event("khách mới"))
        assert not any("lead" in t.lower() for t in rig["client"].texts)

    async def test_nguoi_la_khong_biet_viec_do_ton_tai(self, rig) -> None:
        """Tu choi phai IM LANG, khong duoc bao "ban khong co quyen" — do la lo
        su ton tai cua chuc nang noi bo. Giong het cach ToolRegistry tu choi."""
        await run_one(rig, make_event("nạp lại kho"))
        assert not any("quyền" in t.lower() for t in rig["client"].texts)


class TestCongXacNhan:
    async def test_viec_nguy_hiem_KHONG_chay_ngay(self, la_chu) -> None:
        await run_one(la_chu, make_event("đặt kênh cảnh báo"))

        assert any("xác nhận" in t.lower() for t in la_chu["client"].texts)
        # Chua doi kenh — van la gia tri cu tu .env
        moi = await la_chu["dispatcher"]._resolver.alert_chat_id()  # noqa: SLF001
        assert moi == la_chu["settings"].alert_chat_id

    async def test_noi_ro_HAU_QUA_chu_khong_chi_hoi_co_chac_khong(self, la_chu) -> None:
        await run_one(la_chu, make_event("đặt kênh cảnh báo"))
        tin = next(t for t in la_chu["client"].texts if "xác nhận" in t.lower())
        assert "khách" in tin.lower(), "phai noi ro canh bao kem ten khach"

    async def test_dong_y_roi_thi_chay(self, la_chu) -> None:
        await run_one(la_chu, make_event("đặt kênh cảnh báo", message_id="m1"))
        await run_one(la_chu, make_event("đồng ý", message_id="m2"))

        moi = await la_chu["dispatcher"]._resolver.alert_chat_id()  # noqa: SLF001
        assert moi == "c1"

    async def test_noi_chuyen_khac_thi_HUY_viec_dang_cho(self, la_chu) -> None:
        """Khong duoc de mot cau "ok" ba luot sau lam chay viec da quen."""
        await run_one(la_chu, make_event("đặt kênh cảnh báo", message_id="m1"))
        await run_one(la_chu, make_event("thôi để sau", message_id="m2"))
        await run_one(la_chu, make_event("đồng ý", message_id="m3"))

        moi = await la_chu["dispatcher"]._resolver.alert_chat_id()  # noqa: SLF001
        assert moi == la_chu["settings"].alert_chat_id, "khong duoc chay viec da huy"

    async def test_go_lenh_that_thi_KHONG_qua_cong_xac_nhan(self, la_chu) -> None:
        """Go dung `/datkenhcanhbao` la hanh dong co y thuc, khong phai cau doan."""
        await run_one(la_chu, make_event("/datkenhcanhbao"))
        moi = await la_chu["dispatcher"]._resolver.alert_chat_id()  # noqa: SLF001
        assert moi == "c1"
