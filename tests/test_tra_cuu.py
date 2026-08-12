"""Che do `tra_cuu` — bot tra loi khong can LLM.

Day la duong di MAC DINH cua template, nen no phai duoc canh chat nhu duong `ai`.
Ba thu quan trong nhat o day:

  1. Nguong phan dinh dung — khong tra loi bua khi chua chac
  2. Quyen van do THU MUC quyet dinh, y het che do `ai`
  3. Cau khong tra loi duoc phai duoc GHI LAI nguyen van (vong lap hoc)
"""

from __future__ import annotations

import pytest

from agent_cskh.config import Settings
from agent_cskh.tra_cuu import DinhTuyenTraCuu, phan_dinh
from agent_cskh.tra_cuu.nguong import CHENH_LECH_RO_RANG, NGUONG_CHAC, NGUONG_HOI_LAI
from agent_cskh.wiki import WikiPage, WikiStore

CONG_KHAI = frozenset({"public"})
NOI_BO = frozenset({"public", "hocvien", "internal"})


def _trang(slug: str, tieu_de: str, tom_tat: str, than: str, tu_khoa: list[str]) -> str:
    kh = ", ".join(f'"{k}"' for k in tu_khoa)
    return (
        f"---\ntitle: {tieu_de}\nsummary: {tom_tat}\ntu_khoa: [{kh}]\n---\n\n{than}\n"
    )


@pytest.fixture
def wiki(tmp_path, monkeypatch):
    monkeypatch.setattr(
        Settings, "knowledge_dir", property(lambda _s: tmp_path / "knowledge"), raising=False
    )
    s = Settings(_env_file=None)
    goc = s.knowledge_dir / "wiki"
    for muc in ("public", "hocvien", "internal"):
        (goc / muc).mkdir(parents=True, exist_ok=True)

    (goc / "public" / "bang-gia.md").write_text(
        _trang(
            "bang-gia",
            "Bảng giá",
            "Giá các gói dịch vụ",
            "Gói cơ bản 5 triệu. Gói nâng cao 12 triệu.",
            ["bao nhieu tien", "gia", "chi phi", "mac khong"],
        ),
        encoding="utf-8",
    )
    (goc / "public" / "bao-hanh.md").write_text(
        _trang(
            "bao-hanh",
            "Chính sách bảo hành",
            "Bảo hành 24 tháng",
            "Bảo hành 24 tháng kể từ ngày mua.",
            ["bao hanh", "hong thi sao", "doi tra"],
        ),
        encoding="utf-8",
    )
    # Trang KHONG khai `tu_khoa` — cho co that, va la cach duy nhat de roi vao
    # vung "khong chac lam": khong co cum khai bao thi khong an thuong +25.
    (goc / "public" / "uu-dai.md").write_text(
        _trang(
            "uu-dai",
            "Ưu đãi",
            "Chương trình đang chạy",
            "Giảm 10% cho đơn thứ hai.",
            [],
        ),
        encoding="utf-8",
    )
    (goc / "internal" / "gia-von.md").write_text(
        _trang(
            "gia-von",
            "Giá vốn",
            "Giá vốn từng gói",
            "Gói cơ bản giá vốn 1,2 triệu.",
            ["gia von", "lai bao nhieu"],
        ),
        encoding="utf-8",
    )

    w = WikiStore(s)
    w.reload()
    return w


class TestPhanDinhNguong:
    """Ham thuan — khong can kho, khong can gi ca."""

    def _kq(self, *diem: int) -> list[tuple[int, WikiPage]]:
        return [
            (d, WikiPage(slug=f"t{i}", visibility="public", title=f"T{i}", summary="", body=""))
            for i, d in enumerate(diem)
        ]

    def test_khong_khop_gi_thi_khong_biet(self) -> None:
        assert phan_dinh([]) == "khong_biet"

    def test_diem_qua_thap_thi_khong_biet(self) -> None:
        assert phan_dinh(self._kq(NGUONG_HOI_LAI - 1)) == "khong_biet"

    def test_diem_lung_chung_va_NHIEU_ung_vien_thi_hoi_lai(self) -> None:
        assert phan_dinh(self._kq(NGUONG_HOI_LAI, NGUONG_HOI_LAI - 1)) == "hoi_lai"
        assert phan_dinh(self._kq(NGUONG_CHAC - 1, 5)) == "hoi_lai"

    def test_diem_lung_chung_nhung_CHI_MOT_ung_vien_thi_phong_doan(self) -> None:
        """Menu mot dong la thu vo nghia nhat co the in ra man hinh khach."""
        assert phan_dinh(self._kq(NGUONG_HOI_LAI)) == "phong_doan"
        assert phan_dinh(self._kq(NGUONG_CHAC - 1)) == "phong_doan"

    def test_diem_cao_va_hon_han_thi_tra_loi_thang(self) -> None:
        assert phan_dinh(self._kq(NGUONG_CHAC + 50, 1)) == "chac"

    def test_hai_trang_diem_sat_nhau_thi_PHAI_hoi_lai(self) -> None:
        """Diem cao ma khong hon han thi con so do khong con nghia gi.

        Hai trang 30 va 29: chon bua mot trong hai la 50% sai. Day la truong hop
        de lot nhat, va cung la truong hop lam bot tra ve mot trang chang lien
        quan voi giong dieu rat tu tin.
        """
        cao = NGUONG_CHAC + 20
        assert phan_dinh(self._kq(cao, cao - CHENH_LECH_RO_RANG + 1)) == "hoi_lai"
        assert phan_dinh(self._kq(cao, cao - CHENH_LECH_RO_RANG)) == "chac"


