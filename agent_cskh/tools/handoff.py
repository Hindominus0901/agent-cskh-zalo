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

from agent_cskh.harness.ban_giao import LY_DO, MSG_DA_CHUYEN, loi_da_chuyen, mo_ban_giao
from agent_cskh.logging_setup import get_logger
from agent_cskh.tools.base import Tool

if TYPE_CHECKING:
    from agent_cskh.harness.turn import TurnContext

log = get_logger(__name__)

__all__ = ["HANDOFF_TOOLS", "LY_DO", "MSG_DA_CHUYEN"]


async def _chuyen_nguoi_that(ctx: TurnContext, args: dict[str, Any]) -> str:
    ly_do = str(args.get("ly_do") or "khong_chac").strip()
    tom_tat = str(args.get("tom_tat") or "").strip()

    if not tom_tat:
        return (
            "Thiếu tham số tom_tat. Hãy tóm tắt lại khách cần gì và bạn đã trao đổi "
            "được tới đâu, để người tiếp quản không phải hỏi lại khách từ đầu."
        )

    # Toan bo phan lam viec THAT nam o `harness/ban_giao.py` — dung chung voi
    # che do `tra_cuu`. O day chi dich ket qua thanh loi day model.
    kq = await mo_ban_giao(ctx, ly_do=ly_do, tom_tat=tom_tat)

    if not kq.da_mo and kq.ly_do_bo_qua == "noi_bo":
        return (
            "Người đang nói chuyện là người NỘI BỘ, nên không có ai để chuyển việc sang — "
            "họ chính là người phụ trách. Đừng nói 'em chuyển cho anh/chị phụ trách'.\n\n"
            "Thay vào đó, nói thẳng là kho tri thức chưa có thông tin này, và nếu đây là "
            "câu hỏi hợp lệ thì gợi ý họ bổ sung một trang mới."
        )

    if not kq.da_mo and kq.ly_do_bo_qua == "da_cho_nguoi":
        return (
            "Cuộc trò chuyện này ĐÃ được chuyển cho người phụ trách từ trước, và họ "
            "đã nhận được thông tin. ĐỪNG nói lại câu 'em đã chuyển cho anh/chị phụ "
            "trách' một lần nữa — khách đã nghe rồi và đang không hài lòng.\n\n"
            "Thay vào đó: thừa nhận ngắn gọn rằng bạn chưa giúp được phần này, rồi "
            "hỏi xem còn việc gì khác bạn hỗ trợ được ngay không. Nói như người thật, "
            "đừng lặp lại mẫu câu."
        )

    if not kq.da_bao_duoc_nguoi:
        # Van chuyen trang thai, nhung noi that de bot khong hua hen qua muc.
        return (
            "Đã ghi nhận yêu cầu chuyển người, nhưng CHƯA gửi được thông báo cho "
            "người phụ trách (chưa cấu hình ALERT_CHAT_ID). Hãy nói với khách là "
            "sẽ có người liên hệ lại, và đừng hứa thời gian cụ thể."
        )
    return (
        "Đã chuyển cho người phụ trách và gửi tóm tắt thành công. "
        f"Bây giờ hãy nói với khách đúng ý này rồi dừng lại: «{loi_da_chuyen(ctx.event.chat_id)}»"
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
