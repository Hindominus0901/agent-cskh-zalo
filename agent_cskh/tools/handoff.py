"""Ban giao cho nguoi that.

Ba tinh huong bat buoc chuyen: khach doi gap nguoi, bot khong chac, hoac viec
nam ngoai pham vi. Sau khi chuyen, bot IM LANG tuyet doi cho den khi nhan vien
go /tha — vi khong gi lam khach buc bang viec vua duoc hua chuyen nguoi xong
lai co con bot chen vao giua.

Luong: bot goi tool -> trang thai HUMAN_PENDING -> gui tom tat vao chat canh bao
-> nhan vien go /nhan -> HUMAN_ACTIVE (bot im) -> /tha -> BOT.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_cskh.logging_setup import get_logger
from agent_cskh.tools.base import Tool

if TYPE_CHECKING:
    from agent_cskh.harness.turn import TurnContext

log = get_logger(__name__)

LY_DO = {
    "khach_yeu_cau": "Khách chủ động xin gặp người",
    "khong_chac": "Bot không chắc câu trả lời",
    "ngoai_pham_vi": "Ngoài phạm vi kho tri thức",
    "thanh_toan": "Liên quan thanh toán, cần đối soát",
    "khieu_nai": "Khách phàn nàn hoặc khiếu nại",
}

MSG_DA_CHUYEN = (
    "Dạ em đã chuyển thông tin sang anh/chị phụ trách rồi ạ. "
    "Mình chờ giúp em trong giờ làm việc nhé."
)


async def _chuyen_nguoi_that(ctx: TurnContext, args: dict[str, Any]) -> str:
    ly_do = str(args.get("ly_do") or "khong_chac").strip()
    tom_tat = str(args.get("tom_tat") or "").strip()

    if not tom_tat:
        return (
            "Thiếu tham số tom_tat. Hãy tóm tắt lại khách cần gì và bạn đã trao đổi "
            "được tới đâu, để người tiếp quản không phải hỏi lại khách từ đầu."
        )

    # DA chuyen roi thi dung chuyen nua. Ngay 08/08/2026: khach hoi mot cau bot
    # khong tra loi duoc -> bot chuyen nguoi -> khach noi "khong thich" -> bot
    # CHUYEN LAN NUA va doc lai dung cau cu. Nguoi that nhan hai canh bao cho
    # cung mot viec, con khach thi nghe mot cau vo ich hai lan.
    #
    # Lap lai mot cau da khong lam khach hai long lan dau la cach chac chan de
    # ho buc them.
    ctx.da_chuyen_nguoi = True

    # NGUOI NOI CHINH LA CHO DE LEO THANG — khong co ai o tren ho ca.
    #
    # Ngay 08/08/2026 chu bot hoi mot cau ngoai pham vi. Bot mo yeu cau ban giao,
    # va canh bao "CO 1 KHACH DANG CHO NGUOI" duoc gui ve chinh chu bot, noi rang
    # co khach dang cho — khach do la ho. Roi job nhac lap lai moi 2 tieng.
    #
    # `_chan_tra_loi_khong_co_goc` trong turn.py da bo qua staff tro len tu truoc.
    # Tang cong cu thi chua, va mot lop bao ve khong doi xung con nguy hiem hon
    # khong co: nguoi doc tuong ca hai duong deu duoc canh.
    if ctx.principal.at_least("staff"):
        log.info("bo_qua_handoff_nguoi_noi_bo", role=ctx.principal.role)
        return (
            "Người đang nói chuyện là người NỘI BỘ, nên không có ai để chuyển việc sang — "
            "họ chính là người phụ trách. Đừng nói 'em chuyển cho anh/chị phụ trách'.\n\n"
            "Thay vào đó, nói thẳng là kho tri thức chưa có thông tin này, và nếu đây là "
            "câu hỏi hợp lệ thì gợi ý họ bổ sung một trang bằng /themtrang."
        )

    da_cho_nguoi = await ctx.repo.get_state(ctx.chat_id) == "HUMAN_PENDING"

    if da_cho_nguoi:
        log.info("bo_qua_chuyen_nguoi_lap", chat_id=ctx.chat_id[:8])
        return (
            "Cuộc trò chuyện này ĐÃ được chuyển cho người phụ trách từ trước, và họ "
            "đã nhận được thông tin. ĐỪNG nói lại câu 'em đã chuyển cho anh/chị phụ "
            "trách' một lần nữa — khách đã nghe rồi và đang không hài lòng.\n\n"
            "Thay vào đó: thừa nhận ngắn gọn rằng bạn chưa giúp được phần này, rồi "
            "hỏi xem còn việc gì khác bạn hỗ trợ được ngay không. Nói như người thật, "
            "đừng lặp lại mẫu câu."
        )

    await ctx.repo.set_state(ctx.chat_id, "HUMAN_PENDING")
    handoff_id = await ctx.repo.open_handoff(ctx.chat_id, reason=ly_do, summary=tom_tat)

    ten = ctx.principal.display_name or "khách"
    than = (
        f"Khách: {ten}\n"
        f"Lý do: {LY_DO.get(ly_do, ly_do)}\n\n"
        f"Tóm tắt:\n{tom_tat}\n\n"
        f"chat_id: {ctx.chat_id}\n"
        f"Gõ /nhan trong cuộc trò chuyện đó để tiếp quản."
    )

    # Giao cho DUNG MOT nguoi neu da co danh sach tu van vien. Mot yeu cau roi
    # vao kenh chung thi ba nguoi cung doc va khong ai thay minh co trach nhiem.
    nguoi = await ctx.giao_cho_tu_van_vien(handoff_id, than)
    sent = nguoi is not None

    if nguoi is not None:
        # Van bao kenh chung, nhung noi ro ai dang cam viec — de chu bot theo doi
        # duoc ma khong phai hoi.
        await ctx.notify_staff(f"🔔 CẦN NGƯỜI TIẾP QUẢN → {nguoi.ho_ten}\n\n{than}")
    else:
        # Chua ai dang ky tu van vien: quay ve hanh vi cu. Khong co danh sach
        # khong duoc lam he thong ngung chay.
        sent = await ctx.notify_staff(f"🔔 CẦN NGƯỜI TIẾP QUẢN\n\n{than}")

    log.info(
        "yeu_cau_handoff",
        chat_id=ctx.chat_id[:8],
        ly_do=ly_do,
        giao_cho=nguoi.ho_ten if nguoi else None,
        da_bao=sent,
    )

    if not sent:
        # Van chuyen trang thai, nhung noi that de bot khong hua hen qua muc.
        return (
            "Đã ghi nhận yêu cầu chuyển người, nhưng CHƯA gửi được thông báo cho "
            "người phụ trách (chưa cấu hình ALERT_CHAT_ID). Hãy nói với khách là "
            "sẽ có người liên hệ lại, và đừng hứa thời gian cụ thể."
        )
    return (
        "Đã chuyển cho người phụ trách và gửi tóm tắt thành công. "
        f"Bây giờ hãy nói với khách đúng ý này rồi dừng lại: «{MSG_DA_CHUYEN}»"
    )


CHUYEN_NGUOI_THAT = Tool(
    name="chuyen_nguoi_that",
    description=(
        "Chuyển cuộc trò chuyện cho người phụ trách. Dùng khi: khách xin gặp người thật; "
        "bạn không chắc câu trả lời; câu hỏi ngoài kho tri thức; khách gửi ảnh chuyển "
        "khoản; khách phàn nàn. Sau khi gọi công cụ này, hãy báo khách rồi DỪNG LẠI — "
        "đừng cố trả lời tiếp câu hỏi đã chuyển đi."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "ly_do": {
                "type": "string",
                "enum": list(LY_DO),
                "description": "Lý do chuyển.",
            },
            "tom_tat": {
                "type": "string",
                "description": (
                    "Tóm tắt cho người tiếp quản: khách là ai, cần gì, đã trao đổi tới "
                    "đâu, còn vướng chỗ nào. Viết đủ để họ không phải hỏi lại khách."
                ),
            },
        },
        "required": ["ly_do", "tom_tat"],
    },
    handler=_chuyen_nguoi_that,
    min_role="stranger",
)

HANDOFF_TOOLS = [CHUYEN_NGUOI_THAT]