class TestCachLyQuyen:
    """Y het `test_wiki.py::TestCachLyQuyen`. Che do khac khong duoc lam quyen
    khac — mot trang `internal/` khong bao gio duoc ro ra qua duong nay."""

    def test_nguoi_la_khong_lay_duoc_trang_noi_bo(self, wiki) -> None:
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("giá vốn bao nhiêu", chat_id="c1", scope=CONG_KHAI)
        assert "1,2 triệu" not in kq.text

    def test_nguoi_la_khong_thay_ca_TEN_trang_noi_bo(self, wiki) -> None:
        """Danh sach hoi lai cung phai loc — lo ten trang la lo su ton tai."""
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("giá vốn", chat_id="c1", scope=CONG_KHAI)
        assert "Giá vốn" not in kq.text

    def test_noi_bo_thi_doc_duoc(self, wiki) -> None:
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("giá vốn bao nhiêu", chat_id="c1", scope=NOI_BO)
        assert "1,2 triệu" in kq.text


class TestTraLoiDung:
    def test_hoi_gia_thi_ra_bang_gia(self, wiki) -> None:
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("bảng giá bao nhiêu ạ", chat_id="c1", scope=CONG_KHAI)
        assert "5 triệu" in kq.text
        assert not kq.can_nguoi_that

    def test_tu_khoa_bat_duoc_cach_noi_khac(self, wiki) -> None:
        """Day la ly do truong `tu_khoa` ton tai.

        "mắc không" khong co mot chu nao trung voi tieu de hay than bai cua trang
        bang gia. Regex thuan se truot sach. `tu_khoa` la thu bu vao cho do — va
        no la khac biet giua mot bot dung duoc va mot bot lam khach bo di.
        """
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("cái này mắc không", chat_id="c1", scope=CONG_KHAI)
        assert "5 triệu" in kq.text

    def test_chao_hoi_khong_di_qua_tim_kiem(self, wiki) -> None:
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("chào shop", chat_id="c1", scope=CONG_KHAI)
        assert "triệu" not in kq.text
        assert not kq.can_nguoi_that


class TestHuTuKhongDuocAnDiem:
    """Do duoc 10/08/2026 khi di tron duong cua mot hoc vien that.

    Diem cham theo so lan khop, moi lan o tieu de/tom tat/tu_khoa an 5 diem.
    Nhung "khong", "co", "cho" nam rai trong tu_khoa va tieu de cua gan nhu moi
    trang, nen chung mot minh du de lat nguoc thu tu.
    """

    def test_hu_tu_khong_keo_nham_sang_trang_khac(self, wiki) -> None:
        """Cau that: "chỗ mình có ship không" tung tra ve trang bao hanh/cho ngoi
        thay vi giao hang, vi "cho" + "khong" an 15 diem con "ship" chi an 5."""
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("chỗ mình có bảo hành không", chat_id="c1", scope=CONG_KHAI)
        assert "24 tháng" in kq.text

    def test_cau_toan_hu_tu_thi_khong_doan_bua(self, wiki) -> None:
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("có không ạ", chat_id="c1", scope=CONG_KHAI)
        assert kq.can_nguoi_that


