"""Ma tran quyen — tuyen phong thu chinh chong ro ri du lieu noi bo.

Neu mot test o day do, DUNG LAI va sua truoc khi lam gi khac.
"""

from __future__ import annotations

import re

import pytest

from agent_cskh.commands.router import ALIASES, COMMANDS
from agent_cskh.config import Settings
from agent_cskh.security.whitelist import Principal, PrincipalResolver, _scope_for
from agent_cskh.store import Database

# Cac bang deu bat NOT NULL tren created_at — khong co default trong schema.
NOW = "2026-08-07T00:00:00+00:00"


def make(role: str) -> Principal:
    return Principal(
        user_id="u1",
        chat_id="c1",
        role=role,  # type: ignore[arg-type]
        visibility_scope=_scope_for(role),  # type: ignore[arg-type]
    )


class TestPhamViTruyHoi:
    def test_nguoi_la_chi_thay_public(self) -> None:
        assert make("stranger").visibility_scope == frozenset({"public"})

    def test_hoc_vien_thay_tai_lieu_khoa_hoc(self) -> None:
        assert make("student").visibility_scope == frozenset({"public", "hocvien"})

    def test_hoc_vien_KHONG_thay_noi_bo(self) -> None:
        """Thu bac cao hon nguoi la, nhung `visibility` khong cong don theo rank.

        Neu test nay do thi hoc vien dang doc duoc tai lieu noi bo cua cong ty —
        DUNG LAI va sua truoc khi lam gi khac.
        """
        assert "internal" not in make("student").visibility_scope
        assert "internal" not in make("student").visibility_sql()

    @pytest.mark.parametrize("role", ["staff", "owner"])
    def test_noi_bo_thay_tat_ca(self, role: str) -> None:
        assert make(role).visibility_scope == frozenset({"public", "hocvien", "internal"})

    def test_menh_de_sql_cua_nguoi_la_khong_chua_internal(self) -> None:
        sql = make("stranger").visibility_sql()
        assert sql == "visibility IN ('public')"
        assert "internal" not in sql
        assert "hocvien" not in sql

    def test_menh_de_sql_cua_noi_bo(self) -> None:
        assert make("owner").visibility_sql() == "visibility IN ('hocvien', 'internal', 'public')"


class TestThuBac:
    def test_thu_tu_vai(self) -> None:
        assert make("owner").at_least("staff")
        assert make("staff").at_least("student")
        assert make("student").at_least("stranger")
        assert not make("staff").at_least("owner")
        assert not make("stranger").at_least("staff")

    def test_hoc_vien_khong_phai_nhan_vien(self) -> None:
        """Hoc vien duoi staff — khong duoc dung tool ghi hay lenh noi bo."""
        hv = make("student")
        assert not hv.at_least("staff")
        assert not hv.can_write

    def test_chi_noi_bo_duoc_ghi(self) -> None:
        assert not make("stranger").can_write
        assert make("staff").can_write
        assert make("owner").can_write

    def test_nhan_dien_nguoi_la(self) -> None:
        assert make("stranger").is_stranger
        assert not make("staff").is_stranger


