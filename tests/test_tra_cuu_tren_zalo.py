"""Che do `tra_cuu` chay TREN ZALO, khong phai trong terminal.

Day la lo hong nghiem trong nhat tung co trong repo, phat hien 11/08/2026:
`agent_cskh/tra_cuu/` chi duoc import o `cli.py`. Duong chay Zalo khong doc
`settings.che_do` o bat ky dau — hoc vien de `CHE_DO=tra_cuu` roi chay bot thi
bot van goi Claude, va `config.problems()` khong bao gi vi no chi kiem API key
khi `che_do == "ai"`.

Toan bo loi hua "ban 0 dong chay tren Zalo" — diem ban hang chinh cua template —
la khong dung.

Nhom test nay canh dung dieu do. No kiem HANH DONG THAT, khong kiem chuoi tra ve:
`cli.py` truoc day cung "chuyen nguoi that" — bang cach IN RA MAN HINH. Tren Zalo
ma lam vay thi khach duoc hua chuyen nguoi con nhan vien khong biet gi.
"""

from __future__ import annotations

import pytest

from agent_cskh.tra_cuu.chay import VongTraCuu
from tests.conftest import make_event, run_one


@pytest.fixture
def rig_tra_cuu(rig):
    """Thay bo nao cua dispatcher bang `VongTraCuu`, y nhu `app.py` lam khi
    `CHE_DO=tra_cuu`."""
    rig["dispatcher"]._loop = VongTraCuu(rig["dispatcher"]._wiki)  # noqa: SLF001
    return rig


def _them_trang(rig, slug: str, tieu_de: str, than: str, tu_khoa: list[str]) -> None:
    goc = rig["settings"].knowledge_dir / "wiki" / "public"
    goc.mkdir(parents=True, exist_ok=True)
    kh = ", ".join(f'"{k}"' for k in tu_khoa)
    (goc / f"{slug}.md").write_text(
        f"---\ntitle: {tieu_de}\nsummary: {tieu_de}\ntu_khoa: [{kh}]\n---\n\n{than}\n",
        encoding="utf-8",
    )
    rig["dispatcher"]._wiki.reload()  # noqa: SLF001


class TestChonDungBoNao:
    """Dong quan trong nhat cua ca ban sua nay. Truoc 11/08/2026 no khong ton tai."""

    def _wiki(self, tmp_path, monkeypatch):
        from agent_cskh.config import Settings
        from agent_cskh.wiki import WikiStore

        monkeypatch.setattr(
            Settings, "knowledge_dir", property(lambda _s: tmp_path / "k"), raising=False
        )
        return Settings(_env_file=None), WikiStore(Settings(_env_file=None))

    def test_tra_cuu_thi_KHONG_dung_AgentLoop(self, tmp_path, monkeypatch) -> None:
        from agent_cskh.app import chon_bo_nao

        s, w = self._wiki(tmp_path, monkeypatch)
        s.che_do = "tra_cuu"
        assert isinstance(chon_bo_nao(s, w), VongTraCuu)

    def test_ai_thi_dung_AgentLoop(self, tmp_path, monkeypatch) -> None:
        from agent_cskh.app import chon_bo_nao
        from agent_cskh.harness.loop import AgentLoop

        s, w = self._wiki(tmp_path, monkeypatch)
        s.che_do = "ai"
        assert isinstance(chon_bo_nao(s, w), AgentLoop)


class TestKhongGoiModel:
    async def test_tra_loi_duoc_ma_KHONG_goi_model_nao(self, rig_tra_cuu) -> None:
        """Day la ca ly do che do nay ton tai. Mot lan goi model o day nghia la
        hoc vien bi tinh tien du da chon ban mien phi."""
        _them_trang(rig_tra_cuu, "bang-gia", "Bảng giá", "Gói cơ bản 5 triệu.", ["gia"])
        await run_one(rig_tra_cuu, make_event("bảng giá bao nhiêu"))

        assert any("5 triệu" in t for t in rig_tra_cuu["client"].texts)
        assert rig_tra_cuu["provider"].calls == [], "che do tra_cuu KHONG duoc goi model"


