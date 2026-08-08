"""Canh bao khi model chet.

Bai hoc 07/08/2026: khoa Anthropic bi thu hoi. Bot van chay, Zalo van khoe, log
van chay — nhung moi luot deu 401 va moi khach chi nhan duoc cau "he thong dang
truc trac". Khong ai biet cho den khi co nguoi ngoi go thu.

Te hon nua: chinh cau du phong do hua "em da bao cho anh/chi phu trach roi",
trong khi khong he co ai duoc bao. Job nay lam cho loi hua ay thanh su that.
"""

from __future__ import annotations

import pytest

from agent_cskh.config import Settings
from agent_cskh.health import Health
from agent_cskh.scheduler.runner import NGUONG_LOI_MODEL, Scheduler

CHAT_CHU = "chat_cua_chu"


class ClientGia:
    def __init__(self) -> None:
        self.da_gui: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str) -> list[str]:
        self.da_gui.append((chat_id, text))
        return ["msg_1"]


class QuotaGia:
    async def count_sent(self, n: int) -> None:
        return None


def _scheduler(health_model: Health) -> tuple[Scheduler, ClientGia]:
    client = ClientGia()
    s = Scheduler(
        Settings(alert_chat_id=CHAT_CHU),
        client=client,  # type: ignore[arg-type]
        repo=None,  # type: ignore[arg-type]
        quota=QuotaGia(),  # type: ignore[arg-type]
        health=Health(ten="Zalo"),
        health_model=health_model,
    )
    return s, client


def _hong(so_loi: int, mo_ta: str = "[claude] HTTP 401") -> Health:
    h = Health(ten="Claude")
    for _ in range(so_loi):
        h.ghi_loi(mo_ta)
    return h


class TestCanhModel:
    @pytest.mark.asyncio
    async def test_du_so_loi_thi_bao_chu(self) -> None:
        sched, client = _scheduler(_hong(NGUONG_LOI_MODEL))
        await sched._canh_model()

        assert len(client.da_gui) == 1
        chat_id, text = client.da_gui[0]
        assert chat_id == CHAT_CHU
        # Canh bao phai noi duoc NGUYEN NHAN, khong chi "co loi".
        assert "401" in text
        assert "ANTHROPIC_API_KEY" in text

    @pytest.mark.asyncio
    async def test_chua_du_nguong_thi_im(self) -> None:
        """Mot hai luot loi la binh thuong — mang chap chon, model qua tai."""
        sched, client = _scheduler(_hong(NGUONG_LOI_MODEL - 1))
        await sched._canh_model()

        assert client.da_gui == []

    @pytest.mark.asyncio
    async def test_khong_spam(self) -> None:
        """Khoa chet thi MOI luot deu loi. Bao mot lan, khong bao moi 5 phut."""
        h = _hong(NGUONG_LOI_MODEL)
        sched, client = _scheduler(h)
        for _ in range(5):
            h.ghi_loi("[claude] HTTP 401")
            await sched._canh_model()

        assert len(client.da_gui) == 1

    @pytest.mark.asyncio
    async def test_song_lai_thi_bao_duoc_lan_sau(self) -> None:
        """Thay khoa moi -> lan hong ke tiep phai bao lai, khong im vinh vien."""
        h = _hong(NGUONG_LOI_MODEL)
        sched, client = _scheduler(h)
        await sched._canh_model()

        h.ghi_thanh_cong()  # chu da thay khoa
        assert h.so_loi_lien_tiep == 0
        assert not h.da_bao_mat_ket_noi

        for _ in range(NGUONG_LOI_MODEL):
            h.ghi_loi("[claude] HTTP 529")
        await sched._canh_model()

        assert len(client.da_gui) == 2

    @pytest.mark.asyncio
    async def test_gui_that_bai_thi_khong_danh_dau_da_bao(self) -> None:
        """Neu canh bao khong den noi thi phai thu lai lan sau, khong nuot."""
        h = _hong(NGUONG_LOI_MODEL)
        sched, _ = _scheduler(h)

        async def gui_hong(chat_id: str, text: str) -> list[str]:
            raise RuntimeError("Zalo tu choi")

        sched._client.send_message = gui_hong  # type: ignore[method-assign]
        await sched._canh_model()

        assert not h.da_bao_mat_ket_noi

    @pytest.mark.asyncio
    async def test_chua_dat_alert_chat_id_thi_khong_no(self) -> None:
        """Bot moi cai chua dien ALERT_CHAT_ID — job khong duoc nem loi."""
        h = _hong(NGUONG_LOI_MODEL)
        sched = Scheduler(
            Settings(alert_chat_id=""),
            client=ClientGia(),  # type: ignore[arg-type]
            repo=None,  # type: ignore[arg-type]
            quota=QuotaGia(),  # type: ignore[arg-type]
            health=Health(),
            health_model=h,
        )
        await sched._canh_model()

        assert not h.da_bao_mat_ket_noi


