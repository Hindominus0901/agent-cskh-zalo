"""Client gia cho kenh web.

`TurnDispatcher` duoc viet de noi chuyen voi `ZaloClient`. Thay vi sua dispatcher
(no da duoc test ky va dang chay that tren Zalo), ta lam mot vat the co CUNG BE
MAT nhung khong goi Zalo: `send_message` bo cau tra loi vao hop thu trong RAM,
roi tang HTTP lay ra tra ve cho trinh duyet.

Day la ly do goi `transport/base.py` ton tai: moi an so ve Zalo bi nhot trong do,
nen phan con lai cua he thong khong biet — va khong can biet — minh dang tra loi
ai qua duong nao.
"""

from __future__ import annotations

import asyncio
from typing import Any

from agent_cskh.config import Settings
from agent_cskh.logging_setup import get_logger
from agent_cskh.transport.zalo_client import split_text

log = get_logger(__name__)


class HopThu:
    """Cau tra loi cua mot luot, cho HTTP den lay.

    `xong` duoc dispatcher bat len sau khi xu ly xong luot — nho no ma tang HTTP
    biet khi nao duoc tra ve, thay vi phai doan bang cach cho mot khoang thoi gian.
    """

    __slots__ = ("cac_cau", "xong")

    def __init__(self) -> None:
        self.cac_cau: list[str] = []
        self.xong = asyncio.Event()


class KhachWeb:
    """Duck-type `ZaloClient` — chi phan ma dispatcher that su dung toi.

    KHONG ke thua ZaloClient: ke thua thi moi lan Zalo them phuong thuc moi, lop
    nay lang le thua huong mot thu no khong lam duoc, va loi se hien ra o tan
    trinh duyet cua khach.
    """

    def __init__(self, settings: Settings, zalo: Any | None = None) -> None:
        self._s = settings
        self._hop: dict[str, HopThu] = {}
        # Duong bao cho NGUOI THAT. Xem `send_message`.
        self._zalo = zalo

    # ---------- phia web ----------
    def mo_hop(self, chat_id: str) -> HopThu:
        hop = HopThu()
        self._hop[chat_id] = hop
        return hop

    def dong_hop(self, chat_id: str) -> None:
        self._hop.pop(chat_id, None)

    # ---------- be mat giong ZaloClient ----------
    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        parse_mode: str | None = None,
        reply_to_message_id: str | None = None,
    ) -> list[str]:
        hop = self._hop.get(chat_id)
        if hop is None:
            # Khong phai phien web dang mo. Hai truong hop rat khac nhau:
            #
            # 1. `chat_id` KHONG bat dau bang "web:" -> day la tin gui cho NGUOI
            #    THAT (kenh canh bao, tu van vien) — vi du "CAN NGUOI TIEP QUAN"
            #    khi khach web hoi cau bot khong tra loi duoc.
            #
            #    Neu bo tin nay di thi chu shop KHONG BAO GIO BIET co khach web
            #    dang cho, va khach thi vua duoc hua "bên em sẽ liên hệ lại".
            #    Mot loi hua khong ai thuc hien te hon la khong hua.
            #
            #    Nen ta chuyen tiep sang Zalo neu bot Zalo da duoc cau hinh.
            #
            # 2. `chat_id` bat dau bang "web:" -> phien da dong (khach da tat
            #    tab). Khong co cho nao de gui. Bo di, nhung ghi log.
            if not chat_id.startswith("web:") and self._zalo is not None:
                try:
                    return await self._zalo.send_message(chat_id, text)
                except Exception as e:  # noqa: BLE001 - khong duoc lam hong luot cua khach
                    log.warning("web_khong_bao_duoc_zalo", chat_id=chat_id[:12], error=str(e))
                    return []
            log.warning("web_tra_loi_khong_ai_nhan", chat_id=chat_id[:12])
            return []

        # Van cat theo `max_reply_chars`. Trinh duyet khong co gioi han 2000 ky
        # tu nhu Zalo, nhung giu nguyen cach cat de cau tra loi hien ra GIONG
        # NHAU o ca hai kenh — chu shop chi phai kiem tra noi dung mot lan.
        phan = split_text(text, self._s.max_reply_chars)
        hop.cac_cau.extend(phan)
        return [f"web-{len(hop.cac_cau)}"]

    async def send_chat_action(self, chat_id: str, action: str = "typing") -> None:
        """Web hien dau ba cham o phia trinh duyet, khong can goi gi len server."""
        return None

    async def get_me(self) -> dict[str, Any]:
        return {"id": "web", "display_name": self._s.bot_name or "Bot"}

    async def aclose(self) -> None:
        return None

    async def close(self) -> None:
        return None