class TestChuyenNguoiThatLaTHAT:
    """`cli.py` chi in ra man hinh. Tren Zalo phai mo ban giao that."""

    async def test_khong_biet_thi_mo_ban_giao_that(self, rig_tra_cuu) -> None:
        _them_trang(rig_tra_cuu, "bang-gia", "Bảng giá", "Gói cơ bản 5 triệu.", ["gia"])
        await run_one(rig_tra_cuu, make_event("bên mình có làm SEO website không"))

        trang_thai = await rig_tra_cuu["repo"].get_state("c1")
        assert trang_thai == "HUMAN_PENDING", "phai chuyen sang cho nguoi that"

        cho = await rig_tra_cuu["repo"].pending_handoffs()
        assert len(cho) == 1, "phai mo dung mot yeu cau ban giao"

    async def test_co_bao_cho_nhan_vien(self, rig_tra_cuu) -> None:
        """Mo ban giao ma khong bao ai thi khach cho mai."""
        _them_trang(rig_tra_cuu, "bang-gia", "Bảng giá", "Gói cơ bản 5 triệu.", ["gia"])
        await run_one(rig_tra_cuu, make_event("bên mình có làm SEO website không"))

        assert any("CẦN NGƯỜI TIẾP QUẢN" in t for _, t in rig_tra_cuu["client"].sent)

    async def test_khach_van_duoc_tra_loi_mot_cau_tu_te(self, rig_tra_cuu) -> None:
        _them_trang(rig_tra_cuu, "bang-gia", "Bảng giá", "Gói cơ bản 5 triệu.", ["gia"])
        await run_one(rig_tra_cuu, make_event("bên mình có làm SEO website không"))

        assert any("chưa nắm chắc" in t for t in rig_tra_cuu["client"].texts)


class TestVongLapHoc:
    """Moi cau bot khong tra loi duoc phai thanh mot dong trong bao cao 20h.

    Khong ghi thi chu bot khong bao gio biet phai viet them trang gi — do la nut
    that lon nhat cua ca he thong.
    """

    async def test_ghi_thieu_trang_NGUYEN_VAN(self, rig_tra_cuu) -> None:
        _them_trang(rig_tra_cuu, "bang-gia", "Bảng giá", "Gói cơ bản 5 triệu.", ["gia"])
        cau = "bên mình có giao hàng đi Đà Nẵng không"
        await run_one(rig_tra_cuu, make_event(cau))

        rows = await rig_tra_cuu["repo"].thieu_trang_gan_day(ngay=1)
        assert len(rows) == 1
        assert rows[0]["cau_hoi"] == cau, "phai ghi nguyen van, khong tom tat"

    async def test_tra_loi_duoc_thi_KHONG_ghi(self, rig_tra_cuu) -> None:
        _them_trang(rig_tra_cuu, "bang-gia", "Bảng giá", "Gói cơ bản 5 triệu.", ["gia"])
        await run_one(rig_tra_cuu, make_event("bảng giá bao nhiêu"))

        assert await rig_tra_cuu["repo"].thieu_trang_gan_day(ngay=1) == []


class TestCachLyQuyenGiuNguyen:
    """Doi bo nao KHONG duoc doi quyen. Mot trang `internal/` khong bao gio ro
    ra qua duong nay."""

    async def test_nguoi_la_khong_doc_duoc_trang_noi_bo(self, rig_tra_cuu) -> None:
        goc = rig_tra_cuu["settings"].knowledge_dir / "wiki" / "internal"
        goc.mkdir(parents=True, exist_ok=True)
        (goc / "gia-von.md").write_text(
            '---\ntitle: Giá vốn\nsummary: Giá vốn\ntu_khoa: ["gia von"]\n---\n\nGiá vốn 6.000đ.\n',
            encoding="utf-8",
        )
        rig_tra_cuu["dispatcher"]._wiki.reload()  # noqa: SLF001

        await run_one(rig_tra_cuu, make_event("giá vốn bao nhiêu"))
        assert not any("6.000" in t for t in rig_tra_cuu["client"].texts)


class TestAnh:
    async def test_khach_gui_anh_thi_noi_that_va_chuyen_nguoi(self, rig_tra_cuu) -> None:
        """Che do nay khong co model nen khong xem duoc anh. Im lang truoc mot
        anh chuyen khoan la kho chiu nhat."""
        await run_one(rig_tra_cuu, make_event("", photo_url="https://x/y.jpg", kind="photo"))

        assert any("chưa xem được ảnh" in t for t in rig_tra_cuu["client"].texts)
        assert await rig_tra_cuu["repo"].get_state("c1") == "HUMAN_PENDING"