class ResolverGia:
    def __init__(self, noi_bo: bool) -> None:
        self._noi_bo = noi_bo
        self.da_hoi: list[str] = []

    async def la_kenh_noi_bo(self, chat_id: str) -> bool:
        self.da_hoi.append(chat_id)
        return self._noi_bo


class TestKhongLoNoiDungNoiBo:
    """Canh bao mang noi dung noi bo — ke ca tom tat khach hang va chat_id ho.

    Dat nham ALERT_CHAT_ID vao mot khach hang thi vua lo du lieu khach khac cho
    ho, vua lo cach van hanh ben trong. Zalo tra 410 cho chat_id khong ton tai
    nen go nham thuong hong an toan; nguy hiem la go nham ma van trung mot chat
    CO THAT.
    """

    def _voi_resolver(self, noi_bo: bool) -> tuple[Scheduler, ClientGia, ResolverGia]:
        client = ClientGia()
        resolver = ResolverGia(noi_bo)
        sched = Scheduler(
            Settings(alert_chat_id=CHAT_CHU),
            client=client,  # type: ignore[arg-type]
            repo=None,  # type: ignore[arg-type]
            quota=QuotaGia(),  # type: ignore[arg-type]
            health=Health(ten="Zalo"),
            health_model=_hong(NGUONG_LOI_MODEL),
            resolver=resolver,  # type: ignore[arg-type]
        )
        return sched, client, resolver

    @pytest.mark.asyncio
    async def test_kenh_la_thi_khong_gui_gi_ca(self) -> None:
        sched, client, resolver = self._voi_resolver(noi_bo=False)
        await sched._canh_model()

        assert client.da_gui == [], "da gui noi dung noi bo cho nguoi ngoai"
        assert resolver.da_hoi == [CHAT_CHU], "khong he kiem tra nguoi nhan"

    @pytest.mark.asyncio
    async def test_kenh_noi_bo_thi_gui_binh_thuong(self) -> None:
        sched, client, _ = self._voi_resolver(noi_bo=True)
        await sched._canh_model()

        assert len(client.da_gui) == 1

    @pytest.mark.asyncio
    async def test_nhac_handoff_cung_qua_cua_nay(self) -> None:
        """Nhac handoff kem tom tat khach — phai bi chan y het canh bao model."""
        sched, client, _ = self._voi_resolver(noi_bo=False)
        await sched._bao_chu("⏰ CÓ 1 KHÁCH ĐANG CHỜ — anh Minh hỏi báo giá gói A")

        assert client.da_gui == []

    @pytest.mark.asyncio
    async def test_bi_chan_thi_khong_danh_dau_da_bao(self) -> None:
        """Chan khong duoc bien thanh 'da bao roi' — sua cau hinh xong phai bao lai."""
        sched, _, _ = self._voi_resolver(noi_bo=False)
        await sched._canh_model()

        assert not sched._health_model.da_bao_mat_ket_noi


class TestHaiNhipTimTachRoi:
    def test_moi_ben_tu_xung_ten(self) -> None:
        assert "Gọi Zalo thành công" in Health(ten="Zalo").tom_tat()
        assert "Gọi Claude thành công" in Health(ten="Claude").tom_tat()

    def test_loi_cuoi_hien_trong_tom_tat(self) -> None:
        h = Health(ten="Claude")
        h.ghi_loi("[claude] HTTP 401")
        assert "401" in h.tom_tat()

    def test_thanh_cong_xoa_loi_cuoi(self) -> None:
        h = Health(ten="Claude")
        h.ghi_loi("[claude] HTTP 401")
        h.ghi_thanh_cong()
        assert h.loi_cuoi == ""
        assert "Lỗi gần nhất" not in h.tom_tat()
