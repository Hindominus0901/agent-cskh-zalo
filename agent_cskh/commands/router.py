"""Dinh tuyen lenh /... — xu ly trong code, khong ton token LLM.

Tra ve True neu lenh da duoc xu ly; False thi de agent loop lo tiep.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from agent_cskh.commands import bo_nho, internal, public, quan_tri, tu_van
from agent_cskh.harness.turn import TurnContext
from agent_cskh.logging_setup import get_logger
from agent_cskh.security.whitelist import Role

log = get_logger(__name__)

Handler = Callable[[TurnContext], Awaitable[bool]]

# ten lenh -> (handler, quyen toi thieu)
COMMANDS: dict[str, tuple[Handler, Role]] = {
    "start": (public.cmd_start, "stranger"),
    "help": (public.cmd_help, "stranger"),
    "lienhe": (public.cmd_lienhe, "stranger"),
    "whoami": (public.cmd_whoami, "stranger"),
    "nhogi": (bo_nho.cmd_nhogi, "student"),
    "xoanho": (bo_nho.cmd_xoanho, "student"),
    "nhantuvan": (tu_van.cmd_nhantuvan, "staff"),
    "nghituvan": (tu_van.cmd_nghituvan, "staff"),
    "dstuvan": (tu_van.cmd_dstuvan, "staff"),
    "xoatuvan": (tu_van.cmd_xoatuvan, "owner"),
    "trangthai": (internal.cmd_trangthai, "staff"),
    "baocao": (internal.cmd_baocao, "staff"),
    "datkenhcanhbao": (quan_tri.cmd_datkenhcanhbao, "owner"),
    "kenhcanhbao": (quan_tri.cmd_kenhcanhbao, "staff"),
    "themtrang": (quan_tri.cmd_themtrang, "staff"),
    "suatrang": (quan_tri.cmd_suatrang, "staff"),
    "xoatrang": (quan_tri.cmd_xoatrang, "staff"),
    "xemtrang": (quan_tri.cmd_xemtrang, "staff"),
    "dstrang": (quan_tri.cmd_dstrang, "staff"),
    "nhan": (internal.cmd_nhan, "staff"),
    "tha": (internal.cmd_tha, "staff"),
    "quen": (internal.cmd_quen, "staff"),
    "nap": (internal.cmd_nap, "staff"),
    "suckhoe": (internal.cmd_suckhoe, "staff"),
    "lead": (internal.cmd_lead, "staff"),
    "bienlai": (internal.cmd_bienlai, "staff"),
}

# Bi danh cho nguoi quen go tieng Anh.
ALIASES = {"status": "trangthai", "claim": "nhan", "release": "tha", "contact": "lienhe"}


async def handle(ctx: TurnContext) -> bool:
    name = ctx.event.command
    if not name:
        return False
    name = ALIASES.get(name, name)

    entry = COMMANDS.get(name)
    if entry is None:
        # Lenh la — de agent tra loi tu nhien thay vi bao loi kho khan.
        log.debug("lenh_khong_biet", command=name)
        return False

    handler, min_role = entry
    if not ctx.principal.at_least(min_role):
        # Khong tiet lo su ton tai cua lenh noi bo voi nguoi la.
        log.info("tu_choi_lenh", command=name, role=ctx.principal.role)
        return False

    log.info("chay_lenh", command=name, role=ctx.principal.role)
    return await handler(ctx)