class TestCumTuKhoaKhopNguyenVan:
    """Chu doanh nghiep khai mot cum vao `tu_khoa` la ho da noi thang: khach hoi
    kieu do la hoi trang nay. Cham tung tu le thi cum do tan ra."""

    def test_cum_khai_bao_phai_thang_du_lan_trong_hu_tu(self, wiki) -> None:
        """"cái này mắc không" — "cai"/"nay"/"khong" deu la hu tu bi loc, chi con
        "mac". Neu khong co thuong cho cum khai bao thi tong diem khong du nguong
        va bot chuyen nguoi that cho mot cau ma chinh chu da day no tra loi."""
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("cái này mắc không", chat_id="c1", scope=CONG_KHAI)
        assert "5 triệu" in kq.text
        assert not kq.can_nguoi_that

    def test_cum_khong_khai_thi_van_khong_biet(self, wiki) -> None:
        """Thuong cho cum khong duoc bien thanh cai co de tra loi bua."""
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("quán có bán bánh ngọt không", chat_id="c1", scope=CONG_KHAI)
        assert kq.can_nguoi_that

    def test_cum_phai_khop_RANH_GIOI_TU_khong_phai_chuoi_con(self, wiki) -> None:
        """Bug 12/08/2026, do chinh thuong +25 nay sinh ra.

        Ban dau doi chieu bang `c in q` (chuoi con), nen `tu_khoa: ["gia"]` an
        tron 25 diem cho cau "có GIAo hàng đi Đà Nẵng không" — "gia" nam trong
        "giao". Trang bang gia thang tuyet doi moi cau hoi ve giao hang, va cau
        do khong bao gio duoc ghi vao `thieu_trang` de chu shop biet ma bo sung.

        Dung cai bay tieng Viet ma `search_scored` da canh bao ngay dong ben canh.
        """
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("bên mình có giao hàng đi Đà Nẵng không", chat_id="c1", scope=CONG_KHAI)
        assert "5 triệu" not in kq.text, "'gia' khong duoc khop vao giua 'giao'"
        assert kq.can_nguoi_that


class TestKhongBietThiGhiLai:
    """Nua kia cua vong lap hoc. Bot tu choi rat ngoan ma khong ghi lai thi chu
    bot khong bao gio biet phai viet them trang gi."""

    def test_ngoai_kho_thi_chuyen_nguoi_that(self, wiki) -> None:
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("bên mình có làm SEO website không", chat_id="c1", scope=CONG_KHAI)
        assert kq.can_nguoi_that

    def test_ghi_NGUYEN_VAN_cau_hoi_khong_tom_tat(self, wiki) -> None:
        """Chu bot can biet khach dung TU GI de dat ten trang moi. Mot ban tom
        tat lam mat dung cai thong tin do."""
        dt = DinhTuyenTraCuu(wiki)
        cau = "bên mình có làm SEO website không"
        kq = dt.tra_loi(cau, chat_id="c1", scope=CONG_KHAI)
        assert kq.cau_hoi_thieu == cau

    def test_tra_loi_duoc_thi_KHONG_ghi_thieu_trang(self, wiki) -> None:
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("bảng giá bao nhiêu ạ", chat_id="c1", scope=CONG_KHAI)
        assert kq.cau_hoi_thieu is None


class TestKhongDoanBuaKhiKhongChac:
    """Truoc 11/08/2026 cho nay dua ra mot MENU DANH SO va bao khach "nhan so
    giup em". Da bo: menu danh so cung la mot dang lenh, ma khach that khong doc
    menu — ho go tiep cau hoi cua ho.

    Te hon: con so lac cua luot truoc lam bot mo nham mot trang chang lien quan.
    Gio bot doan mot cach thanh that, va khach sua duoc trong mot luot.
    """

    def test_khong_chac_thi_noi_ro_la_dang_doan(self, wiki) -> None:
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("ưu đãi gì", chat_id="c1", scope=CONG_KHAI)
        assert "có phải" in kq.text.lower()
        assert "10%" in kq.text

    def test_chac_chan_thi_tra_loi_thang_khong_rao_don(self, wiki) -> None:
        """Chu shop khai `mac khong` vao tu_khoa nghia la ho da noi thang: hoi
        kieu do la hoi trang gia. Luc do rao don la thua."""
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("cái này mắc không", chat_id="c1", scope=CONG_KHAI)
        assert "5 triệu" in kq.text
        assert "có phải" not in kq.text.lower()

    def test_khong_con_menu_danh_so(self, wiki) -> None:
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("ưu đãi gì", chat_id="c1", scope=CONG_KHAI)
        assert "nhắn số" not in kq.text
        assert "\n1." not in kq.text

    def test_khong_giu_trang_thai_giua_cac_luot(self, wiki) -> None:
        """Khong con trang thai "dang cho chon" nen khong the ro ri giua hai
        khach, va restart cung khong mat gi."""
        dt = DinhTuyenTraCuu(wiki)
        assert not hasattr(dt, "_cho_chon")

    def test_con_so_don_doc_khong_lam_bot_mo_trang_la(self, wiki) -> None:
        """Khach go "2" ma khong co ngu canh gi thi khong duoc mo trang nao ca."""
        dt = DinhTuyenTraCuu(wiki)
        kq = dt.tra_loi("2", chat_id="c1", scope=CONG_KHAI)
        assert "24 tháng" not in kq.text
        assert "5 triệu" not in kq.text
