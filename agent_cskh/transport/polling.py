"""Long-polling qua getUpdates.

Canh bao van hanh: Zalo khong co `offset`. Long-poll tieu thu tin ngay khi tra ve,
nen giao hang la at-most-once — tin gui luc bot tat coi nhu MAT. Cung vi vay
TUYET DOI khong chay hai tien trinh polling song song: tin se bi chia ngau nhien
giua hai ben.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from agent_cskh.config import Settings
from agent_cskh.health import Health
from agent_cskh.logging_setup import get_logger
from agent_cskh.transport.base import InboundEvent, Transport
from agent_cskh.transport.normalize import normalize
from agent_cskh.transport.zalo_client import ZaloAPIError, ZaloClient

log = get_logger(__name__)

POLL_TIMEOUT = 30
# Backoff khi Zalo tu choi lien tuc, de khong dot quota bang chinh cac lan thu lai.
BACKOFF_MIN = 1.0
BACKOFF_MAX = 60.0


class PollingTransport(Transport):
    def __init__(
        self, settings: Settings, client: ZaloClient, health: Health | None = None
    ) -> None:
        self._s = settings
        self._client = client
        self._health = health or Health()
        self._running = False
        self._backoff = BACKOFF_MIN

    async def start(self) -> None:
        # getUpdates khong hoat dong neu webhook dang bat.
        try:
            await self._client.delete_webhook()
            log.info("webhook_da_xoa_truoc_khi_polling")
        except ZaloAPIError as e:
            log.debug("delete_webhook_bo_qua", error=str(e))
        self._running = True
        log.info("polling_bat_dau", timeout=POLL_TIMEOUT)

    async def stop(self) -> None:
        self._running = False
        log.info("polling_dung")

    async def stream(self) -> AsyncIterator[InboundEvent]:
        while self._running:
            try:
                body = await self._client.get_updates(timeout=POLL_TIMEOUT)
            except ZaloAPIError as e:
                self._health.ghi_loi()
                if e.is_quota:
                    log.error("het_quota_zalo", description=e.description)
                    await asyncio.sleep(BACKOFF_MAX)
                    continue
                await self._sleep_backoff()
                continue
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                self._health.ghi_loi()
                log.exception("polling_loi_khong_luong_truoc", error=str(e))
                await self._sleep_backoff()
                continue

            if body is None:
                # get_updates tra None khi 5xx / body khong phai JSON / dut mang —
                # do chinh la trieu chung cua su co 05/08/2026. Phai tinh la LOI,
                # khong phai "khong co tin", neu khong canh bao mat ket noi se
                # khong bao gio no.
                #
                # PHAI ngu truoc khi thu lai. get_updates() nuot loi mang roi tra
                # None NGAY LAP TUC — khong con long-poll 30 giay giu nhip nua. Khong
                # ngu thi vong lap quay het toc do: ngay 05/08/2026 mat DNS 5 giay
                # da sinh hang nghin dong log va mot loi CPU chay 100%.
                self._health.ghi_loi()
                await self._sleep_backoff()
                continue

            # Chi reset backoff khi that su noi duoc toi Zalo.
            self._backoff = BACKOFF_MIN
            self._health.ghi_thanh_cong()
            if not body:
                continue
            event = normalize(body)
            if event is None:
                continue
            if event.is_bot:
                log.debug("bo_qua_tin_tu_bot", chat_id=event.chat_id)
                continue

            self._health.ghi_su_kien()
            log.info("nhan_su_kien", summary=event.summary())
            yield event

    async def _sleep_backoff(self) -> None:
        await asyncio.sleep(self._backoff)
        self._backoff = min(self._backoff * 2, BACKOFF_MAX)
