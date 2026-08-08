"""Quan tri tu Zalo: kenh canh bao va sua kho tri thuc.

Bai hoc 08/08/2026: tin "CAN NGUOI TIEP QUAN" — kem TEN KHACH va chat_id — hien
ngay giua doan chat cua chu bot voi bot, vi ALERT_CHAT_ID tro vao chinh chat do.
O chat rieng thi chi kho chiu. Trong mot nhom hoc vien thi hoc vien A doc duoc
chuyen cua hoc vien B.

Nen kenh canh bao phai DAT DUOC TU TRONG CHAT, va phai tach khoi noi bot phuc vu.
"""

from __future__ import annotations

import pytest

from tests.conftest import make_event, run_one


@pytest.fixture
def la_chu(rig):
    # THEM chu bot, khong thay the: "admin" van phai la kenh canh bao hop le.
    rig["dispatcher"]._resolver._owners |= {"u1"}  # noqa: SLF001
    return rig


class TestKenhCanhBao:
    async def test_dat_duoc_tu_trong_chat(self, rig, la_chu) -> None:
        await run_one(rig, make_event("/datkenhcanhbao Nhóm nội bộ"))

        assert any("Đã đặt cuộc trò chuyện này" in t for t in rig["client"].texts)
        moi = await rig["dispatcher"]._resolver.alert_chat_id()  # noqa: SLF001
        assert moi == "c1"

    async def test_canh_bao_ro_ve_rui_ro_lo_du_lieu(self, rig, la_chu) -> None:
        """Nguoi dat kenh phai biet ngay rang day KHONG duoc la nhom hoc vien."""
        await run_one(rig, make_event("/datkenhcanhbao"))

        tin = next(t for t in rig["client"].texts if "Đã đặt" in t)
        assert "học viên" in tin.lower()
        assert "khách hàng" in tin.lower()

    async def test_dat_kenh_moi_thi_go_kenh_cu(self, rig, la_chu) -> None:
        """Hai kenh nghia la mot nua canh bao di mot noi — khong ai phat hien."""
        r = rig["dispatcher"]._resolver  # noqa: SLF001
        await r.dat_kenh_canh_bao("chat_cu", "cũ")
        await r.dat_kenh_canh_bao("chat_moi", "mới")

        assert await r.alert_chat_id() == "chat_moi"
        con = await rig["db"].fetch_val(
            "SELECT COUNT(*) FROM trusted_chats WHERE is_alert_target = 1"
        )
        assert con == 1

    async def test_uu_tien_csdl_hon_env(self, rig, la_chu) -> None:
        r = rig["dispatcher"]._resolver  # noqa: SLF001
        assert await r.alert_chat_id() == rig["settings"].alert_chat_id

        await r.dat_kenh_canh_bao("nhom_noi_bo")
        assert await r.alert_chat_id() == "nhom_noi_bo"

    async def test_canh_bao_di_theo_kenh_moi(self, rig, la_chu) -> None:
        """Doi kenh xong thi canh bao phai toi noi MOI, khong phai noi cu."""
        r = rig["dispatcher"]._resolver  # noqa: SLF001
        await r.dat_kenh_canh_bao("nhom_noi_bo")

        await run_one(rig, make_event("/themtrang public trang-e\nNội dung"))

        gui_cho = {c for c, t in rig["client"].sent if "KHO TRI THỨC VỪA ĐỔI" in t}
        assert gui_cho == {"nhom_noi_bo"}

    async def test_nhan_vien_khong_doi_duoc_kenh(self, rig) -> None:
        """Doi kenh canh bao la doi noi du lieu khach hang chay ve — chi chu bot."""
        await rig["db"].execute(
            "INSERT INTO principals (user_id, role, created_at, updated_at) VALUES (?,?,?,?)",
            ("u1", "staff", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
        )
        await run_one(rig, make_event("/datkenhcanhbao"))
        assert not any("Đã đặt cuộc trò chuyện này" in t for t in rig["client"].texts)


class TestSuaKhoTriThucTuZalo:
    async def test_them_trang_va_bot_doc_duoc_ngay(self, rig, la_chu) -> None:
        await run_one(
            rig,
            make_event("/themtrang public bang-gia-thu\nBảng giá thử\nGói cơ bản 5 triệu."),
        )

        assert any("Đã thêm" in t for t in rig["client"].texts)
        page = rig["dispatcher"]._wiki.read("bang-gia-thu", frozenset({"public"}))  # noqa: SLF001
        assert page is not None
        assert "Gói cơ bản 5 triệu" in page.body

    async def test_dong_dau_thanh_tieu_de(self, rig, la_chu) -> None:
        await run_one(rig, make_event("/themtrang public trang-thu\nTiêu đề của tôi\nNội dung."))
        page = rig["dispatcher"]._wiki.read("trang-thu", frozenset({"public"}))  # noqa: SLF001
        assert page.title == "Tiêu đề của tôi"

    async def test_ten_trang_khong_thoat_duoc_thu_muc(self, rig, la_chu) -> None:
        """Bot khong bao gio ghep duong dan tu dau vao nguoi dung."""
        for xau in ("../../../etc/passwd", "..%2Fabc", "a/b", "..", "CON"):
            rig["client"].sent.clear()
            await run_one(
                rig,
                make_event(f"/themtrang public {xau}\nnội dung", message_id=f"m{hash(xau)}"),
            )
            assert any(
                "không hợp lệ" in t or "chỉ dùng chữ thường" in t for t in rig["client"].texts
            )

    async def test_muc_la_bi_tu_choi(self, rig, la_chu) -> None:
        await run_one(rig, make_event("/themtrang bimat trang-x\nnội dung"))
        assert any("không có" in t for t in rig["client"].texts)

    async def test_khong_ghi_de_nham_khi_trang_da_co(self, rig, la_chu) -> None:
        await run_one(rig, make_event("/themtrang public trang-a\nBản một", message_id="m1"))
        await run_one(rig, make_event("/themtrang public trang-a\nBản hai", message_id="m2"))

        assert any("đã có rồi" in t for t in rig["client"].texts)
        page = rig["dispatcher"]._wiki.read("trang-a", frozenset({"public"}))  # noqa: SLF001
        assert "Bản một" in page.body

    async def test_sua_trang_giu_lai_ban_cu(self, rig, la_chu) -> None:
        """Go nham tren dien thoai khong co Ctrl+Z."""
        await run_one(rig, make_event("/themtrang public trang-b\nBản gốc", message_id="m1"))
        await run_one(rig, make_event("/suatrang public trang-b\nBản mới", message_id="m2"))

        goc = rig["settings"].knowledge_dir / "wiki" / "public"
        assert (goc / "trang-b.md.bak").exists()
        assert "Bản gốc" in (goc / "trang-b.md.bak").read_text(encoding="utf-8")
        assert "Bản mới" in (goc / "trang-b.md").read_text(encoding="utf-8")

    async def test_xoa_khong_xoa_han(self, rig, la_chu) -> None:
        await run_one(rig, make_event("/themtrang public trang-c\nNội dung", message_id="m1"))
        await run_one(rig, make_event("/xoatrang public trang-c", message_id="m2"))

        goc = rig["settings"].knowledge_dir / "wiki" / "public"
        assert not (goc / "trang-c.md").exists()
        assert (goc / "trang-c.md.bak").exists()
        assert rig["dispatcher"]._wiki.read("trang-c", frozenset({"public"})) is None  # noqa: SLF001

    async def test_moi_thay_doi_deu_bao_nguoi_that(self, rig, la_chu) -> None:
        """Kho doi la bot noi khac voi MOI nguoi — khong duoc am tham."""
        await run_one(rig, make_event("/themtrang public trang-d\nNội dung"))
        assert any("KHO TRI THỨC VỪA ĐỔI" in t for _, t in rig["client"].sent)

    async def test_khach_than_thiet_khong_sua_duoc_kho(self, rig) -> None:
        """Vai `student` la khach da duoc nhan dien — van khong duoc dung toi kho."""
        await rig["db"].execute(
            "INSERT INTO principals (user_id, role, created_at, updated_at) VALUES (?,?,?,?)",
            ("u1", "student", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
        )
        await run_one(rig, make_event("/themtrang public trang-lau\nnội dung"))
        goc = rig["settings"].knowledge_dir / "wiki" / "public"
        assert not (goc / "trang-lau.md").exists()

    async def test_nguoi_la_khong_sua_duoc_kho(self, rig) -> None:
        await run_one(rig, make_event("/themtrang public trang-la\nnội dung"))
        goc = rig["settings"].knowledge_dir / "wiki" / "public"
        assert not (goc / "trang-la.md").exists()

    async def test_xemtrang_ton_trong_quyen(self, rig, la_chu) -> None:
        """Chu bot doc duoc internal; hoc vien thi khong — dung mot lenh."""
        await run_one(rig, make_event("/themtrang internal bi-mat\nBí mật\nKhông cho ai xem."))
        rig["client"].sent.clear()
        await run_one(rig, make_event("/xemtrang bi-mat", message_id="m9"))
        assert any("Không cho ai xem" in t for t in rig["client"].texts)
