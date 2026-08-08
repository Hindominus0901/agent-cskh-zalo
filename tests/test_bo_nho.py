"""Tri nho lau dai — tim hoi thoai cu (FTS5) va bo nho do agent tu soan.

Nam tinh chat, moi cai ung voi mot cach hong da luong truoc:

  khong ro tim thay  — tin nhan cu tim duoc ca khi go khong dau
  khong ro chat khac — tim kiem KHONG BAO GIO thay tin cua cuoc tro chuyen khac
  khong ghi ho nguoi — cong cu ghi khong co duong nao ghi vao ho so nguoi khac
  khong phinh vo han — moi nguoi toi da 20 muc, cham tran thi don cai cu nhat
  khong duoc mien tra kho — goi cong cu tri nho khong lam mat lop chan pham vi

Cai thu hai va thu nam la hai cai quan trong nhat: mot cai la ro du lieu, mot
cai la mo lai duong vong ma toan bo lop chan pham vi sinh ra de bit.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from agent_cskh.store.repo.bo_nho import TOI_DA_KY_TU, TOI_DA_MOI_NGUOI, lam_sach_truy_van
from agent_cskh.tools import default_registry
from agent_cskh.tools.bo_nho import GHI_NHO, TIM_HOI_THOAI


async def _tin(rig, chat_id: str, text: str, *, huong: str = "in", cach_day_ngay: int = 0) -> None:
    """Nhet mot tin nhan that vao CSDL. Trigger FTS5 phai tu lap chi muc."""
    luc = (datetime.now(tz=UTC) - timedelta(days=cach_day_ngay)).isoformat()
    await rig["db"].execute(
        "INSERT OR IGNORE INTO conversations (chat_id, chat_type, session_id, created_at) "
        "VALUES (?, 'private', 's1', ?)",
        (chat_id, luc),
    )
    await rig["db"].execute(
        "INSERT INTO messages (chat_id, session_id, user_id, direction, kind, text, created_at) "
        "VALUES (?, 's1', 'u1', ?, 'text', ?, ?)",
        (chat_id, huong, text, luc),
    )


class TestTimHoiThoaiCu:
    async def test_tim_duoc_tin_ngoai_cua_so_12_tin(self, rig) -> None:
        """Chinh la lo hong can va: hoc vien quay lai sau hai tuan."""
        await _tin(rig, "c1", "Em làm ngành mỹ phẩm handmade ạ", cach_day_ngay=14)
        for i in range(30):
            await _tin(rig, "c1", f"tin nhắn lấp chỗ số {i}")

        kq = await rig["bo_nho"].tim("c1", "mỹ phẩm", bo_qua_gan_nhat=13)
        assert len(kq) == 1
        assert "handmade" in kq[0].van_ban

    async def test_go_khong_dau_van_tim_ra(self, rig) -> None:
        await _tin(rig, "c1", "Trang web của em là thuyle.vn ạ", cach_day_ngay=3)
        assert await rig["bo_nho"].tim("c1", "trang web")

    async def test_go_co_dau_tim_ra_tin_khong_dau(self, rig) -> None:
        await _tin(rig, "c1", "Em ban my pham cho me bim sua", cach_day_ngay=3)
        assert await rig["bo_nho"].tim("c1", "mỹ phẩm")

    async def test_KHONG_BAO_GIO_thay_tin_cua_chat_khac(self, rig) -> None:
        """Rang buoc quan trong nhat cua ca file nay.

        Mot bo tim kiem tren toan bang `messages` se tra ve doan chat cua khach
        khac cho bat ky ai biet hoi dung tu khoa. `chat_id` la tham so bat buoc
        va khong co duong nao bo qua no.
        """
        await _tin(rig, "cua_nguoi_khac", "Số tài khoản của tôi là 0123456789")
        assert await rig["bo_nho"].tim("cua_nguoi_khac", "tài khoản")
        assert await rig["bo_nho"].tim("c1", "tài khoản") == []
        assert await rig["bo_nho"].tim("c1", "0123456789") == []

    async def test_bo_qua_nhung_tin_model_dang_nhin_thay(self, rig) -> None:
        """Tin vua den se luon tu khop voi chinh no — do la nhieu, khong phai ket qua."""
        await _tin(rig, "c1", "cho em hỏi về mỹ phẩm")
        assert await rig["bo_nho"].tim("c1", "mỹ phẩm", bo_qua_gan_nhat=0)
        assert await rig["bo_nho"].tim("c1", "mỹ phẩm", bo_qua_gan_nhat=13) == []

    async def test_ky_tu_cu_phap_fts_khong_lam_no_truy_van(self, rig) -> None:
        """Tin nhan nguoi dung day dau ngoac kep, dau sao, dau tru.

        Mot dau ngoac kep le lot thang vao FTS5 la ca cau truy van nem loi —
        va loi do se hien ra duoi dang "cong cu gap loi" giua cuoc tro chuyen.
        """
        await _tin(rig, "c1", "Em bán mỹ phẩm ạ", cach_day_ngay=2)
        for ac in ('mỹ" OR "', "* NEAR AND -", '"""', "^$[]()", "AND OR NOT"):
            assert await rig["bo_nho"].tim("c1", ac) is not None

    async def test_truy_van_rong_tra_ve_rong_chu_khong_tra_ve_tat_ca(self, rig) -> None:
        await _tin(rig, "c1", "một tin bất kỳ", cach_day_ngay=2)
        assert lam_sach_truy_van("!!! ???") == ""
        assert await rig["bo_nho"].tim("c1", "!!! ???") == []

    async def test_chi_muc_theo_kip_khi_tin_bi_xoa(self, rig) -> None:
        """External content table: thieu trigger thi chi muc lech va tra ve rac."""
        await _tin(rig, "c1", "một bí mật cần xoá", cach_day_ngay=2)
        assert await rig["bo_nho"].tim("c1", "bí mật")
        await rig["db"].execute("DELETE FROM messages WHERE text = ?", ("một bí mật cần xoá",))
        assert await rig["bo_nho"].tim("c1", "bí mật") == []


