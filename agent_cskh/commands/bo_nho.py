"""Lenh ve BO NHO DAI HAN — nguoi bi nho phai xem va xoa duoc.

Bo nho ma nguoi bi nho khong xem duoc la mot cai bay: den luc bot noi mot cau
ky la ("da biet chi thich mau xanh"), khong ai lan ra duoc vi sao no biet. Hai
lenh nay la mot doi — co /nhogi thi phai co /xoanho.

Chi mo tu `student` tro len, giong dung cach `TurnContext.bo_nho_da_biet()` loc.
Nguoi la khong co bo nho: ho la lead, va da co cong cu rieng cho viec do.
"""

from __future__ import annotations

from agent_cskh.harness.turn import TurnContext
from agent_cskh.logging_setup import get_logger

log = get_logger(__name__)


async def cmd_nhogi(ctx: TurnContext) -> bool:
    """/nhogi — xem bot dang nho gi ve minh."""
    ds = await ctx.bo_nho.danh_sach(ctx.principal.user_id)
    if not ds:
        await ctx.reply(
            "Dạ em chưa ghi nhớ gì riêng về anh/chị ạ.\n\n"
            "Anh/chị kể về nhu cầu hay tình huống của mình thì lần sau em nhớ để "
            "tư vấn sát hơn."
        )
        return True

    dong = [f"🧠 Em đang nhớ {len(ds)} điều về anh/chị:", ""]
    for n in ds:
        nguon = " (đội ngũ ghi)" if n.do_doi_ngu_ghi else ""
        dong.append(f"• {n.khoa}: {n.gia_tri}{nguon}")
    dong.append("")
    dong.append("Muốn em quên điều nào thì gõ: /xoanho <tên mục>")
    dong.append("Quên hết: /xoanho tatca")
    await ctx.reply("\n".join(dong))
    return True


async def cmd_xoanho(ctx: TurnContext) -> bool:
    """/xoanho <khoa> | /xoanho tatca — xoa thu bot da nho ve minh."""
    khoa = ctx.event.command_args.strip()
    if not khoa:
        await ctx.reply("Cú pháp: /xoanho <tên mục>\nXoá hết: /xoanho tatca\nXem: /nhogi")
        return True

    if khoa.lower() in ("tatca", "tat ca", "tất cả", "all"):
        n = await ctx.bo_nho.xoa_het(ctx.principal.user_id)
        log.info("xoa_bo_nho", user_id=ctx.principal.user_id[:8], so=n, tat_ca=True)
        await ctx.reply(f"Dạ em đã quên hết {n} mục ạ.")
        return True

    n = await ctx.bo_nho.xoa(ctx.principal.user_id, khoa)
    if n == 0:
        await ctx.reply(f"Dạ em không có mục nào tên '{khoa}' ạ. Gõ /nhogi để xem danh sách.")
        return True
    log.info("xoa_bo_nho", user_id=ctx.principal.user_id[:8], khoa=khoa)
    await ctx.reply(f"Dạ em đã quên mục '{khoa}' rồi ạ.")
    return True
