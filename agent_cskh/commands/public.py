"""Lenh ai cung dung duoc."""

from __future__ import annotations

from agent_cskh.harness.turn import TurnContext

HELP_PUBLIC = """\
Em có thể giúp anh/chị:
• Hỏi đáp về sản phẩm, dịch vụ, cách bên em làm việc
• Gửi ảnh để em xem giúp (biên lai, sản phẩm, chụp màn hình)
• /lienhe — kết nối với người phụ trách

Lưu ý: Zalo Bot chưa nhận được file tài liệu, anh/chị chụp màn hình gửi ảnh giúp em nhé.\
"""

# CO Y CHI LIET KE HAI LENH.
#
# Khach nhan tin nhu noi chuyen, khong ai hoc thuoc menu. Do mot danh sach lenh
# ra truoc mat ho khong lam ho manh hon — no lam ho tuong rang phai nho lenh moi
# dung duoc bot, roi thoi khong nhan nua.
#
# Hai lenh o day deu lien quan den SU DONG Y: xem va xoa thu bot nho ve minh.
# Nhung viec con lai deu lam duoc bang loi.
HELP_HOC_VIEN = """\
Dành cho khách quen:
• /nhogi — em đang nhớ gì về anh/chị
• /xoanho <mục> — bảo em quên đi

Ngoài ra anh/chị cứ nhắn bình thường ạ, không cần nhớ lệnh.\
"""

# /help NGAN, phan con lai tra theo nhom.
#
# Ba muoi lenh trong mot buc tuong chu thi khong ai doc — va thu bi bo qua
# khong phai nhung lenh hiem, ma la CA DANH SACH. Nguoi ta luot mot cai roi
# quay lai lam thu cong.
#
# Sau dong dau la nhung viec lam moi ngay. Con lai nam sau `/help <nhom>`, chi
# tra khi thuc su can. Cung nguyen tac da ap cho hoc vien.
HELP_INTERNAL = """\
Hằng ngày:
• /baocao — việc cần làm hôm nay, và những câu bot chưa trả lời được
• /nhan · /tha — tiếp quản hội thoại này / trả lại cho bot
• /lead · /bienlai — khách mới để lại thông tin, ảnh chuyển khoản chờ đối soát

Tra thêm khi cần:
/help kho · /help viec · /help hethong\
"""

HELP_CHU_DE = {
    "kho": """\
KHO TRI THỨC (sửa được ngay từ điện thoại)
• /dstrang — có những trang nào
• /xemtrang <tên-trang> — đọc một trang
• /themtrang <mức> <tên-trang> rồi xuống dòng viết nội dung
• /suatrang — ghi đè, bản cũ vẫn giữ lại
• /xoatrang <tên-trang>
• /nap — nạp lại sau khi sửa file trực tiếp trên máy

Mức: public (ai cũng đọc) · hocvien (khách quen) · internal (chỉ nội bộ)\
""",
    "viec": """\
CHIA VIỆC CHO NGƯỜI THẬT
• /nhan — tiếp quản hội thoại này, bot im lặng cho tới khi /tha
• /tha — trả lại cho bot
• /quen — xoá trạng thái bàn giao của chat này

Nhận khách theo lượt:
• /nhantuvan [tên] — tự ghi danh, PHẢI gõ trong chat riêng của mình với bot
• /nghituvan — tạm không nhận đơn mới, việc đang cầm vẫn của mình
• /dstuvan — ai đang nhận, đã nhận bao nhiêu
• /xoatuvan <tên> — bỏ khỏi danh sách (chỉ chủ bot)

Có danh sách thì mỗi khách được giao đúng một người. Chưa ai ghi danh thì
mọi yêu cầu vẫn dồn về kênh cảnh báo chung.\
""",
    "hethong": """\
HỆ THỐNG
• /suckhoe — nhịp tim Zalo và model, kho tri thức
• /trangthai — hạn mức tin nhắn tháng này
• /kenhcanhbao — cảnh báo đang gửi về đâu
• /datkenhcanhbao — đặt CHÍNH chat này làm nơi nhận (chỉ chủ bot)
• /whoami — user_id và chat_id của mình

Đừng chạy /datkenhcanhbao trong nhóm có khách hàng: nội dung cảnh báo kèm tên
khách và chat_id của họ.\
""",
}


async def cmd_start(ctx: TurnContext) -> bool:
    name = ctx.principal.display_name or "anh/chị"
    await ctx.reply(
        f"Dạ em chào {name} ạ. Em là trợ lý AI, anh/chị cần hỗ trợ gì em giúp ngay.\n\n"
        "Gõ /help để xem em làm được những gì."
    )
    return True


async def cmd_help(ctx: TurnContext) -> bool:
    """Moi vai thay dung phan cua minh. Doc mot danh sach lenh khong dung duoc
    vua vo ich vua lo su ton tai cua chuc nang noi bo.

    `/help <nhom>` chi danh cho noi bo — nguoi la va hoc vien go vao se nhan
    dung ban ngan cua ho, khong bao gio thay ten cac nhom lenh quan tri.
    """
    nhom = ctx.event.command_args.strip().lower()
    if nhom and ctx.principal.at_least("staff"):
        chi_tiet = HELP_CHU_DE.get(nhom)
        if chi_tiet is None:
            ds = " · ".join(f"/help {k}" for k in HELP_CHU_DE)
            await ctx.reply(f"Không có nhóm '{nhom}'.\n\nCác nhóm: {ds}")
            return True
        await ctx.reply(chi_tiet)
        return True

    phan = [HELP_PUBLIC]
    if ctx.principal.at_least("student"):
        phan.append(HELP_HOC_VIEN)
    if ctx.principal.at_least("staff"):
        phan.append(HELP_INTERNAL)
    await ctx.reply("\n\n".join(phan))
    return True


async def cmd_lienhe(ctx: TurnContext) -> bool:
    # Phase 3 noi tool handoff that vao day.
    await ctx.repo.set_state(ctx.chat_id, "HUMAN_PENDING")
    await ctx.reply(
        "Dạ em đã chuyển tin của anh/chị sang bộ phận phụ trách ạ. "
        "Mình chờ giúp em trong giờ làm việc nhé."
    )
    return True


async def cmd_whoami(ctx: TurnContext) -> bool:
    """Cong khai co chu dich: chinh la cach chu bot lay user_id cua minh lan dau."""
    p = ctx.principal
    await ctx.reply(
        "Thông tin định danh của anh/chị trên Zalo:\n"
        f"user_id: {p.user_id}\n"
        f"chat_id: {p.chat_id}\n"
        f"loại chat: {ctx.event.chat_type}\n"
        f"quyền hiện tại: {p.role}\n\n"
        "Dán user_id vào OWNER_USER_IDS trong file .env để nhận quyền quản trị."
    )
    return True
