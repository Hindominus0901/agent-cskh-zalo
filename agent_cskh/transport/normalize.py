"""Update JSON tho -> InboundEvent. DIEM SUA DUY NHAT khi Zalo doi schema.

Nguyen tac fail-soft: khong bao gio nem exception. Khoa la se log WARNING kem
nguyen van JSON va van tra ve mot InboundEvent dung duoc. Bot khong duoc chet
vi mot tin nhan la.

Su that da kiem chung (05/08/2026):
  - Payload boc trong `result`: {"ok":true,"result":{"message":{...},"event_name":"..."}}
  - `chat.chat_type` (KHONG phai `chat.type`), gia tri "PRIVATE" / "GROUP"
  - `date` tinh bang MILI giay
  - `message_id` la chuoi HEX, khong phai so
  - KHONG co `update_id` dang tin -> idempotency dua vao `message_id`
  - Anh: docs ghi `photo`, SDK TS doc `photo_url` -> chap nhan CA HAI
  - Khong co truong `document`/`file` — file roi vao message.unsupported.received
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agent_cskh.logging_setup import get_logger
from agent_cskh.transport.base import ChatType, EventKind, InboundEvent, PhotoRef

log = get_logger(__name__)

# Khoa da biet. Bat cu khoa nao ngoai danh sach nay se duoc log de ta phat hien
# Zalo them truong moi.
_KNOWN_MESSAGE_KEYS = {
    "message_id",
    "date",
    "chat",
    "from",
    "text",
    "message_type",
    "photo",
    "photo_url",
    "caption",
    "sticker",
    "url",
    "voice_url",
}

_CHAT_TYPE_MAP: dict[str, ChatType] = {
    "PRIVATE": "private",
    "GROUP": "group",
}


def _chat_type(raw: str | None) -> ChatType:
    if not raw:
        return "unknown"
    return _CHAT_TYPE_MAP.get(str(raw).upper(), "unknown")


def _parse_date(value: Any) -> datetime | None:
    """Zalo gui mili giay. Chap nhan ca giay phong khi ho doi."""
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    if ts <= 0:
        return None
    # Sau nam 2001 tinh bang giay = 1e9; nguong 1e11 tach giay khoi mili giay.
    if ts > 1e11:
        ts /= 1000.0
    try:
        return datetime.fromtimestamp(ts, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _classify(msg: dict[str, Any], event_name: str) -> EventKind:
    """Uu tien event_name; neu thieu thi suy tu truong co mat."""
    name = (event_name or "").lower()
    for token, kind in (
        ("image", "photo"),
        ("photo", "photo"),
        ("sticker", "sticker"),
        ("voice", "voice"),
        ("text", "text"),
    ):
        if token in name:
            return kind  # type: ignore[return-value]
    if msg.get("photo") or msg.get("photo_url"):
        return "photo"
    if msg.get("sticker"):
        return "sticker"
    if msg.get("voice_url"):
        return "voice"
    if msg.get("text"):
        return "text"
    return "unsupported"


def unwrap(body: dict[str, Any]) -> dict[str, Any] | None:
    """Boc lop `result` neu co. Webhook va getUpdates dung chung hinh dang ben trong."""
    if not isinstance(body, dict):
        return None
    if "result" in body and isinstance(body["result"], dict):
        return body["result"]
    # Webhook co the POST thang phan trong.
    if "message" in body or "event_name" in body:
        return body
    return None


def normalize(body: dict[str, Any]) -> InboundEvent | None:
    """Tra ve InboundEvent, hoac None neu payload rong (long-poll het gio)."""
    now = datetime.now(tz=UTC)

    result = unwrap(body)
    if not result:
        return None

    msg = result.get("message")
    if not isinstance(msg, dict) or not msg:
        # Long-poll het gio tra ve {"ok":true} rong — binh thuong, khong canh bao.
        if body.get("ok") and not result:
            return None
        log.warning("update_khong_co_message", raw=body)
        return None

    event_name = str(result.get("event_name") or "")

    # Canh bao khi Zalo them truong moi — de ta biet ma cap nhat file nay.
    unknown = set(msg) - _KNOWN_MESSAGE_KEYS
    if unknown:
        log.warning("truong_la_trong_message", fields=sorted(unknown), raw=msg)

    chat = msg.get("chat") if isinstance(msg.get("chat"), dict) else {}
    sender = msg.get("from") if isinstance(msg.get("from"), dict) else {}

    chat_id = str(chat.get("id") or "")
    user_id = str(sender.get("id") or "") or chat_id

    message_id = str(msg.get("message_id") or "")
    if not message_id:
        # Khong co khoa idempotency -> tu dung mot khoa tong hop de van xu ly duoc,
        # nhung ghi canh bao vi de trung lap.
        message_id = f"noid:{chat_id}:{msg.get('date')}"
        log.warning("thieu_message_id", raw=msg)

    if not chat_id:
        log.warning("thieu_chat_id_khong_the_tra_loi", raw=msg)
        return None

    kind = _classify(msg, event_name)

    photo_url = msg.get("photo") or msg.get("photo_url")
    photo = PhotoRef(url=str(photo_url), caption=msg.get("caption")) if photo_url else None

    return InboundEvent(
        event_id=message_id,
        event_name=event_name,
        kind=kind,
        chat_id=chat_id,
        chat_type=_chat_type(chat.get("chat_type") or chat.get("type")),
        user_id=user_id,
        display_name=sender.get("display_name"),
        is_bot=bool(sender.get("is_bot", False)),
        text=msg.get("text") or msg.get("caption"),
        photo=photo,
        voice_url=msg.get("voice_url"),
        sticker=msg.get("sticker"),
        sent_at=_parse_date(msg.get("date")),
        received_at=now,
        raw=body,
    )
