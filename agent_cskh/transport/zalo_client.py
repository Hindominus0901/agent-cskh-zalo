"""Client HTTP thuan cho Zalo Bot API.

Vi sao khong dung SDK `python-zalo-bot` o duong chay chinh (da kiem tra source 0.1.9):
  - `Message.de_json` chi doc `photo_url`, BO QUA `photo`, `caption`, `voice_url`
  - `Update` khong co `update_id` -> tham so `offset` cua chinh SDK vo dung
  - `send_message` khong ho tro `parse_mode` / `text_styles`
SDK van nam trong dependencies de doi chieu, nhung moi loi goi that di qua day.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from agent_cskh.config import Settings
from agent_cskh.logging_setup import get_logger
from agent_cskh.transport.base import OutboundMessage

log = get_logger(__name__)

# Gioi han cung cua sendMessage.
MAX_TEXT = 2000
# Ma loi Zalo (docs/error-code): 400 sai path · 401 token hong · 403 loi server
# · 404 khong thay · 408 timeout · 429 vuot quota.
RETRYABLE_CODES = {403, 408, 429, 500, 502, 503, 504}


class ZaloAPIError(RuntimeError):
    def __init__(self, method: str, code: int | None, description: str) -> None:
        super().__init__(f"{method} that bai (error_code={code}): {description}")
        self.method = method
        self.code = code
        self.description = description

    @property
    def retryable(self) -> bool:
        return self.code in RETRYABLE_CODES

    @property
    def is_quota(self) -> bool:
        return self.code == 429


class _Retryable(ZaloAPIError):
    """Phan lop chi de tenacity phan biet — khong dung truc tiep."""


def split_text(text: str, limit: int = MAX_TEXT) -> list[str]:
    """Cat tin qua dai thanh nhieu phan, uu tien ranh gioi doan roi den cau.

    Zalo khong co editMessageText nen khong the noi dan — phai cat truoc khi gui.
    """
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    remaining = text
    while len(remaining) > limit:
        window = remaining[:limit]
        cut = max(window.rfind("\n\n"), window.rfind("\n"))
        if cut < limit // 2:
            cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
            cut = cut + 1 if cut > limit // 2 else -1
        if cut < 0:
            cut = window.rfind(" ")
        if cut < limit // 2:
            cut = limit
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return [p for p in parts if p]


class ZaloClient:
    """Bao API Zalo: retry, dem quota, che token trong log."""

    def __init__(
        self,
        settings: Settings,
        *,
        on_sent: Callable[[int], Awaitable[None]] | None = None,
        on_received: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        self._s = settings
        self._client: httpx.AsyncClient | None = None
        self._on_sent = on_sent
        self._on_received = on_received

    async def __aenter__(self) -> ZaloClient:
        await self.open()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def open(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, read=90.0),
                limits=httpx.Limits(max_connections=20),
            )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def http(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("ZaloClient chua open()")
        return self._client

    # ---------- loi goi co ban ----------
    @retry(
        retry=retry_if_exception_type((_Retryable, httpx.TransportError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=1, max=30),
        reraise=True,
    )
    async def _call(
        self,
        method: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        quiet_codes: frozenset[int] = frozenset(),
    ) -> Any:
        url = self._s.api_url(method)
        try:
            resp = await self.http.post(url, json=payload or {}, timeout=timeout)
        except httpx.TransportError as e:
            log.warning("zalo_loi_mang", method=method, error=str(e))
            raise

        try:
            body = resp.json()
        except ValueError:
            raise ZaloAPIError(method, resp.status_code, resp.text[:200]) from None

        if body.get("ok"):
            return body.get("result")

        code = body.get("error_code") or resp.status_code
        desc = str(body.get("description") or "")
        err = ZaloAPIError(method, code, desc)
        if err.retryable:
            log.warning("zalo_loi_tam_thoi", method=method, code=code, description=desc)
            raise _Retryable(method, code, desc)
        if code in quiet_codes:
            log.debug("zalo_loi_du_kien", method=method, code=code, description=desc)
        else:
            log.error("zalo_loi", method=method, code=code, description=desc)
        raise err

    # ---------- doc ----------
    async def get_me(self) -> dict[str, Any]:
        return await self._call("getMe")

    # `timeout` la tham so GIAO THUC gui len Zalo (do dai long-poll), khong phai
    # timeout huy tac vu phia client -> asyncio.timeout khong thay the duoc.
    async def get_updates(self, timeout: int = 30) -> dict[str, Any] | None:
        """Long-poll. Tra ve body THO (con nguyen lop `result`) de normalize() tu boc.

        Ba gia tri tra ve, phan biet ky vi nhip tim dua vao day:
          dict co du lieu -> co tin nhan
          dict rong {}     -> khong co tin (408 het gio cho, hoac body rong). BINH THUONG.
          None             -> that su loi (5xx, body khong phai JSON, loi mang)

        Luu y: Zalo KHONG ho tro `offset`/`limit` — chi co `timeout`. Giao hang la
        at-most-once; tin gui khi bot offline coi nhu mat.
        """
        url = self._s.api_url("getUpdates")
        try:
            resp = await self.http.post(url, json={"timeout": str(timeout)}, timeout=timeout + 20)
        except httpx.TransportError as e:
            log.warning("polling_loi_mang", error=str(e))
            return None
        try:
            body = resp.json()
        except ValueError:
            log.warning("polling_body_khong_phai_json", status=resp.status_code)
            return None
        if not body.get("ok"):
            code = body.get("error_code") or resp.status_code
            if code == 408:
                # 408 la cach Zalo bao "het gio cho, khong co tin nao" — trang thai
                # BINH THUONG khi khong ai nhan, lap lai moi ~30 giay. Tra ve rong
                # chu khong phai None, neu khong nhip tim se coi day la mat ket noi
                # va bao dong gia sau moi 10 phut yen ang.
                log.debug("polling_het_gio_cho", timeout=timeout)
                return {}
            log.warning("polling_that_bai", code=code, description=body.get("description"))
            if code == 429:
                raise ZaloAPIError("getUpdates", 429, str(body.get("description") or ""))
            return None
        if body.get("result") and self._on_received:
            await self._on_received(1)
        return body

    async def get_webhook_info(self) -> dict[str, Any]:
        return await self._call("getWebhookInfo")

    # ---------- ghi ----------
    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        parse_mode: str | None = None,
        reply_to_message_id: str | None = None,
    ) -> list[str]:
        """Gui text, tu cat neu > 2000 ky tu. Tra ve danh sach message_id da gui."""
        ids: list[str] = []
        for part in split_text(text, self._s.max_reply_chars):
            payload: dict[str, Any] = {"chat_id": chat_id, "text": part}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            if reply_to_message_id and not ids:
                payload["reply_to_message_id"] = reply_to_message_id
            result = await self._call("sendMessage", payload)
            if self._on_sent:
                await self._on_sent(1)
            if isinstance(result, dict) and result.get("message_id"):
                ids.append(str(result["message_id"]))
        return ids

    async def send_photo(self, chat_id: str, photo_url: str, caption: str = "") -> str | None:
        """sendPhoto chi nhan URL — Zalo khong ho tro upload multipart."""
        result = await self._call(
            "sendPhoto",
            {"chat_id": chat_id, "photo": photo_url, "caption": caption[:MAX_TEXT]},
        )
        if self._on_sent:
            await self._on_sent(1)
        return str(result.get("message_id")) if isinstance(result, dict) else None

    async def send_sticker(self, chat_id: str, sticker: str) -> None:
        await self._call("sendSticker", {"chat_id": chat_id, "sticker": sticker})
        if self._on_sent:
            await self._on_sent(1)

    async def send_chat_action(self, chat_id: str, action: str = "typing") -> None:
        """Tin hieu 'dang xu ly' duy nhat ma Zalo cho phep.

        Thuan tuy trang tri: hong thi lo mat hieu ung "dang nhap...", khong anh
        huong gi den cau tra loi. Khong bao gio ghi o muc ERROR.
        """
        try:
            await self._call(
                "sendChatAction",
                {"chat_id": chat_id, "action": action},
                quiet_codes=frozenset({400, 404, 410}),
            )
        except (ZaloAPIError, httpx.HTTPError) as e:
            log.debug("chat_action_that_bai", error=str(e))

    async def send(self, msg: OutboundMessage) -> None:
        if msg.text:
            await self.send_message(
                msg.chat_id, msg.text, reply_to_message_id=msg.reply_to_message_id
            )
        if msg.photo_url:
            await self.send_photo(msg.chat_id, msg.photo_url, msg.caption or "")
        if msg.sticker:
            await self.send_sticker(msg.chat_id, msg.sticker)

    # ---------- webhook ----------
    async def set_webhook(self, url: str, secret_token: str) -> Any:
        return await self._call("setWebhook", {"url": url, "secret_token": secret_token})

    async def delete_webhook(self) -> Any:
        """Phai goi truoc khi polling — getUpdates va webhook loai tru nhau.

        Zalo tra 400 khi chua tung dat webhook. Do la trang thai binh thuong,
        khong phai loi — dung lam ban log luc khoi dong.
        """
        return await self._call("deleteWebhook", quiet_codes=frozenset({400}))
