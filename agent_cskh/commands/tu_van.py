"""Lenh quan ly tu van vien.

DANG KY PHAI DO CHINH NGUOI DO GO, TRONG CHAT RIENG cua ho voi bot. Cung khuon
voi /datkenhcanhbao, va vi cung mot ly do: nen tang Zalo khong tra chat_id tu
user_id, nen mot ban ghi do nguoi khac them ho se co dia chi doan mo. Tin dau
tien gui di roi vao hu vo — hoac te hon, vao nham mot cuoc tro chuyen co that.

Bat ho tu go mot lenh la cach duy nhat CHUNG MINH duoc dia chi nhan.
"""

from __future__ import annotations

from agent_cskh.harness.turn import TurnContext
from agent_cskh.logging_setup import get_logger

log = get_logger(__name__)


async def cmd_nhantuvan(ctx: TurnContext) -> bool:
    """/nhantuvan [tên] — tự ghi danh làm tư vấn viên, chạy trong chat riêng."""
    if ctx.event.chat_type == "group":
        await ctx.reply(
            "Lệnh này phải gõ trong cuộc trò chuyện RIÊNG giữa anh/chị với bot ạ.\n\n"
            "Lý do: bot cần đúng địa chỉ để nhắn riêng việc cho anh/chị. "
            "Trong nhóm thì địa chỉ là của nhóm, và việc của anh/chị sẽ hiện ra cho cả nhóm đọc."
        )
        return True

    ho_ten = ctx.event.command_args.strip() or ctx.principal.display_name or "Tư vấn viên"
    moi = await ctx.tu_van.dang_ky(
        user_id=ctx.principal.user_id, chat_id=ctx.chat_id, ho_ten=ho_ten
    )
    log.info("dang_ky_tu_van_vien", ho_ten=ho_ten, moi=moi)

    lam_gi = "Đã ghi danh" if moi else "Đã cập nhật"
    await ctx.reply(
        f"✅ {lam_gi} anh/chị **{ho_ten}** vào danh sách tư vấn viên.\n\n"
        "Từ giờ khi có khách cần người, bot sẽ nhắn riêng cho anh/chị theo lượt — "
        "mỗi khách đúng một người, không phải ai cũng nhận rồi không ai làm.\n\n"
        "Nhận việc: gõ /nhan ngay trong cuộc trò chuyện với khách.\n"
        "Bận thì gõ /nghituvan, quay lại thì /nhantuvan."
    )
    return True


async def cmd_nghituvan(ctx: TurnContext) -> bool:
    """/nghituvan — tạm không nhận đơn mới. Không xoá, chỉ tắt."""
    n = await ctx.tu_van.dat_dang_nhan(ctx.principal.user_id, bat=False)
    if not n:
        await ctx.reply("Anh/chị chưa có trong danh sách tư vấn viên ạ. Gõ /nhantuvan để ghi danh.")
        return True
    log.info("tu_van_vien_tam_nghi", user_id=ctx.principal.user_id[:8])
    await ctx.reply(
        "Đã tạm dừng nhận đơn mới cho anh/chị.\n\n"
        "Việc đang cầm vẫn là của anh/chị. Quay lại nhận đơn thì gõ /nhantuvan."
    )
    return True


async def cmd_dstuvan(ctx: TurnContext) -> bool:
    """/dstuvan — ai đang nhận đơn, ai đã nhận bao nhiêu."""
    ds = await ctx.tu_van.danh_sach()
    if not ds:
        await ctx.reply(
            "Chưa có tư vấn viên nào ạ.\n\n"
            "Mỗi người cần tự gõ /nhantuvan trong chat riêng của họ với bot. "
            "Chưa ai ghi danh thì mọi yêu cầu vẫn dồn về kênh cảnh báo chung như cũ."
        )
        return True

    dong = [f"👥 {len(ds)} tư vấn viên", ""]
    for t in ds:
        trang_thai = "đang nhận" if t.dang_nhan else "tạm nghỉ"
        gan_nhat = t.lan_cuoi_giao[:10] if t.lan_cuoi_giao else "chưa lần nào"
        dong.append(f"• {t.ho_ten} — {trang_thai}")
        dong.append(f"  đã nhận {t.so_da_giao} việc · gần nhất {gan_nhat}")
    dong.append("")
    dong.append("Chia theo lượt: ai lâu nhất chưa được giao thì tới lượt.")
    await ctx.reply("\n".join(dong))
    return True


async def cmd_xoatuvan(ctx: TurnContext) -> bool:
    """/xoatuvan <tên hoặc user_id> — bỏ khỏi danh sách. Chỉ chủ bot."""
    khoa = ctx.event.command_args.strip()
    if not khoa:
        await ctx.reply("Cú pháp: /xoatuvan <tên hoặc user_id>\nXem danh sách: /dstuvan")
        return True

    n = await ctx.tu_van.xoa(khoa)
    if not n:
        await ctx.reply(f"Không tìm thấy tư vấn viên '{khoa}'. Gõ /dstuvan để xem danh sách.")
        return True
    log.info("xoa_tu_van_vien", khoa=khoa)
    await ctx.reply(
        f"Đã bỏ '{khoa}' khỏi danh sách tư vấn viên.\n\n"
        "Lịch sử việc đã giao vẫn giữ nguyên. Nếu chỉ nghỉ tạm thì lần sau dùng /nghituvan."
    )
    return True
