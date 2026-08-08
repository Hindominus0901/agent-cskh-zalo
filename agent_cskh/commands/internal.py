"""Lenh cho nhan vien va chu bot."""

from __future__ import annotations

import asyncio

from agent_cskh.harness.turn import TurnContext
from agent_cskh.logging_setup import get_logger

log = get_logger(__name__)


async def cmd_trangthai(ctx: TurnContext) -> bool:
    st = await ctx.quota.status()
    bar_len = 20
    filled = min(bar_len, int(st.pct / 100 * bar_len))
    bar = "█" * filled + "░" * (bar_len - filled)
    await ctx.reply(
        f"Hạn mức Zalo tháng {st.period}\n"
        f"{bar} {st.pct:.1f}%\n"
        f"Đã dùng {st.used}/{st.limit} tin — còn {st.remaining} tin.\n\n"
        "Gói Basic giới hạn 3.000 tin/tháng và 50 người dùng/bot."
    )
    return True


async def cmd_nhan(ctx: TurnContext) -> bool:
    """Nhan vien tiep quan hoi thoai. Bot im lang cho den khi /tha."""
    await ctx.repo.set_state(ctx.chat_id, "HUMAN_ACTIVE")
    await ctx.repo.claim_handoff(ctx.chat_id, ctx.principal.user_id)
    # Dong phan cong lai, du nguoi go /nhan khong phai nguoi duoc giao.
    # Viec da co nguoi lam thi khong duoc nhac nua — nhac tiep se day mot
    # dong nghiep thu hai vao cung mot cuoc tro chuyen.
    await ctx.tu_van.danh_dau_da_nhan(ctx.chat_id)
    await ctx.reply("Đã tiếp quản hội thoại này. Bot sẽ im lặng cho tới khi anh/chị gõ /tha.")
    log.info("handoff_tiep_quan", chat_id=ctx.chat_id[:8], by=ctx.principal.user_id[:8])
    return True


async def cmd_tha(ctx: TurnContext) -> bool:
    await ctx.repo.set_state(ctx.chat_id, "BOT")
    await ctx.repo.release_handoff(ctx.chat_id, ctx.principal.user_id)
    await ctx.reply("Đã trả hội thoại lại cho bot.")
    log.info("handoff_tra_lai", chat_id=ctx.chat_id[:8], by=ctx.principal.user_id[:8])
    return True


async def cmd_suckhoe(ctx: TurnContext) -> bool:
    """Trang thai ket noi va kho tri thuc — kiem tra tu dien thoai, khong can mo may."""
    kho = ctx.wiki.stats(ctx.principal.visibility_scope)
    treo = await ctx.repo.pending_handoffs(limit=50)
    leads = await ctx.repo.count_leads()
    await ctx.reply(
        f"🩺 SỨC KHOẺ BOT\n\n"
        f"{ctx.health.tom_tat()}\n\n"
        # Lenh nay chay duoc nghia la model dang song — nhung van in ra, vi con
        # so loi lien tiep cho biet co dang chap chon hay khong.
        f"{ctx.health_model.tom_tat()}\n\n"
        f"Kho tri thức: {kho['trang']} trang, {kho['ky_tu']:,} ký tự\n"
        f"Khách đang chờ người: {len(treo)}\n"
        f"Tổng lead đã lưu: {leads}"
    )
    return True


async def cmd_lead(ctx: TurnContext) -> bool:
    """Xem nhanh lead moi nhat."""
    rows = await ctx.repo.recent_leads(limit=10)
    if not rows:
        await ctx.reply("Chưa có lead nào được lưu.")
        return True
    dong = [f"📇 {len(rows)} LEAD GẦN NHẤT", ""]
    for r in rows:
        lien_he = r.get("phone") or r.get("email") or "(chưa có liên hệ)"
        dong.append(f"• {r.get('name') or '(chưa rõ tên)'} — {lien_he}")
        if r.get("service"):
            dong.append(f"  {r['service'][:80]}")
        dong.append(f"  giai đoạn: {r.get('stage')}")
    await ctx.reply("\n".join(dong))
    return True


async def cmd_bienlai(ctx: TurnContext) -> bool:
    """Danh sach anh chuyen khoan dang cho doi soat voi sao ke."""
    rows = await ctx.repo.pending_payment_claims(limit=15)
    if not rows:
        await ctx.reply("Không có biên lai nào đang chờ đối soát.")
        return True

    dong = [f"💰 {len(rows)} BIÊN LAI CHỜ ĐỐI SOÁT", ""]
    for r in rows:
        tien = f"{r['amount']:,}đ".replace(",", ".") if r.get("amount") else "(không đọc được)"
        dong.append(f"#{r['id']} — {tien}")
        if r.get("txn_time"):
            dong.append(f"  lúc {r['txn_time']}")
        if r.get("memo"):
            dong.append(f"  nội dung: {r['memo'][:60]}")
        dong.append(f"  ảnh: {r.get('media_path') or '(chưa tải được)'}")
        dong.append(f"  chat_id: {r['chat_id']}")
        dong.append("")
    dong.append("Đối chiếu với sao kê ngân hàng rồi tự cập nhật trong data/app.db.")
    await ctx.reply("\n".join(dong))
    return True


async def cmd_nap(ctx: TurnContext) -> bool:
    """Nap lai kho tri thuc tu dia — sua file xong khong phai khoi dong lai bot."""
    truoc = ctx.wiki.stats(ctx.principal.visibility_scope)["trang"]
    n = await asyncio.to_thread(ctx.wiki.reload)
    sau = ctx.wiki.stats(ctx.principal.visibility_scope)

    thay_doi = sau["trang"] - truoc
    dau = "+" if thay_doi > 0 else ""
    await ctx.reply(
        f"Đã nạp lại kho tri thức.\n"
        f"Tổng: {n} trang ({sau['trang']} trang bạn đọc được"
        f"{f', {dau}{thay_doi}' if thay_doi else ''}).\n"
        f"Dung lượng: {sau['ky_tu']:,} ký tự."
    )
    log.info("nap_lai_wiki", tong=n, by=ctx.principal.user_id[:8])
    return True


async def cmd_quen(ctx: TurnContext) -> bool:
    """Bat dau phien moi — huu ich khi test."""
    await ctx.repo.set_state(ctx.chat_id, "BOT")
    await ctx.repo.reset_session(ctx.chat_id)
    await ctx.reply("Đã bắt đầu phiên mới. Em quên ngữ cảnh cũ rồi ạ.")
    return True


async def cmd_baocao(ctx: TurnContext) -> bool:
    """Xem bao cao bat cu luc nao, khong doi den 20h.

    Dung chung ham voi job hang ngay — mot nguon su that duy nhat, va sua mot
    cho la ca hai duong doi theo.
    """
    from agent_cskh.outbound.bao_cao import dung_bao_cao

    await ctx.reply(
        await dung_bao_cao(
            repo=ctx.repo,
            quota=ctx.quota,
            health_tom_tat=ctx.health.tom_tat(),
            health_model_tom_tat=ctx.health_model.tom_tat(),
        )
    )
    return True
