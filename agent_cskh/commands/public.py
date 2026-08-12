"""Lenh ai cung dung duoc."""

from __future__ import annotations

from agent_cskh.harness.turn import TurnContext

# KHONG MOT DAU GACH CHEO NAO TRONG CAC CHUOI DUOI DAY.
#
# Khach hang that khong go lenh, va chu shop cung khong — ho la nguoi ban hang,
# khong phai nguoi dung terminal. In mot bang lenh ra truoc mat ho khong lam ho
# manh hon: no lam ho tuong rang phai hoc thuoc moi dung duoc bot, roi thoi
# khong nhan nua.
#
# Moi viec o day deu lam duoc bang loi noi — xem `agent_cskh/y_dinh/`.
# Lenh `/...` van chay ngam lam duong lui, nhung khong o dau quang cao chung.
HELP_PUBLIC = """\
Em có thể giúp anh/chị:
• Hỏi đáp về sản phẩm, dịch vụ, cách bên em làm việc
• Gửi ảnh để em xem giúp (biên lai, sản phẩm, chụp màn hình)
• Cần gặp người thật thì anh/chị cứ nói “cho em gặp nhân viên” ạ

Anh/chị cứ nhắn bình thường thôi ạ, không cần theo cú pháp nào cả.

Lưu ý: Zalo chưa gửi được file tài liệu sang cho em, anh/chị chụp màn hình gửi ảnh giúp em nhé.\
"""

HELP_HOC_VIEN = """\
Vài câu anh/chị hay cần:
• “em nhớ gì về tôi” — xem những gì em đã ghi nhớ
• “quên giùm tôi …” — bảo em quên một mục đi

Ngoài ra cứ nhắn bình thường ạ.\
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
Anh/chị cứ nói bằng lời, em hiểu — không cần cú pháp gì cả.

Hằng ngày:
• “báo cáo hôm nay” — việc cần làm, và những câu em chưa trả lời được
• “tôi nhận chat này” / “trả lại cho bot” — tiếp quản hoặc trả lại
• “khách mới” · “biên lai” — ai vừa để lại thông tin, ảnh chuyển khoản chờ đối soát

Hỏi thêm: “hướng dẫn kho”, “hướng dẫn việc”, “hướng dẫn hệ thống”\
"""

HELP_CHU_DE = {
    "kho": """\
KHO TRI THỨC — sửa được ngay từ điện thoại, chỉ cần nói:
• “có những trang nào”
• “xem trang bang-gia”
• “thêm trang công khai bang-gia” rồi xuống dòng viết nội dung
• “sửa trang bang-gia” rồi xuống dòng — bản cũ vẫn giữ lại
• “xoá trang bang-gia” — em hỏi lại một câu trước khi xoá
• “nạp lại kho” — sau khi sửa file trực tiếp trên máy

Ba mức: công khai (ai cũng đọc) · khách quen · nội bộ (chỉ nhân viên)\
""",
    "viec": """\
CHIA VIỆC CHO NGƯỜI THẬT
• “tôi nhận chat này” — anh/chị tiếp quản, em im lặng
• “trả lại cho bot” — em trả lời tiếp
• “bắt đầu lại” — xoá trạng thái bàn giao của cuộc trò chuyện này

Nhận khách theo lượt:
• “tôi nhận tư vấn” — tự ghi danh, PHẢI nói trong chat riêng của mình với em
• “tôi tạm nghỉ” — không nhận đơn mới, việc đang cầm vẫn của mình
• “ai đang nhận khách” — xem danh sách

Có danh sách thì mỗi khách được giao đúng một người. Chưa ai ghi danh thì
mọi yêu cầu vẫn dồn về kênh cảnh báo chung.\
""",
    "hethong": """\
HỆ THỐNG
• “sức khoẻ” — nhịp tim Zalo và model, kho tri thức
• “còn bao nhiêu tin” — hạn mức tháng này
• “cảnh báo gửi về đâu”
• “đặt kênh cảnh báo” — đặt CHÍNH cuộc trò chuyện này làm nơi nhận
• “id của tôi”

Đừng đặt kênh cảnh báo trong nhóm có khách hàng: nội dung cảnh báo kèm tên
khách và mã cuộc trò chuyện của họ. Em sẽ hỏi lại trước khi đặt.\
""",
}


async def cmd_start(ctx: TurnContext) -> bool:
    name = ctx.principal.display_name or "anh/chị"
    await ctx.reply(
        f"Dạ em chào {name} ạ. Em là trợ lý AI, anh/chị cần hỗ trợ gì em giúp ngay.\n\n"
        "Anh/chị cứ nhắn bình thường thôi ạ."
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
