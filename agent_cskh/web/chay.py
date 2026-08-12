"""Chay bot o kenh web (widget tren website).

Dung y het cac manh ghep cua duong Zalo — cung kho tri thuc, cung ky nang, cung
ba lop guard — chi thay HAI thu:

    ZaloClient  ->  KhachWeb   (cau tra loi ve trinh duyet, khong ve Zalo)
    QuotaGuard  ->  QuotaWeb   (han muc Zalo khong ap dung cho web)

Khong co scheduler: cac job dinh ky (bao cao 20h, canh han muc, nhac handoff)
deu NHAN TIN CHU DONG qua Zalo. Kenh web khong nhan tin chu dong duoc — khach
dong tab la het. Chay bot Zalo song song neu ban muon co bao cao.
"""

from __future__ import annotations

import uvicorn

from agent_cskh.commands import handle as handle_command
from agent_cskh.config import Settings
from agent_cskh.harness.dispatcher import TurnDispatcher
from agent_cskh.llm.router import ModelRouter
from agent_cskh.logging_setup import get_logger
from agent_cskh.memory import ConversationBuffer
from agent_cskh.security import PrincipalResolver, RateLimiter
from agent_cskh.skills import KhoSkill
from agent_cskh.store import Database
from agent_cskh.store.repo import BoNhoRepo, ChatRepo, TuVanRepo
from agent_cskh.tools import default_registry
from agent_cskh.wiki import WikiStore

log = get_logger(__name__)


class QuotaWeb:
    """Han muc Zalo khong lien quan gi den web.

    Duck-type `QuotaGuard` de dispatcher khong phai biet minh dang o kenh nao.
    Luon cho qua — tran cua kenh web la `web.chan.TranNgay`, kiem o tang HTTP
    truoc khi su kien vao toi day.
    """

    async def count_received(self, n: int = 1) -> None:
        return None

    async def count_sent(self, n: int = 1) -> None:
        return None

    async def allows(self, *, is_internal: bool) -> bool:
        return True


async def chay_web(settings: Settings) -> int:
    from agent_cskh.app import chon_bo_nao
    from agent_cskh.web.khach import KhachWeb
    from agent_cskh.web.server import tao_app

    settings.ensure_dirs()
    db = Database(settings)
    await db.connect()

    try:
        wiki = WikiStore(settings)
        wiki.reload()
        kho_skill = KhoSkill(settings)
        kho_skill.nap()

        repo = ChatRepo(db)

        # Duong bao cho chu shop. Kenh web KHONG tu bao duoc cho ai — no chi
        # song trong mot tab dang mo. Nen khi khach web can nguoi that, canh bao
        # phai di qua Zalo.
        #
        # Khong co token thi van chay, chi la chu shop phai tu vao xem. Bat buoc
        # co Zalo moi chay duoc web la mot rang buoc vo co.
        zalo = None
        if settings.token:
            from agent_cskh.transport import ZaloClient

            zalo = ZaloClient(settings)
            await zalo.open()
        else:
            print("Cảnh báo:  chưa có ZALO_BOT_TOKEN — khách web cần người thật")
            print("           sẽ KHÔNG có ai được báo. Xem docs/08.")

        khach = KhachWeb(settings, zalo=zalo)

        dispatcher = TurnDispatcher(
            settings,
            client=khach,  # type: ignore[arg-type]  # duck-type: xem web/khach.py
            repo=repo,
            bo_nho=BoNhoRepo(db),
            tu_van=TuVanRepo(db),
            resolver=PrincipalResolver(settings, db),
            limiter=RateLimiter(settings, db),
            quota=QuotaWeb(),  # type: ignore[arg-type]
            buffer=ConversationBuffer(repo),
            router=ModelRouter(settings),
            loop=chon_bo_nao(settings, wiki),
            wiki=wiki,
            kho_skill=kho_skill,
            registry=default_registry(settings),
            command_handler=handle_command,
        )

        app = tao_app(settings, dispatcher=dispatcher, khach=khach, db=db)

        print(f"Chế độ: {settings.che_do}", end="")
        print("  (0 đồng, không gọi API)" if settings.che_do == "tra_cuu" else "")
        print(f"Trang thử:  http://localhost:{settings.web_port}/")
        if settings.web_origins:
            print(f"Cho phép:   {', '.join(settings.web_origins)}")
        else:
            print("Cho phép:   (chưa khai WEB_ORIGINS — mới chỉ thử được ở máy này)")
        print(f"Trần ngày:  {settings.web_tran_ngay} lượt")

        cau_hinh = uvicorn.Config(
            app,
            host=settings.web_host,
            port=settings.web_port,
            log_level="warning",
            access_log=False,
        )
        await uvicorn.Server(cau_hinh).serve()
        await dispatcher.drain()
        if zalo is not None:
            await zalo.close()
        return 0
    finally:
        await db.close()