class TestMaTranLenh:
    """Lenh noi bo khong duoc lo ra ngoai.

    Ba tap duoi day phai phu KIN `COMMANDS`. Them lenh moi ma quen khai bao vao
    day thi `test_khong_bo_sot_lenh_nao` do — co y, de khong ai them duoc mot
    lenh ma khong dung lai nghi xem ai duoc dung no.
    """

    INTERNAL = {
        "trangthai",
        "nhan",
        "tha",
        "quen",
        "nap",
        "suckhoe",
        "lead",
        "bienlai",
        "baocao",
        "kenhcanhbao",
        "themtrang",
        "suatrang",
        "xoatrang",
        "xemtrang",
        "dstrang",
        # Tu van vien tu ghi danh trong chat rieng cua chinh ho — do la cach
        # duy nhat chung minh duoc dia chi nhan viec.
        "nhantuvan",
        "nghituvan",
        "dstuvan",
    }
    # Chi CHU BOT duoc doi noi nhan canh bao — do la thu quyet dinh du lieu
    # khach hang di ve dau.
    CHU_BOT = {"datkenhcanhbao", "xoatuvan"}
    # Vai `student` = khach da duoc nhan dien (khach quen, hoc vien, thanh vien).
    # Ho duoc nhieu hon nguoi la mot chut, nhung khong dung toi du lieu noi bo.
    KHACH_QUEN = {
        # Bo nho ma nguoi bi nho khong xem va xoa duoc la mot cai bay.
        "nhogi",
        "xoanho",
    }
    PUBLIC = {"start", "help", "lienhe", "whoami"}

    def test_moi_lenh_deu_khai_bao_quyen(self) -> None:
        for name, (handler, role) in COMMANDS.items():
            assert callable(handler), name
            assert role in {"stranger", "student", "staff", "owner"}, name

    def test_lenh_noi_bo_can_it_nhat_staff(self) -> None:
        for name in self.INTERNAL:
            assert COMMANDS[name][1] == "staff", f"{name} phai la staff"

    def test_lenh_khach_quen_dung_muc_student(self) -> None:
        for name in self.KHACH_QUEN:
            assert COMMANDS[name][1] == "student", f"{name} phai la student"

    def test_lenh_cong_khai_mo_cho_moi_nguoi(self) -> None:
        for name in self.PUBLIC:
            assert COMMANDS[name][1] == "stranger", f"{name} phai mo"

    def test_lenh_chu_bot_dung_muc_owner(self) -> None:
        for name in self.CHU_BOT:
            assert COMMANDS[name][1] == "owner", f"{name} phai la owner"

    def test_nhan_vien_khong_doi_duoc_kenh_canh_bao(self) -> None:
        """Doi kenh canh bao la doi noi du lieu khach hang chay ve."""
        nv = make("staff")
        for name in self.CHU_BOT:
            assert not nv.at_least(COMMANDS[name][1]), name

    def test_khong_bo_sot_lenh_nao(self) -> None:
        assert set(COMMANDS) == self.INTERNAL | self.KHACH_QUEN | self.PUBLIC | self.CHU_BOT

    def test_bi_danh_tro_toi_lenh_co_that(self) -> None:
        for alias, target in ALIASES.items():
            assert target in COMMANDS, f"bi danh {alias} tro toi lenh khong ton tai"

    def test_nguoi_la_bi_chan_khoi_lenh_noi_bo(self) -> None:
        stranger = make("stranger")
        for name in self.INTERNAL:
            assert not stranger.at_least(COMMANDS[name][1]), name

    def test_khach_quen_bi_chan_khoi_lenh_noi_bo(self) -> None:
        """Khach quen khong duoc xem lead hay bien lai cua nguoi khac."""
        hv = make("student")
        for name in self.INTERNAL:
            assert not hv.at_least(COMMANDS[name][1]), name

    def test_nguoi_la_bi_chan_khoi_lenh_khach_quen(self) -> None:
        stranger = make("stranger")
        for name in self.KHACH_QUEN:
            assert not stranger.at_least(COMMANDS[name][1]), name


