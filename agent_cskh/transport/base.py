"""Kieu du lieu bien giua Zalo va phan con lai cua he thong.

Moi an so ve Zalo API bi nhot trong goi `transport`. Cac module khac CHI duoc
nhin thay `InboundEvent` — mot dataclass do ta dinh nghia, on dinh theo thoi gian.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

ChatType = Literal["private", "group", "unknown"]
EventKind = Literal["text", "photo", "sticker", "voice", "unsupported"]


@dataclass(frozen=True, slots=True)
class PhotoRef:
    """Anh khach gui. Zalo tra URL HTTPS truc tiep — khong co getFile."""

    url: str | None
    caption: str | None = None


@dataclass(frozen=True, slots=True)
class InboundEvent:
    """Mot su kien den, da chuan hoa.

    `event_id` lay tu `message_id` (chuoi hex). Zalo khong co `update_id` dang tin
    nen day la khoa idempotency duy nhat.
    """

    event_id: str
    event_name: str
    kind: EventKind
    chat_id: str
    chat_type: ChatType
    user_id: str
    display_name: str | None
    is_bot: bool
    text: str | None
    photo: PhotoRef | None
    voice_url: str | None
    sticker: str | None
    sent_at: datetime | None
    received_at: datetime
    # Update goc, luon giu lai. Khi Zalo doi schema, day la bang chung duy nhat.
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_private(self) -> bool:
        return self.chat_type == "private"

    @property
    def is_command(self) -> bool:
        return bool(self.text) and self.text.lstrip().startswith("/")

    @property
    def command(self) -> str | None:
        """`/baogia abc` -> `baogia`. None neu khong phai lenh."""
        if not self.is_command:
            return None
        return self.text.lstrip().split()[0][1:].split("@")[0].lower()

    @property
    def command_args(self) -> str:
        if not self.is_command:
            return ""
        parts = self.text.lstrip().split(maxsplit=1)
        return parts[1] if len(parts) > 1 else ""

    def summary(self) -> str:
        """Mot dong gon de log — khong chua noi dung day du."""
        preview = (self.text or "")[:40].replace("\n", " ")
        return (
            f"{self.kind}/{self.chat_type} chat={self.chat_id[:8]} "
            f"user={self.user_id[:8]} «{preview}»"
        )


@dataclass(slots=True)
class OutboundMessage:
    """Mot tin nhan di. `text` da duoc cat <= 2000 ky tu truoc khi den day."""

    chat_id: str
    text: str | None = None
    photo_url: str | None = None
    caption: str | None = None
    sticker: str | None = None
    reply_to_message_id: str | None = None


class Transport(ABC):
    """Nguon su kien. Polling hom nay, webhook ngay mai — phan con lai khong doi."""

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    def stream(self) -> AsyncIterator[InboundEvent]:
        """Sinh ra InboundEvent lien tuc cho den khi stop()."""
        ...
