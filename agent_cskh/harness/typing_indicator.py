"""Bao "dang nhap..." trong suot mot luot.

Zalo khong co editMessageText nen khong the stream tung chu. sendChatAction la
tin hieu "dang xu ly" DUY NHAT nen tang cho phep. Trang thai tu tat sau ~5 giay
nen phai gui lai dinh ky.
"""

from __future__ import annotations

import asyncio
from types import TracebackType

from agent_cskh.logging_setup import get_logger
from agent_cskh.transport.zalo_client import ZaloClient

log = get_logger(__name__)

INTERVAL = 4.0


class TypingKeepAlive:
    """Dung nhu async context manager. Tu huy task khi thoat, ke ca khi co loi."""

    def __init__(self, client: ZaloClient, chat_id: str) -> None:
        self._client = client
        self._chat_id = chat_id
        self._task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> TypingKeepAlive:
        self._task = asyncio.create_task(self._loop())
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        try:
            while True:
                await self._client.send_chat_action(self._chat_id, "typing")
                await asyncio.sleep(INTERVAL)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 - khong bao gio duoc lam hong mot luot
            log.debug("typing_indicator_dung", error=str(e))