class TestKenhNhanNoiDungNoiBo:
    """Ai duoc nhan canh bao. Sai o day la lo du lieu khach cho nguoi ngoai.

    Canh bao va nhac handoff mang tom tat khach hoi gi va chat_id cua ho. Neu
    ALERT_CHAT_ID tro nham vao mot khach hang, bot se ke chuyen khach A cho
    khach B. Mac dinh phai la TU CHOI.
    """

    @pytest.fixture
    async def resolver(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            Settings, "db_path", property(lambda _self: tmp_path / "t.db"), raising=False
        )
        s = Settings(_env_file=None, owner_user_ids=["chu_bot"])
        db = Database(s)
        await db.connect()
        yield PrincipalResolver(s, db), db
        await db.close()

    async def test_chu_bot_duoc_nhan(self, resolver) -> None:
        r, _ = resolver
        assert await r.la_kenh_noi_bo("chu_bot")

    async def test_nguoi_la_bi_tu_choi(self, resolver) -> None:
        r, _ = resolver
        assert not await r.la_kenh_noi_bo("mot_khach_hang_nao_do")

    async def test_chuoi_rong_bi_tu_choi(self, resolver) -> None:
        r, _ = resolver
        assert not await r.la_kenh_noi_bo("")
        assert not await r.la_kenh_noi_bo("   ")

    async def test_staff_trong_bang_principals_duoc_nhan(self, resolver) -> None:
        r, db = resolver
        await db.execute(
            "INSERT INTO principals (user_id, role, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("nv1", "staff", NOW, NOW),
        )
        assert await r.la_kenh_noi_bo("nv1")

    async def test_nguoi_co_trong_bang_nhung_van_la_stranger_thi_bi_tu_choi(self, resolver) -> None:
        """Co ten trong bang khong dong nghia voi du tin cay."""
        r, db = resolver
        await db.execute(
            "INSERT INTO principals (user_id, role, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("kh1", "stranger", NOW, NOW),
        )
        assert not await r.la_kenh_noi_bo("kh1")

    async def test_nhom_tin_cay_duoc_nhan(self, resolver) -> None:
        r, db = resolver
        await db.execute(
            "INSERT INTO trusted_chats (chat_id, role, created_at) VALUES (?, ?, ?)",
            ("nhom_noi_bo", "staff", NOW),
        )
        assert await r.la_kenh_noi_bo("nhom_noi_bo")


class TestHelpKhongTroi:
    """/help phai theo kip bang lenh — ca hai chieu.

    Mot lenh khong ai biet la mot lenh khong ton tai. Mot lenh duoc quang cao ma
    da bi go la mot cau tra loi sai giua cuoc tro chuyen. Ca hai deu la kieu hong
    im lang: bo test van xanh, chi co nguoi dung la vap.
    """

    # /start va /help khong tu quang cao — biet ro va co y.
    KHONG_CAN_QUANG_CAO = {"start", "help"}
    # Bi danh tieng Anh, khong phai lenh chinh.
    from agent_cskh.commands.router import ALIASES

    # Dau / phai dung dau dong hoac sau khoang trang. Khong co rang buoc nay thi
    # "anh/chi" bi doc thanh lenh "/ch" — va test se to cao mot loi khong co that.
    _LENH = re.compile(r"(?<![^\s•])/([a-z]+)")

    def _help_day_du(self) -> str:
        """Gom ca ban ngan lan cac nhom tra sau. Mot lenh chi nam trong nhom van
        la mot lenh tim duoc — mien la co duong den no."""
        from agent_cskh.commands.public import (
            HELP_CHU_DE,
            HELP_HOC_VIEN,
            HELP_INTERNAL,
            HELP_PUBLIC,
        )

        return HELP_PUBLIC + HELP_INTERNAL + HELP_HOC_VIEN + "".join(HELP_CHU_DE.values())

    def test_moi_lenh_noi_bo_deu_duoc_nhac_toi(self) -> None:
        h = self._help_day_du()
        thieu = [
            n
            for n, (_, role) in COMMANDS.items()
            if role in ("staff", "owner") and n not in self.KHONG_CAN_QUANG_CAO and f"/{n}" not in h
        ]
        assert not thieu, f"lệnh nội bộ không ai biết: {thieu}"

    def test_help_khong_quang_cao_lenh_da_bi_go(self) -> None:
        hop_le = set(COMMANDS) | set(self.ALIASES)
        nhac_toi = set(self._LENH.findall(self._help_day_du()))
        assert not (nhac_toi - hop_le), f"/help nhắc lệnh không tồn tại: {nhac_toi - hop_le}"

    def test_hoc_vien_chi_thay_MOT_NHUM_NHO_lenh(self) -> None:
        """Hoc vien nhan tin nhu noi chuyen, khong ai hoc thuoc menu.

        Do chin lenh ra truoc mat ho khong lam ho manh hon — no lam ho tuong
        phai nho lenh moi dung duoc bot, roi thoi khong nhan nua. Nhung viec con
        lai bot lam duoc bang loi; xem khoi _HOC_VIEN trong prompt.
        """
        from agent_cskh.commands.public import HELP_HOC_VIEN

        assert len(set(self._LENH.findall(HELP_HOC_VIEN))) <= 5

    def test_ban_ngan_noi_bo_khong_do_ca_bang_lenh_ra(self) -> None:
        """Ba muoi lenh trong mot buc tuong chu thi khong ai doc — va thu bi bo
        qua khong phai nhung lenh hiem, ma la CA DANH SACH."""
        from agent_cskh.commands.public import HELP_INTERNAL

        assert len(set(self._LENH.findall(HELP_INTERNAL))) <= 12

    def test_moi_nhom_tra_sau_deu_co_duong_den_tu_ban_ngan(self) -> None:
        """Mot nhom khong duoc nhac toi la mot nhom khong ton tai."""
        from agent_cskh.commands.public import HELP_CHU_DE, HELP_INTERNAL

        for nhom in HELP_CHU_DE:
            assert f"/help {nhom}" in HELP_INTERNAL, f"nhóm '{nhom}' không ai tìm ra"


