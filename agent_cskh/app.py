"""Noi day toan bo he thong va chay.

Vong doi: mo CSDL -> mo HTTP client -> kiem tra token -> chon transport ->
nhan su kien -> dieu phoi. Ctrl+C thi cho cac luot dang chay xong roi dung.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal

from agent_cskh.commands import handle as handle_command
from agent_cskh.config import Settings
from agent_cskh.harness.dispatcher import TurnDispatcher, VongMotLuot
from agent_cskh.harness.loop import AgentLoop
from agent_cskh.health import Health
from agent_cskh.llm.router import ModelRouter
from agent_cskh.logging_setup import get_logger
from agent_cskh.memory import ConversationBuffer
from agent_cskh.scheduler import Scheduler
from agent_cskh.security import PrincipalResolver, QuotaGuard, RateLimiter
from agent_cskh.skills import KhoSkill
from agent_cskh.store import Database
from agent_cskh.store.repo import BoNhoRepo, ChatRepo, TuVanRepo
from agent_cskh.tools import default_registry
from agent_cskh.tra_cuu.chay import VongTraCuu
from agent_cskh.transport import PollingTransport, WebhookTransport, ZaloClient
from agent_cskh.transport.base import Transport
from agent_cskh.wiki import WikiStore

log = get_logger(__name__)


def chon_bo_nao(settings: Settings, wiki: WikiStore) -> VongMotLuot:
    """Chon bo nao theo `CHE_DO`. DAY LA CHO DUY NHAT `che_do` doi hanh vi bot.

    Tach thanh ham rieng de test duoc — day la dong quan trong nhat cua ca file,
    va truoc 11/08/2026 no KHONG TON TAI.

    Luc do `che_do` chi duoc doc o `config.py` va `cli.py`; duong chay Zalo luon
    dung `AgentLoop`. Hoc vien de `CHE_DO=tra_cuu` roi chay bot -> bot van goi
    Claude, va `config.problems()` khong bao gi vi no chi kiem API key khi
    `che_do == "ai"`. Ca loi hua "ban 0 dong chay tren Zalo" la khong dung.

    Hai lop deu co `run_turn(ctx)` nen dispatcher khong can biet minh chay cai nao.
    """
    if settings.che_do == "tra_cuu":
        return VongTraCuu(wiki)
    return AgentLoop()


class Application:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._db = Database(settings)
        self._stop = asyncio.Event()
        self._health = Health(ten="Zalo")
        self._health_model = Health(ten="Claude")

    async def run(self) -> int:
        self._s.ensure_dirs()
        await self._db.connect()

        repo = ChatRepo(self._db)
        bo_nho = BoNhoRepo(self._db)
        tu_van = TuVanRepo(self._db)
        quota = QuotaGuard(self._s, self._db)

        wiki = WikiStore(self._s)
        wiki.reload()
        kho_skill = KhoSkill(self._s)
        kho_skill.nap()
        registry = default_registry()

        vong = chon_bo_nao(self._s, wiki)
        log.info("che_do_dang_chay", che_do=self._s.che_do, bo_nao=type(vong).__name__)
        print(
            f"Chế độ: {self._s.che_do}"
            + ("  (0 đồng, không gọi API)" if self._s.che_do == "tra_cuu" else "")
        )

        async with ZaloClient(self._s, on_sent=quota.count_sent, on_received=None) as client:
            me = await self._verify_token(client)
            if me is None:
                return 1

            resolver = PrincipalResolver(self._s, self._db)
            await self._kiem_tra_kenh_canh_bao(resolver)

            dispatcher = TurnDispatcher(
                self._s,
                client=client,
                repo=repo,
                bo_nho=bo_nho,
                tu_van=tu_van,
                resolver=resolver,
                limiter=RateLimiter(self._s, self._db),
                quota=quota,
                buffer=ConversationBuffer(repo),
                router=ModelRouter(self._s),
                loop=vong,
                wiki=wiki,
                kho_skill=kho_skill,
                registry=registry,
                health=self._health,
                health_model=self._health_model,
                command_handler=handle_command,
            )

            transport = self._build_transport(client)
            scheduler = Scheduler(
                self._s,
                client=client,
                repo=repo,
                quota=quota,
                health=self._health,
                health_model=self._health_model,
                resolver=resolver,
                tu_van=tu_van,
                db=self._db,
            )
            scheduler.start()
            self._install_signals()

            # Don ban ghi dedup cu — chay mot lan luc khoi dong la du.
            removed = await repo.prune_processed()
            if removed:
                log.info("don_dedup_cu", rows=removed)

            await transport.start()
            consumer = asyncio.create_task(self._consume(transport, dispatcher))

            await self._stop.wait()
            log.info("dang_dung...")

            scheduler.shutdown()
            await transport.stop()
            consumer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await consumer
            await dispatcher.drain()

        await self._db.close()
        log.info("da_dung")
        return 0

    # ---------- ben trong ----------
    async def _verify_token(self, client: ZaloClient) -> dict | None:
        try:
            me = await client.get_me()
        except Exception as e:  # noqa: BLE001
            log.error("token_khong_dung_hoac_khong_goi_duoc_api", error=self._s.redact(str(e)))
            print("Khong xac thuc duoc voi Zalo. Kiem tra ZALO_BOT_TOKEN trong .env.")
            return None

        log.info(
            "bot_san_sang",
            account_name=me.get("account_name"),
            can_join_groups=me.get("can_join_groups"),
        )
        print(f"Bot: {me.get('account_name')} (id={me.get('id')})")
        if me.get("can_join_groups") is False:
            print("Luu y: can_join_groups=False — bot chua vao nhom duoc.")
        return me

    async def _kiem_tra_kenh_canh_bao(self, resolver: PrincipalResolver) -> None:
        """Xac minh ALERT_CHAT_ID luc khoi dong, khong doi den luc co su co.

        Canh bao va nhac handoff mang noi dung noi bo — ke ca tom tat khach hoi
        gi. Neu chat_id nay tro nham vao mot khach hang, ta se lo du lieu cua
        khach khac cho ho. Phat hien luc khoi dong thi con sua duoc trong yen
        binh; phat hien luc su co thi da gui mat roi.
        """
        target = self._s.alert_chat_id.strip()
        if not target:
            log.warning(
                "chua_dat_alert_chat_id",
                hau_qua="Se khong ai nhan duoc canh bao khi bot hong",
                cach_sua="Nhan 'id cua toi' cho bot roi dien chat_id vao ALERT_CHAT_ID",
            )
            print("Luu y: chua dat ALERT_CHAT_ID — bot hong se khong bao cho ai.")
            return

        if await resolver.la_kenh_noi_bo(target):
            log.info("kenh_canh_bao_hop_le", chat_id=target[:8])
            return

        log.error("alert_chat_id_khong_phai_noi_bo", chat_id=target[:8])
        print(
            "CANH BAO: ALERT_CHAT_ID khong thuoc chu bot hay nhom noi bo nao.\n"
            "  Bot se KHONG gui canh bao di, de tranh lo noi dung noi bo cho nguoi ngoai.\n"
            "  Sua: nhan 'id cua toi' cho bot de lay chat_id dung."
        )

    def _build_transport(self, client: ZaloClient) -> Transport:
        if self._s.transport == "webhook":
            return WebhookTransport(self._s, client)
        # Health duoc truyen vao de scheduler biet khi nao Zalo im lang.
        # Luu y van hanh: ngay 05/08/2026 getUpdates cua Zalo chet ~2 tieng (504/502
        # tren moi bot) roi tu hoi phuc. Polling khong can ten mien nen tien cho may
        # local; webhook on dinh hon cho chay that. Xem docs/04-van-hanh.md.
        return PollingTransport(self._s, client, self._health)

    async def _consume(self, transport: Transport, dispatcher: TurnDispatcher) -> None:
        try:
            async for event in transport.stream():
                await dispatcher.submit(event)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            log.exception("vong_nhan_su_kien_chet", error=str(e))
            self._stop.set()

    def _install_signals(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._stop.set)
            except NotImplementedError:
                # Windows khong ho tro add_signal_handler cho SIGTERM.
                signal.signal(sig, lambda *_: self._stop.set())
