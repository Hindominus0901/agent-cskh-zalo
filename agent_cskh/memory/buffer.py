"""Tang 1 — buffer hoi thoai ngan han.

Doc N tin gan nhat tu SQLite va dung thanh danh sach Msg cho LLM.
Gop cac tin lien tiep cung vai tro: Claude cho phep, nhung gop lai giup
prompt gon va on dinh hon giua cac luot (tot cho prompt cache).
"""

from __future__ import annotations

from agent_cskh.llm.base import Msg
from agent_cskh.store.repo import ChatRepo, StoredMessage
from agent_cskh.transport.base import InboundEvent

DEFAULT_WINDOW = 12


def _describe(m: StoredMessage) -> str | None:
    if m.text:
        return m.text
    if m.kind == "photo":
        return "[nguoi dung gui mot tam anh]"
    if m.kind == "sticker":
        return "[nguoi dung gui sticker]"
    if m.kind == "voice":
        return "[nguoi dung gui tin thoai]"
    return None


def to_messages(history: list[StoredMessage]) -> list[Msg]:
    out: list[Msg] = []
    for m in history:
        text = _describe(m)
        if not text:
            continue
        role = "user" if m.direction == "in" else "assistant"
        if out and out[-1].role == role and out[-1].text:
            out[-1].text = f"{out[-1].text}\n{text}"
        else:
            out.append(Msg(role=role, text=text))  # type: ignore[arg-type]
    return out


class ConversationBuffer:
    def __init__(self, repo: ChatRepo, *, window: int = DEFAULT_WINDOW) -> None:
        self._repo = repo
        self._window = window

    async def build(self, event: InboundEvent) -> list[Msg]:
        """Lich su + luot hien tai. Luot hien tai LUON o cuoi va luon la 'user'."""
        # +1 vi tin vua den da duoc ghi vao CSDL truoc khi goi ham nay.
        history = await self._repo.recent(event.chat_id, limit=self._window + 1)

        # Bo tin cuoi neu no chinh la su kien dang xu ly — ta tu dung lai ben duoi
        # de dinh kem anh dung cach.
        if history and history[-1].direction == "in":
            history = history[:-1]

        messages = to_messages(history)

        current = Msg(role="user", text=event.text or None)
        if event.photo and event.photo.url:
            current.image_urls = [event.photo.url]
            if not current.text:
                current.text = "Khach gui anh nay, xem giup em."
        if not current.text and not current.image_urls:
            current.text = (
                _describe(StoredMessage(direction="in", kind=event.kind, text=None, created_at=""))
                or "[tin nhan khong doc duoc noi dung]"
            )

        # API yeu cau luot dau tien phai la 'user'.
        while messages and messages[0].role != "user":
            messages.pop(0)

        messages.append(current)
        return messages
