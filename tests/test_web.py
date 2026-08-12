"""Kenh web: widget chat tren website.

Ba dieu phai dung, xep theo muc do thiet hai neu sai:

  1. Khach web KHONG BAO GIO doc duoc `wiki/internal/` (gia von, quy trinh noi bo)
  2. Tran ngay chan that — day la thu duy nhat dung giua mot con bot cao va
     tai khoan API cua chu shop
  3. CORS chi mo cho ten mien da khai bao
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from agent_cskh.app import chon_bo_nao
from agent_cskh.commands import handle as handle_command
from agent_cskh.config import Settings
from agent_cskh.harness.dispatcher import TurnDispatcher
from agent_cskh.memory import ConversationBuffer
from agent_cskh.security import PrincipalResolver, RateLimiter
from agent_cskh.store import Database
from agent_cskh.store.repo import BoNhoRepo, ChatRepo, TuVanRepo
from agent_cskh.tools import default_registry
from agent_cskh.web.chan import NhipIP, TranNgay
from agent_cskh.web.chay import QuotaWeb
from agent_cskh.web.khach import KhachWeb
from agent_cskh.web.server import tao_app
from agent_cskh.wiki import WikiStore

GOC = "https://shop.example.com"

TRANG_CONG_KHAI = """---
title: Giờ mở cửa
summary: Bên em mở cửa 8h đến 21h mỗi ngày.
tags: [gio, mo cua]
tu_khoa: ["may gio", "mo cua"]
---

Bên em mở cửa 8h–21h tất cả các ngày trong tuần ạ.
"""

TRANG_NOI_BO = """---
title: Giá vốn
summary: Bảng giá vốn nội bộ.
tags: [gia von]
tu_khoa: ["gia von", "chiet khau toi da"]
---