class TestGhiNho:
    async def test_ghi_roi_doc_lai_duoc(self, rig) -> None:
        assert (
            await rig["bo_nho"].ghi(
                user_id="u1",
                khoa="nganh",
                gia_tri="mỹ phẩm handmade",
                nguon_role="student",
                nguon_chat_id="c1",
            )
            == "moi"
        )
        ds = await rig["bo_nho"].danh_sach("u1")
        assert [(n.khoa, n.gia_tri) for n in ds] == [("nganh", "mỹ phẩm handmade")]

    async def test_ghi_lai_cung_khoa_thi_THAY_chu_khong_chong_them(self, rig) -> None:
        """Hai dong mau thuan de model tu chon la kieu hong te nhat."""
        for v in ("mỹ phẩm", "mỹ phẩm handmade cho mẹ bỉm"):
            await rig["bo_nho"].ghi(
                user_id="u1",
                khoa="nganh",
                gia_tri=v,
                nguon_role="student",
                nguon_chat_id="c1",
            )
        ds = await rig["bo_nho"].danh_sach("u1")
        assert len(ds) == 1
        assert ds[0].gia_tri == "mỹ phẩm handmade cho mẹ bỉm"

    async def test_cham_tran_thi_don_cai_cu_nhat(self, rig) -> None:
        """Quen dan la hanh vi dung. Tu choi ghi khi day se lam bot ket lai o
        hieu biet cua tuan dau tien va khong bao gio cap nhat duoc nua."""
        for i in range(TOI_DA_MOI_NGUOI + 5):
            await rig["bo_nho"].ghi(
                user_id="u1",
                khoa=f"muc{i:02d}",
                gia_tri=f"giá trị {i}",
                nguon_role="student",
                nguon_chat_id="c1",
            )
        ds = await rig["bo_nho"].danh_sach("u1")
        assert len(ds) == TOI_DA_MOI_NGUOI
        khoa = {n.khoa for n in ds}
        assert "muc24" in khoa
        assert "muc00" not in khoa

    async def test_cat_gia_tri_qua_dai(self, rig) -> None:
        await rig["bo_nho"].ghi(
            user_id="u1",
            khoa="dai",
            gia_tri="x" * 5000,
            nguon_role="student",
            nguon_chat_id="c1",
        )
        assert len((await rig["bo_nho"].danh_sach("u1"))[0].gia_tri) == TOI_DA_KY_TU

    async def test_bo_nho_cua_ai_o_yen_cho_nguoi_do(self, rig) -> None:
        await rig["bo_nho"].ghi(
            user_id="u1",
            khoa="nganh",
            gia_tri="mỹ phẩm",
            nguon_role="student",
            nguon_chat_id="c1",
        )
        assert await rig["bo_nho"].danh_sach("u2") == []

    async def test_xoa_duoc(self, rig) -> None:
        await rig["bo_nho"].ghi(
            user_id="u1",
            khoa="nganh",
            gia_tri="mỹ phẩm",
            nguon_role="student",
            nguon_chat_id="c1",
        )
        assert await rig["bo_nho"].xoa("u1", "nganh") == 1
        assert await rig["bo_nho"].danh_sach("u1") == []


class TestRangBuocCauTruc:
    """Nhung dieu duoc ep boi HINH DANG cua code, khong boi loi dan trong prompt."""

    def test_ghi_nho_khong_co_tham_so_ghi_cho_ai(self) -> None:
        """Khac biet quan trong nhat so voi Hermes Agent.

        Hermes phuc vu mot nguoi dung dang tin. Bot nay noi chuyen voi hoc vien
        va nguoi la. Neu co tham so "ghi cho ai" thi mot hoc vien co the noi mot
        cau khien bot ghi nham vao ho so nguoi khac — o day dieu do khong bieu
        dat duoc, chu khong phai bi cam.
        """
        assert set(GHI_NHO.input_schema["properties"]) == {"khoa", "noi_dung"}

    def test_tim_hoi_thoai_khong_co_tham_so_chat_id(self) -> None:
        """Cung ly le: chat_id lay tu ctx, model khong chon duoc."""
        assert set(TIM_HOI_THOAI.input_schema["properties"]) == {"tu_khoa"}

    def test_nguoi_la_khong_ghi_nho_duoc(self) -> None:
        ten = {t.name for t in default_registry().allowed("stranger")}
        assert "ghi_nho" not in ten
        assert "tim_hoi_thoai" in ten

    def test_hoc_vien_ghi_nho_duoc(self) -> None:
        assert "ghi_nho" in {t.name for t in default_registry().allowed("student")}

    @pytest.mark.parametrize("ten", ["ghi_nho", "tim_hoi_thoai"])
    def test_cong_cu_tri_nho_KHONG_duoc_mien_tra_kho_tri_thuc(self, ten: str) -> None:
        """Neu tinh la 'luot da lam viec that' thi model hoc duoc mot duong vong:
        goi mot cong cu tri nho re tien, roi tra loi tu tri thuc chung — va lop
        chan pham vi o reply() thanh vo dung."""
        tool = next(t for t in default_registry().allowed("student") if t.name == ten)
        assert tool.tinh_la_lam_viec is False
