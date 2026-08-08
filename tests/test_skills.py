"""Kho ky nang — bo nho quy trinh.

Hai thu duoc canh o day:

  1. CONG DUYET. Skill bot tu sinh khong duoc vao prompt truoc khi nguoi duyet.
  2. MUC LUC KHONG CHUA THAN BAI. Do la ca ly do co cong cu `doc_skill`.

Cong them mot test canh chinh cai loi cua ban goc: muc luc noi "goi doc_skill"
ma cong cu do khong ton tai trong registry.
"""

from __future__ import annotations

import pytest

from agent_cskh.config import Settings
from agent_cskh.skills import KhoSkill, doc_skill


def _viet(goc, ten: str, *, nguon: str = "nguoi", trang_thai: str = "") -> None:
    d = goc / ten
    d.mkdir(parents=True, exist_ok=True)
    tt = f"trang_thai: {trang_thai}\n" if trang_thai else ""
    (d / "SKILL.md").write_text(
        f"---\nname: {ten}\ndescription: Mô tả của {ten}.\n"
        f"when: Khi gặp {ten}.\nnguon: {nguon}\n{tt}---\n\n"
        f"# {ten}\n\nBƯỚC BÍ MẬT CỦA {ten}.\n",
        encoding="utf-8",
    )


@pytest.fixture
def kho(tmp_path, monkeypatch):
    monkeypatch.setattr(
        Settings, "skills_dir", property(lambda _s: tmp_path / "skills"), raising=False
    )
    s = Settings(_env_file=None)
    s.skills_dir.mkdir(parents=True, exist_ok=True)
    return s


class TestDocFile:
    def test_thu_muc_khong_co_SKILL_md_thi_bo_qua(self, kho, tmp_path) -> None:
        (tmp_path / "skills" / "rong").mkdir(parents=True)
        k = KhoSkill(kho)
        assert k.nap() == 0

    def test_doc_duoc_mo_ta_va_khi_nao(self, kho, tmp_path) -> None:
        _viet(tmp_path / "skills", "bao-gia")
        s = doc_skill(tmp_path / "skills" / "bao-gia")
        assert s is not None
        assert s.mo_ta == "Mô tả của bao-gia."
        assert s.khi_nao == "Khi gặp bao-gia."

    def test_thieu_mo_ta_thi_noi_ro_la_thieu(self, kho, tmp_path) -> None:
        """Im lang o day nghia la mot skill nam trong muc luc voi mot dong trong
        — model se khong bao gio goi no, va khong ai biet vi sao."""
        d = tmp_path / "skills" / "khong-mo-ta"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: x\n---\n\nThân bài.\n", encoding="utf-8")
        s = doc_skill(d)
        assert "thiếu mô tả" in s.mo_ta


class TestCongDuyet:
    def test_skill_nguoi_viet_duoc_nap_ngay(self, kho, tmp_path) -> None:
        _viet(tmp_path / "skills", "tra-cuu", nguon="nguoi")
        k = KhoSkill(kho)
        k.nap()
        assert [s.ten for s in k.duoc_nap()] == ["tra-cuu"]

    def test_skill_BOT_TU_SINH_phai_cho_duyet(self, kho, tmp_path) -> None:
        """Bot gap rao can, viet mot skill mo ta cach vuot rao, roi lan sau doc
        chinh skill do nhu huong dan. Khong co cong nay thi ba lop guard o
        `harness/turn.py` chi con la mot loi de nghi."""
        _viet(tmp_path / "skills", "tu-sinh", nguon="tu_sinh")
        k = KhoSkill(kho)
        k.nap()
        assert k.duoc_nap() == []
        assert [s.ten for s in k.cho_duyet()] == ["tu-sinh"]

    def test_skill_cho_duyet_KHONG_hien_trong_muc_luc(self, kho, tmp_path) -> None:
        """Biet no ton tai la mot nua duong toi viec dung no."""
        _viet(tmp_path / "skills", "tu-sinh", nguon="tu_sinh")
        k = KhoSkill(kho)
        k.nap()
        assert "tu-sinh" not in k.render_muc_luc()

    def test_skill_cho_duyet_KHONG_doc_duoc(self, kho, tmp_path) -> None:
        _viet(tmp_path / "skills", "tu-sinh", nguon="tu_sinh")
        k = KhoSkill(kho)
        k.nap()
        assert k.doc("tu-sinh") is None

    def test_trang_thai_tat_thi_khong_nap(self, kho, tmp_path) -> None:
        _viet(tmp_path / "skills", "da-tat", trang_thai="tat")
        k = KhoSkill(kho)
        k.nap()
        assert k.duoc_nap() == []


class TestMucLuc:
    def test_muc_luc_KHONG_chua_than_bai(self, kho, tmp_path) -> None:
        """Ca ly do `doc_skill` ton tai. Nhoi than bai vao prompt la vai nghin
        token moi luot cho thu dung toi mot lan trong muoi."""
        _viet(tmp_path / "skills", "bao-gia")
        k = KhoSkill(kho)
        k.nap()
        muc_luc = k.render_muc_luc()
        assert "bao-gia" in muc_luc
        assert "BƯỚC BÍ MẬT" not in muc_luc

    def test_doc_skill_thi_LAY_DUOC_than_bai(self, kho, tmp_path) -> None:
        _viet(tmp_path / "skills", "bao-gia")
        k = KhoSkill(kho)
        k.nap()
        assert "BƯỚC BÍ MẬT" in k.doc("bao-gia").than_bai

    def test_kho_rong_thi_muc_luc_rong(self, kho) -> None:
        """Chuoi rong chu khong phai mot tieu de "# Ky nang" trong — mot khoi
        thua van la mot chuoi khac, va no lam vo diem cache."""
        k = KhoSkill(kho)
        k.nap()
        assert k.render_muc_luc() == ""

    def test_ten_la_khong_thoat_duoc_thu_muc(self, kho, tmp_path) -> None:
        _viet(tmp_path / "skills", "bao-gia")
        k = KhoSkill(kho)
        k.nap()
        for xau in ("../../../etc/passwd", "..", "bao-gia/../..", "skills/bao-gia"):
            assert k.doc(xau) is None


class TestMucLucKhopVoiCongCu:
    def test_cong_cu_doc_skill_CO_THAT_trong_registry(self) -> None:
        """Ban goc (C:\\TOM) bao model "doc file skills/<ten>/SKILL.md bang
        doc_trang" — nhung doc_trang chi quet kho tri thuc, con skills/ la thu
        muc anh em. Model thay ten skill va khong bao gio mo duoc than bai.

        Test nay canh dung viec do: muc luc nhac toi cong cu nao thi cong cu do
        phai ton tai va phai mo cho nguoi la.
        """
        from agent_cskh.tools import default_registry

        ten = {t.name for t in default_registry().specs("stranger")}
        assert "doc_skill" in ten
