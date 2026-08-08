"""Dieu phoi luot.

Moi chat_id co mot hang doi + worker rieng: trong cung mot cuoc tro chuyen thi
tuan tu (giu dung thu tu ngu nghia), giua cac cuoc tro chuyen thi song song.
Mot semaphore toan cuc chan bung no LLM call.

Cong viec chan (embed, doc PDF, sinh Excel) phai di qua asyncio.to_thread —
chay thang tren event loop se dong bang ca bot.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from agent_cskh.config import Settings
from agent_cskh.harness import errors
from agent_cskh.harness.loop import AgentLoop
from agent_cskh.harness.turn import TurnContext
from agent_cskh.health import Health
from agent_cskh.llm.router import ModelRouter
from agent_cskh.logging_setup import get_logger
from agent_cskh.memory import ConversationBuffer
from agent_cskh.security import MSG_HET_QUOTA, PrincipalResolver, QuotaGuard, RateLimiter
from agent_cskh.security.pham_vi import ngoai_pham_vi
from agent_cskh.skills import KhoSkill
from agent_cskh.store.repo import BoNhoRepo, ChatRepo, TuVanRepo
from agent_cskh.tools.base import ToolRegistry
from agent_cskh.transport.base import InboundEvent
from agent_cskh.transport.zalo_client import ZaloClient
from agent_cskh.wiki import WikiStore

log = get_logger(__name__)

# Hang doi moi chat. Vuot nguong nay nghia la nguoi dung spam — bo tin moi nhat.
QUEUE_MAX = 8

CommandHandler = Callable[[TurnContext], Awaitable[bool]]


class TurnDispatcher:
    def __init__(
        self,
        settings: Settings,
        *,
        client: ZaloClient,
        repo: ChatRepo,
        bo_nho: BoNhoRepo,
        tu_van: TuVanRepo,
        resolver: PrincipalResolver,
        limiter: RateLimiter,
        quota: QuotaGuard,
        buffer: ConversationBuffer,
        router: ModelRouter,
        loop: AgentLoop,
        wiki: WikiStore,
        kho_skill: KhoSkill | None = None,
        registry: ToolRegistry,
        health: Health | None = None,
        health_model: Health | None = None,
        command_handler: CommandHandler | None = None,
    ) -> None:
        self._s = settings
        self._client = client
        self._repo = repo
        self._bo_nho = bo_nho
        self._tu_van = tu_van
        self._resolver = resolver
        self._limiter = limiter
        self._quota = quota
        self._buffer = buffer
        self._router = router
        self._loop = loop
        self._wiki = wiki
        self._kho_skill = kho_skill
        self._registry = registry
        self._health = health or Health()
        self._health_model = health_model or Health(ten="Claude")
        self._commands = command_handler

        self._queues: dict[str, asyncio.Queue[InboundEvent]] = {}
        self._workers: dict[str, asyncio.Task[None]] = {}
        self._sem = asyncio.Semaphore(settings.max_concurrent_turns)
        self._running = True

    # ---------- vao ----------
    async def submit(self, event: InboundEvent) -> None:
        """Loc va dua vao hang doi. Moi buoc tu choi deu ghi log ro ly do."""
        if not self._running:
            return

        # 1. Dedup — Zalo giao at-most-once nhung ta khong tin tuyet doi.
        if await self._repo.already_processed(event.event_id):
            log.debug("bo_qua_trung_lap", message_id=event.event_id[:12])
            return
        await self._repo.mark_processed(event.event_id, event.chat_id)
        await self._quota.count_received(1)

        # 2. Quyen
        principal = await self._resolver.resolve(event)
        await self._repo.upsert_principal_seen(event.user_id, event.display_name)

        # 3. Han muc thang cua Zalo
        if not await self._quota.allows(is_internal=principal.at_least("staff")):
            if not principal.at_least("staff"):
                await self._reply_raw(event.chat_id, MSG_HET_QUOTA)
            return

        # 4. Rate limit theo nguoi
        if not await self._limiter.allow(event.user_id):
            await self._reply_raw(event.chat_id, errors.MSG_QUA_NHANH)
            return

        # 5. Dang co nguoi that tiep quan -> bot im lang tuyet doi
        state = await self._repo.get_state(event.chat_id)
        if state == "HUMAN_ACTIVE":
            session_id = await self._repo.ensure_conversation(event)
            await self._repo.save_inbound(event, session_id)
            log.info("im_lang_vi_handoff", chat_id=event.chat_id[:8])
            return

        # 6. Ghi lai roi xep hang
        session_id = await self._repo.ensure_conversation(event)
        await self._repo.save_inbound(event, session_id)

        queue = self._queues.get(event.chat_id)
        if queue is None:
            queue = asyncio.Queue(maxsize=QUEUE_MAX)
            self._queues[event.chat_id] = queue
            self._workers[event.chat_id] = asyncio.create_task(
                self._worker(event.chat_id, queue), name=f"chat-{event.chat_id[:8]}"
            )

        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            log.warning("hang_doi_day_bo_tin", chat_id=event.chat_id[:8])

    # ---------- worker mot chat ----------
    async def _worker(self, chat_id: str, queue: asyncio.Queue[InboundEvent]) -> None:
        while self._running:
            try:
                event = await queue.get()
            except asyncio.CancelledError:
                return
            try:
                async with self._sem:
                    await self._handle(event)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - worker khong duoc chet
                log.exception("worker_loi", chat_id=chat_id[:8], error=str(e))
            finally:
                queue.task_done()

    async def _handle(self, event: InboundEvent) -> None:
        principal = await self._resolver.resolve(event)
        session_id = await self._repo.ensure_conversation(event)

        # PHANH CHI PHI. Vuot tran ngay thi router ha xuong model re.
        #
        # Duong `daily_cost_exceeded -> router.choose() tra ve fast` da co san
        # tu dau, nhung KHONG AI BAT co nay len — phat hien 08/08/2026. May moc
        # day du, chi thieu nguoi keo. `DAILY_COST_LIMIT_USD` trong config vi
        # the la mot con so trang tri.
        #
        # Ha xuong model re chu khong tu choi phuc vu: khach van duoc tra loi,
        # chi la kem sac hon. Im lang la lua chon te nhat trong moi lua chon.
        try:
            hom_nay = await self._repo.chi_phi_hom_nay()
        except Exception as e:  # noqa: BLE001 - khong duoc lam hong luot
            log.warning("khong_doc_duoc_chi_phi", error=str(e))
            hom_nay = 0.0
        vuot_tran = hom_nay >= self._s.daily_cost_limit_usd
        if vuot_tran:
            log.warning(
                "vuot_tran_chi_phi_ngay",
                da_tieu=round(hom_nay, 2),
                tran=self._s.daily_cost_limit_usd,
            )

        ctx = TurnContext(
            settings=self._s,
            event=event,
            principal=principal,
            session_id=session_id,
            client=self._client,
            repo=self._repo,
            bo_nho=self._bo_nho,
            tu_van=self._tu_van,
            buffer=self._buffer,
            router=self._router,
            quota=self._quota,
            wiki=self._wiki,
            kho_skill=self._kho_skill,
            registry=self._registry,
            health=self._health,
            health_model=self._health_model,
            resolver=self._resolver,
            daily_cost_exceeded=vuot_tran,
        )

        # Lenh /... xu ly trong code, khong ton token LLM.
        if self._commands is not None and event.is_command:
            handled = await self._commands(ctx)
            if handled:
                return

        # LOP 2 siet pham vi: chan TRUOC khi goi LLM, tiet kiem ca quota Zalo lan
        # tien token. Chi bat nhung nhom khong bao gio duoc tra loi bat ke kho
        # tri thuc co gi — con "kho tra loi" thi de lop 1 trong reply() lo.
        # Nhan vien khong bi chan: ho co the hoi bat ky dieu gi de kiem tra bot.
        if not principal.at_least("staff"):
            nhom = ngoai_pham_vi(event.text)
            if nhom is not None:
                log.info("chan_ngoai_pham_vi", nhom=nhom.ten, chat_id=event.chat_id[:8])
                await ctx.reply(nhom.tra_loi)
                return

        await self._loop.run_turn(ctx)

    # ---------- tien ich ----------
    async def _reply_raw(self, chat_id: str, text: str) -> None:
        try:
            # Khong dem quota o day — ZaloClient.send_message da dem roi.
            await self._client.send_message(chat_id, text)
        except Exception as e:  # noqa: BLE001
            log.warning("khong_gui_duoc", chat_id=chat_id[:8], error=str(e))

    async def drain(self, grace: float = 20.0) -> None:
        """Cho cac luot dang chay xong roi dung han."""
        self._running = False
        pending = [q.join() for q in self._queues.values()]
        if pending:
            try:
                async with asyncio.timeout(grace):
                    await asyncio.gather(*pending)
            except TimeoutError:
                log.warning("con_luot_chua_xong_khi_dung")
        for task in self._workers.values():
            task.cancel()
        self._workers.clear()
        self._queues.clear()