class TestPersonaCoDuThanhPhan:
    """`persona.md` nap vao MOI system prompt. No khong co test hanh vi nao —
    kiem chung that phai chay `scripts/thu_giong.py` va doc bang mat.

    Nhung vai thu la RANG BUOC, khong phai van phong, va chung phai con o do:
    mot ban persona bi viet lai thieu mat muc "khong bao gia" la mot lo hong
    that, khong phai mot lua chon giong dieu.

    DAY LA LOP CHAN CHINH CHONG VIEC CODING AGENT VIET LAI PERSONA. Agent duoc
    giao viec "dien persona theo loi ke cua chu doanh nghiep" rat de sinh ra mot
    ban sach se, dung giong, va rot mat ba dong ranh gioi — vi ba dong do khong
    nam trong cau tra loi cua ai ca. Test nay giu chung lai.
    """

    def _persona(self) -> str:
        from agent_cskh.config import Settings

        return (Settings().knowledge_dir / "persona.md").read_text(encoding="utf-8")

    @pytest.mark.parametrize(
        "phai_co",
        [
            "KHÔNG báo giá",  # ranh gioi tien bac
            "Xác nhận đã nhận tiền",  # ranh gioi thanh toan
            "doc_trang",  # bat buoc tra kho truoc khi tra loi
            "Đừng đoán",  # khong doan gioi tinh
            "tin điều gì",  # quan diem cua chu — thu tao ra tinh cach
        ],
    )
    def test_khong_mat_rang_buoc_nao(self, phai_co: str) -> None:
        assert phai_co.lower() in self._persona().lower(), f"persona thiếu: {phai_co}"

    def test_co_danh_sach_dau_hieu_van_AI(self) -> None:
        """Danh sach nay la thu duy nhat bien "dung viet nhu AI" thanh mot dieu
        kiem duoc. Bo no di thi loi dan quay ve mot tinh tu."""
        from agent_cskh.wiki import strip_accents
        from scripts.thu_giong import DAU_HIEU_AI

        phang = strip_accents(self._persona().lower())
        thieu = [d for d in DAU_HIEU_AI if d not in phang]
        assert not thieu, f"script kiểm dấu hiệu mà persona không cấm: {thieu}"
