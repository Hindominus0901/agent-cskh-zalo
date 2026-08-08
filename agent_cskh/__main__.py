"""Diem vao: python -m agent_cskh [--check]"""

from __future__ import annotations

import argparse
import asyncio
import sys

from agent_cskh.config import get_settings
from agent_cskh.logging_setup import get_logger, setup_logging
from agent_cskh.store import Database


async def _check() -> int:
    settings = get_settings()
    setup_logging(settings)
    log = get_logger("check")

    settings.ensure_dirs()
    print("Thu muc: da tao/xac nhan data/, knowledge/, tests/fixtures/")

    async with Database(settings) as db:
        health = await db.health()
    print(
        f"SQLite: {health['path']}\n"
        f"  journal_mode={health['journal_mode']} "
        f"foreign_keys={health['foreign_keys']} tables={health['tables']}"
    )

    problems = settings.problems()
    if problems:
        print("\nThieu cau hinh:")
        for p in problems:
            print(f"  - {p}")
        print("\nChua san sang chay bot. Dien .env roi chay lai.")
        log.warning("config_incomplete", count=len(problems))
        return 1

    print("\nCau hinh OK")
    return 0


async def _run() -> int:
    from agent_cskh.app import Application

    settings = get_settings()
    setup_logging(settings)
    log = get_logger("main")

    # OWNER_USER_IDS trong khong chan chay — phai chay bot roi gui /whoami moi lay duoc.
    blocking = [p for p in settings.problems() if not p.startswith("OWNER_USER_IDS")]
    if blocking:
        for p in blocking:
            log.error("config_problem", problem=p)
            print(f"  - {p}")
        print("\nCau hinh chua day du. Chay `python -m agent_cskh --check` de xem chi tiet.")
        return 1

    if not settings.owner_user_ids:
        print("Chua co OWNER_USER_IDS — gui /whoami cho bot de lay user_id cua ban.\n")

    settings.ensure_dirs()
    log.info("starting", transport=settings.transport)
    return await Application(settings).run()


def main() -> int:
    parser = argparse.ArgumentParser(prog="agent_cskh")
    parser.add_argument("--check", action="store_true", help="Kiem tra cau hinh va CSDL roi thoat")
    args = parser.parse_args()
    return asyncio.run(_check() if args.check else _run())


if __name__ == "__main__":
    sys.exit(main())
