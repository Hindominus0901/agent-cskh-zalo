"""Kho tri thuc LLM Wiki.

Nhom TestCachLyQuyen la quan trong nhat trong ca bo test: no chan viec tai lieu
noi bo (gia von, quy trinh, thong tin khach khac) lot ra ngoai cho khach la.
Neu mot test o do do, DUNG LAI va sua truoc khi lam gi khac.
"""

from __future__ import annotations

import pytest

from agent_cskh.config import Settings
from agent_cskh.wiki import WikiStore, strip_accents

PUBLIC = frozenset({"public"})
FULL = frozenset({"public", "internal"})


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(Settings, "knowledge_dir", property(lambda _s: tmp_path), raising=False)
    (tmp_path / "wiki" / "public").mkdir(parents=True)
    (tmp_path / "wiki" / "internal").mkdir(parents=True)

    (tmp_path / "wiki" / "public" / "bang-gia.md").write_text(
        "---\n"
        "title: Bảng giá dịch vụ\n"
        "summary: Ba gói tư vấn thương hiệu cá nhân và giá từng gói.\n"
        "tags: [bang-gia, dich-vu]\n"
        "updated: 2026-08-05\n"
        "---\n\n"
        "# Bảng giá\n\nGói Standard 15.000.000 đồng một năm.\n",
        encoding="utf-8",
    )
    (tmp_path / "wiki" / "public" / "faq.md").write_text(
        "---\ntitle: Câu hỏi thường gặp\nsummary: Giải đáp thắc mắc phổ biến của khách.\n---\n\n"
        "Thời gian triển khai trung bình sáu tuần.\n",
        encoding="utf-8",
    )
    (tmp_path / "wiki" / "internal" / "gia-von.md").write_text(
        "---\ntitle: Giá vốn\nsummary: Chi phí thực tế và biên lợi nhuận từng gói.\n---\n\n"
        "Biên lợi nhuận gói Standard là 62 phần trăm.\n",
        encoding="utf-8",
    )

    s = Settings(_env_file=None)
    st = WikiStore(s)
    st.reload()
    return st


class TestCachLyQuyen:
    """Khach la khong bao gio duoc thay bat cu gi trong internal/."""

    def test_nguoi_la_chi_thay_trang_public(self, store) -> None:
        slugs = {p.slug for p in store.visible(PUBLIC)}
        assert slugs == {"bang-gia", "faq"}
        assert "gia-von" not in slugs

    def test_noi_bo_thay_tat_ca(self, store) -> None:
        assert {p.slug for p in store.visible(FULL)} == {"bang-gia", "faq", "gia-von"}

    def test_index_cua_nguoi_la_khong_lo_ten_trang_noi_bo(self, store) -> None:
        idx = store.render_index(PUBLIC)
        assert "bang-gia" in idx
        assert "gia-von" not in idx, "ten trang noi bo lot vao index cua khach"
        assert "lợi nhuận" not in idx

    def test_nguoi_la_khong_doc_duoc_trang_noi_bo(self, store) -> None:
        assert store.read("gia-von", PUBLIC) is None

    def test_noi_bo_doc_duoc(self, store) -> None:
        page = store.read("gia-von", FULL)
        assert page is not None
        assert "62 phần trăm" in page.body

    def test_tim_kiem_khong_lo_trang_noi_bo(self, store) -> None:
        """Ngay ca khi go dung tu khoa nam trong tai lieu noi bo.

        Luu y: truy van van co the tra ve trang PUBLIC (vi du "giá vốn" khop chu
        "giá" trong bang gia) — do la binh thuong. Dieu cam la trang internal lot ra.
        """
        for q in ("lợi nhuận", "giá vốn", "62 phần trăm"):
            assert all(p.visibility == "public" for p in store.search(q, PUBLIC)), q
            assert "gia-von" not in {p.slug for p in store.search(q, PUBLIC)}, q
        assert [p.slug for p in store.search("lợi nhuận", FULL)] == ["gia-von"]

    def test_khong_thoat_duoc_thu_muc(self, store) -> None:
        """Bot chi chon slug da quet san — khong co duong ghep path."""
        for doc in ("../../../etc/passwd", "..\\..\\.env", "/etc/passwd", "../gia-von"):
            assert store.read(doc, PUBLIC) is None
            assert store.read(doc, FULL) is None


class TestTimKiem:
    def test_tim_duoc_khi_go_khong_dau(self, store) -> None:
        """Khach Viet thuong go khong dau — phai khop duoc."""
        hits = store.search("bang gia", PUBLIC)
        assert [p.slug for p in hits] == ["bang-gia"]

    def test_tim_duoc_khi_go_co_dau(self, store) -> None:
        assert [p.slug for p in store.search("bảng giá", PUBLIC)] == ["bang-gia"]

    def test_tim_trong_than_bai(self, store) -> None:
        assert [p.slug for p in store.search("sáu tuần", PUBLIC)] == ["faq"]

    def test_tieu_de_uu_tien_hon_than_bai(self, store) -> None:
        hits = store.search("gia", PUBLIC)
        assert hits[0].slug == "bang-gia"

    def test_khong_khop_thi_rong(self, store) -> None:
        assert store.search("xyzkhongtontai", PUBLIC) == []

    def test_tu_khoa_rong(self, store) -> None:
        assert store.search("", PUBLIC) == []
        assert store.search("   ", PUBLIC) == []


class TestIndex:
    def test_index_co_tom_tat_tung_trang(self, store) -> None:
        idx = store.render_index(FULL)
        assert "Ba gói tư vấn thương hiệu cá nhân" in idx
        assert "[[bang-gia]]" in idx

    def test_trang_noi_bo_duoc_danh_dau(self, store) -> None:
        assert "[[gia-von]] [nội bộ]" in store.render_index(FULL)

    def test_kho_rong_tra_ve_chuoi_rong(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(Settings, "knowledge_dir", property(lambda _s: tmp_path), raising=False)
        st = WikiStore(Settings(_env_file=None))
        st.reload()
        assert st.render_index(FULL) == ""


class TestDocTrang:
    def test_bo_qua_duoi_md(self, store) -> None:
        assert store.read("bang-gia.md", PUBLIC) is not None

    def test_trang_khong_ton_tai(self, store) -> None:
        assert store.read("khong-co-trang-nay", FULL) is None

    def test_render_co_tieu_de_va_ngay(self, store) -> None:
        out = store.read("bang-gia", PUBLIC).render()
        assert out.startswith("# Bảng giá dịch vụ")
        assert "2026-08-05" in out


class TestBoDau:
    def test_bo_dau_tieng_viet(self) -> None:
        assert strip_accents("Báo giá dịch vụ") == "bao gia dich vu"
        assert strip_accents("ĐƯỜNG") == "duong"
        assert strip_accents("Nguyễn Văn Đức") == "nguyen van duc"