Giá vốn áo thun là 45.000đ. Chiết khấu tối đa được duyệt là 30%.
"""


@pytest.fixture
async def web(tmp_path, monkeypatch):
    """Mot may chu web that, chay tren CSDL tam va kho tri thuc tam."""
    monkeypatch.setattr(
        Settings, "db_path", property(lambda _self: tmp_path / "web.db"), raising=False
    )
    kho = tmp_path / "knowledge"
    for muc in ("public", "hocvien", "internal"):
        (kho / "wiki" / muc).mkdir(parents=True, exist_ok=True)
    (kho / "wiki" / "public" / "gio-mo-cua.md").write_text(TRANG_CONG_KHAI, encoding="utf-8")
    (kho / "wiki" / "internal" / "gia-von.md").write_text(TRANG_NOI_BO, encoding="utf-8")
    monkeypatch.setattr(Settings, "knowledge_dir", property(lambda _self: kho), raising=False)

    s = Settings(
        _env_file=None,
        che_do="tra_cuu",
        web_origins=[GOC],
        web_tran_ngay=5,
        web_nhip_ip_moi_phut=100,  # tat lop IP de test tran ngay cho ro
        web_cho_giay=10,
    )

    db = Database(s)
    await db.connect()
    wiki = WikiStore(s)
    wiki.reload()
    repo = ChatRepo(db)
    khach = KhachWeb(s)

    dispatcher = TurnDispatcher(
        s,
        client=khach,  # type: ignore[arg-type]
        repo=repo,
        bo_nho=BoNhoRepo(db),
        tu_van=TuVanRepo(db),
        resolver=PrincipalResolver(s, db),
        limiter=RateLimiter(s, db),
        quota=QuotaWeb(),  # type: ignore[arg-type]
        buffer=ConversationBuffer(repo),
        router=None,  # type: ignore[arg-type]  # che do tra_cuu khong dung model
        loop=chon_bo_nao(s, wiki),
        wiki=wiki,
        registry=default_registry(s),
        command_handler=handle_command,
    )
    app = tao_app(s, dispatcher=dispatcher, khach=khach, db=db)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://thu"
    ) as client:
        yield {"client": client, "db": db, "dispatcher": dispatcher, "settings": s}

    await dispatcher.drain(grace=2.0)
    await db.close()


async def _hoi(web, text: str, **kw):
    return await web["client"].post("/api/chat", json={"text": text}, **kw)


class TestTraLoi:
    async def test_tra_loi_duoc_cau_hoi_thuong(self, web):
        r = await _hoi(web, "mấy giờ mở cửa")
        assert r.status_code == 200
        assert "8h" in " ".join(r.json()["tra_loi"])

    async def test_phat_cookie_phien(self, web):
        r = await _hoi(web, "mấy giờ mở cửa")
        assert "agent_cskh_phien" in r.cookies

    async def test_luot_khong_bao_gio_treo_vo_han(self, web):
        """Moi duong ra deu phai tra ve — ke ca duong tu choi.

        Neu mot duong nao do quen bat co `xong`, tab cua khach quay den het
        `web_cho_giay` roi moi nhan cau xin loi. Test nay chan dieu do.
        """
        r = await asyncio.wait_for(_hoi(web, "chính sách bảo hành rơi vỡ thế nào"), timeout=8)
        assert r.status_code == 200
        assert r.json()["tra_loi"]


class TestKhongRoNoiBo:
    """Lop chan quan trong nhat cua kenh web."""

    async def test_khach_web_khong_doc_duoc_trang_noi_bo(self, web):
        r = await _hoi(web, "giá vốn bao nhiêu")
        tra = " ".join(r.json()["tra_loi"])
        assert "45.000" not in tra
        assert "30%" not in tra

    async def test_khach_web_luon_la_nguoi_la(self, web):
        """Khong co duong nao nang quyen tu web — id chi la mot cookie."""
        r = await _hoi(web, "chiết khấu tối đa")
        assert "30%" not in " ".join(r.json()["tra_loi"])


class TestChanLamDung:
    async def test_cham_tran_ngay_thi_ngung_phuc_vu(self, web):
        """`web_tran_ngay=5` trong fixture."""
        ma = [(await _hoi(web, "mấy giờ mở cửa")).status_code for _ in range(7)]
        assert 503 in ma, f"trần ngày không chặn: {ma}"

    async def test_dem_ca_luot_bi_tu_choi(self, web):
        """Neu chi dem luot duoc phuc vu, ke cao thu lai vo han ma khong cham tran."""
        for _ in range(7):
            await _hoi(web, "mấy giờ mở cửa")
        st = await TranNgay(web["settings"], web["db"]).trang_thai()
        assert st.da_dung >= 7

    async def test_nhip_ip_chan_khi_go_qua_nhanh(self):
        nhip = NhipIP(moi_phut=3)
        kq = [await nhip.cho_phep("1.2.3.4") for _ in range(5)]
        assert kq[:3] == [True, True, True]
        assert kq[3] is False

    async def test_moi_ip_co_gau_rieng(self):
        nhip = NhipIP(moi_phut=1)
        assert await nhip.cho_phep("1.1.1.1") is True
        assert await nhip.cho_phep("2.2.2.2") is True


class TestCORS:
    async def test_chan_ten_mien_la(self, web):
        r = await _hoi(web, "mấy giờ mở cửa", headers={"Origin": "https://ke-la.com"})
        assert r.status_code == 403

    async def test_cho_ten_mien_da_khai(self, web):
        r = await _hoi(web, "mấy giờ mở cửa", headers={"Origin": GOC})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == GOC

    async def test_khong_co_origin_van_chay(self, web):
        """Mo thang trang thu tren chinh may chu — khong co header Origin."""
        assert (await _hoi(web, "mấy giờ mở cửa")).status_code == 200


class TestWidget:
    async def test_widget_tra_ve_js_va_tro_dung_may_chu(self, web):
        r = await web["client"].get("/widget.js")
        assert r.status_code == 200
        assert "__GOC__" not in r.text, "chua thay dia chi may chu vao widget"
        assert "/api/chat" in r.text

    async def test_health_bao_tran_con_lai(self, web):
        j = (await web["client"].get("/health")).json()
        assert j["ok"] is True
        assert j["tran"] == 5


class TestChuyenNguoiThat:
    """Tren web khong the nhan lai cho khach — nen khong duoc hua nhu tren Zalo."""

    async def test_xin_so_dien_thoai_thay_vi_bao_cho(self, web):
        r = await _hoi(web, "chính sách bảo hành rơi vỡ thế nào")
        tra = " ".join(r.json()["tra_loi"]).lower()
        assert "số điện thoại" in tra or "zalo" in tra, tra

    async def test_khong_hua_cho_tren_web(self, web):
        """Cau cua Zalo — 'mình chờ giúp em' — la loi hua khong giu duoc o web."""
        r = await _hoi(web, "chính sách bảo hành rơi vỡ thế nào")
        assert "chờ giúp em trong giờ làm việc" not in " ".join(r.json()["tra_loi"])

    async def test_zalo_van_giu_cau_cu(self):
        from agent_cskh.harness.ban_giao import MSG_DA_CHUYEN, loi_da_chuyen

        assert loi_da_chuyen("1234567890") == MSG_DA_CHUYEN


class TestBaoChuShop:
    """Canh bao 'can nguoi tiep quan' phai di duoc sang Zalo, khong duoc roi vao hu khong."""

    async def test_tin_cho_nguoi_that_duoc_chuyen_sang_zalo(self):
        da_gui: list[tuple[str, str]] = []

        class ZaloGia:
            async def send_message(self, chat_id: str, text: str, **_kw):
                da_gui.append((chat_id, text))
                return ["1"]

        k = KhachWeb(Settings(_env_file=None), zalo=ZaloGia())
        await k.send_message("admin", "🔔 CẦN NGƯỜI TIẾP QUẢN")
        assert da_gui == [("admin", "🔔 CẦN NGƯỜI TIẾP QUẢN")]

    async def test_phien_web_da_dong_thi_khong_gui_sang_zalo(self):
        """Khong duoc lay tin danh cho khach roi ban vao Zalo cua chu shop."""
        da_gui: list[str] = []

        class ZaloGia:
            async def send_message(self, chat_id: str, text: str, **_kw):
                da_gui.append(chat_id)
                return ["1"]

        k = KhachWeb(Settings(_env_file=None), zalo=ZaloGia())
        await k.send_message("web:da-dong", "câu trả lời cho khách")
        assert da_gui == []

    async def test_zalo_hong_khong_lam_chet_luot(self):
        class ZaloHong:
            async def send_message(self, *_a, **_kw):
                raise RuntimeError("mạng hỏng")

        k = KhachWeb(Settings(_env_file=None), zalo=ZaloHong())
        assert await k.send_message("admin", "cảnh báo") == []


class TestCauHinh:
    def test_bo_dau_gach_cuoi_trong_origin(self):
        """`Origin` cua trinh duyet khong bao gio co `/` cuoi — khai co la khong khop."""
        s = Settings(_env_file=None, web_origins=["https://shop.com/"])
        assert s.web_origins == ["https://shop.com"]

    def test_tach_theo_dau_phay(self):
        s = Settings(_env_file=None, web_origins="https://a.com, https://b.com")
        assert s.web_origins == ["https://a.com", "https://b.com"]


class TestKhachWeb:
    async def test_cat_cau_dai_giong_zalo(self):
        s = Settings(_env_file=None, max_reply_chars=100)
        k = KhachWeb(s)
        hop = k.mo_hop("web:x")
        await k.send_message("web:x", "a" * 250)
        assert len(hop.cac_cau) > 1

    async def test_khong_no_khi_hop_da_dong(self):
        """Job dinh ky ban tin toi mot phien da dong — phai bo qua, khong duoc chet."""
        k = KhachWeb(Settings(_env_file=None))
        assert await k.send_message("web:khong-ton-tai", "xin chào") == []
