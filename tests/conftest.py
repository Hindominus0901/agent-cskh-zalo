"""Ha tang chung cho test: he thong day du voi CSDL tam va cac thanh phan gia.

Dung ZaloClient gia va model gia, nen chay duoc ma khong can token hay API key.

Nguyen tac: lop gia phai giong that o dung nhung co che co the gay loi. Ngay
07/08/2026 FakeZaloClient thieu callback `on_sent` nen bo test khong bao gio
thay quota bi dem gap doi — lop gia bo mat co che gay loi thi no dang giau loi
chu khong phai dang kiem tra.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from agent_cskh.commands import handle as handle_command
from agent_cskh.config import Settings
from agent_cskh.harness.dispatcher import TurnDispatcher
from agent_cskh.harness.loop import AgentLoop
from agent_cskh.health import Health
from agent_cskh.llm.base import LLMResponse, Msg, ToolCall, ToolSpec
from agent_cskh.memory import ConversationBuffer
from agent_cskh.security import PrincipalResolver, QuotaGuard, RateLimiter
from agent_cskh.store import Database
from agent_cskh.store.repo import BoNhoRepo, ChatRepo, TuVanRepo
from agent_cskh.tools import default_registry
from agent_cskh.transport.base import InboundEvent, PhotoRef
from agent_cskh.wiki import WikiStore

# ---------------------------------------------------------------- gia lap


class FakeZaloClient:
    """Ghi lai moi tin da 'gui' thay vi goi mang.

    PHAI goi `on_sent` giong ZaloClient that. Truoc 07/08/2026 lop gia nay khong
    co callback do, nen bo test khong bao gio thay quota bi dem gap doi: test
    thay `used == 2` va xanh, trong khi may that la 3. Lop gia bo mat dung cai
    co che gay loi thi no dang giau loi chu khong phai dang kiem tra.
    """

    def __init__(self, on_sent: Any = None) -> None:
        self.sent: list[tuple[str, str]] = []
        self.actions: list[str] = []
        self._on_sent = on_sent

    async def send_message(self, chat_id: str, text: str, **_kw: Any) -> list[str]:
        self.sent.append((chat_id, text))
        if self._on_sent:
            await self._on_sent(1)
        return [f"mid{len(self.sent)}"]

    async def send_chat_action(self, chat_id: str, action: str = "typing") -> None:
        self.actions.append(action)

    @property
    def texts(self) -> list[str]:
        return [t for _, t in self.sent]


class FakeProvider:
    """Model gia. `script` cho phep kich ban nhieu luot de thu vong lap tool."""

    name = "fake"
    model = "fake-1"

    def __init__(self, reply: str = "Dạ em nghe ạ.") -> None:
        self.reply = reply
        self.script: list[list[ToolCall]] = []
        self.calls: list[list[Msg]] = []
        self.systems: list[str] = []
        self.systems_theo_nguoi: list[str] = []
        self.tools_seen: list[list[str]] = []

    async def complete(
        self,
        messages: list[Msg],
        *,
        system: str,
        system_theo_nguoi: str = "",
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 2048,
        timeout: float = 90.0,
    ) -> LLMResponse:
        self.calls.append(messages)
        self.systems.append(system)
        self.systems_theo_nguoi.append(system_theo_nguoi)
        self.tools_seen.append([t.name for t in (tools or [])])

        tool_calls = self.script.pop(0) if self.script else []
        return LLMResponse(
            text="" if tool_calls else self.reply,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
            provider=self.name,
            model=self.model,
            input_tokens=10,
            output_tokens=5,
        )


class FakeRouter:
    def __init__(self, provider: FakeProvider) -> None:
        self._p = provider

    @property
    def fast(self) -> FakeProvider:
        return self._p

    @property
    def deep(self) -> FakeProvider:
        return self._p

    def choose(self, _ctx: Any) -> FakeProvider:
        return self._p

    def escalate(self, _ctx: Any) -> FakeProvider:
        return self._p


def make_event(
    text: str | None = "chào em",
    *,
    message_id: str = "m1",
    chat_id: str = "c1",
    user_id: str = "u1",
    chat_type: str = "private",
    kind: str = "text",
    photo_url: str | None = None,
) -> InboundEvent:
    return InboundEvent(
        event_id=message_id,
        event_name="message.text.received",
        kind=kind,  # type: ignore[arg-type]
        chat_id=chat_id,
        chat_type=chat_type,  # type: ignore[arg-type]
        user_id=user_id,
        display_name="Minh",
        is_bot=False,
        text=text,
        photo=PhotoRef(url=photo_url) if photo_url else None,
        voice_url=None,
        sticker=None,
        sent_at=datetime.now(tz=UTC),
        received_at=datetime.now(tz=UTC),
        raw={},
    )


# ---------------------------------------------------------------- fixture


@pytest.fixture
async def rig(tmp_path, monkeypatch):
    """Dung mot he thong day du voi CSDL tam va cac thanh phan gia."""
    monkeypatch.setattr(
        Settings, "db_path", property(lambda _self: tmp_path / "test.db"), raising=False
    )
    # Kho tri thuc PHAI la thu muc tam. Ngay 08/08/2026 test cua lenh /themtrang
    # da ghi 8 file rac thang vao knowledge/ that — bot san xuat doc duoc chung.
    # Test khong bao gio duoc cham vao du lieu that.
    kho = tmp_path / "knowledge"
    for muc in ("public", "hocvien", "internal"):
        (kho / "wiki" / muc).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Settings, "knowledge_dir", property(lambda _self: kho), raising=False)
    # ALERT_CHAT_ID tro toi mot chu bot that: notify_staff() va _bao_chu() deu
    # kiem nguoi nhan qua la_kenh_noi_bo(), nen kenh canh bao phai hop le thi
    # test moi phan anh dung mot bot da cau hinh xong.
    settings = Settings(
        _env_file=None,
        owner_user_ids=["admin"],
        alert_chat_id="admin",
        rate_limit_per_min=5,
        zalo_monthly_quota=100,
    )

    db = Database(settings)
    await db.connect()

    repo = ChatRepo(db)
    bo_nho = BoNhoRepo(db)
    tu_van = TuVanRepo(db)
    quota = QuotaGuard(settings, db)
    # Noi giong app.py: ZaloClient la cho dem quota DUY NHAT.
    client = FakeZaloClient(on_sent=quota.count_sent)
    provider = FakeProvider()

    wiki = WikiStore(settings)
    wiki.reload()
    health_model = Health(ten="Claude")

    dispatcher = TurnDispatcher(
        settings,
        client=client,  # type: ignore[arg-type]
        repo=repo,
        bo_nho=bo_nho,
        tu_van=tu_van,
        resolver=PrincipalResolver(settings, db),
        limiter=RateLimiter(settings, db),
        quota=quota,
        buffer=ConversationBuffer(repo),
        router=FakeRouter(provider),  # type: ignore[arg-type]
        loop=AgentLoop(),
        wiki=wiki,
        registry=default_registry(),
        health=Health(ten="Zalo"),
        health_model=health_model,
        command_handler=handle_command,
    )

    yield {
        "settings": settings,
        "db": db,
        "repo": repo,
        "bo_nho": bo_nho,
        "tu_van": tu_van,
        "client": client,
        "provider": provider,
        "quota": quota,
        "dispatcher": dispatcher,
        "health_model": health_model,
    }

    await dispatcher.drain(grace=2.0)
    await db.close()


async def run_one(rig: dict, event: InboundEvent) -> None:
    """Nap su kien roi cho hang doi xu ly xong."""
    await rig["dispatcher"].submit(event)
    for q in rig["dispatcher"]._queues.values():  # noqa: SLF001
        await q.join()
