"""Hai cong cu tri nho: tra lai hoi thoai cu, va ghi nho ve nguoi dang noi.

Lay tu co che tu hoc cua Hermes Agent (Nous Research), nhung KHONG bung nguyen:
Hermes la agent ca nhan, phuc vu mot nguoi dung dang tin. Bot nay noi chuyen
voi hoc vien va nguoi la, nen "agent tu hoc tu hoi thoai" o day dong nghia voi
"nguoi ngoai day duoc bot". Ba khac biet co y:

  1. `ghi_nho` KHONG co tham so "ghi cho ai". No luon ghi ve chinh nguoi dang
     noi. Mot hoc viec khong the noi gi de bot ghi nham vao ho so nguoi khac —
     dieu do khong bieu dat duoc, chu khong phai bi cam.
  2. `min_role="student"`. Nguoi la khong co bo nho. Ho la lead; da co cong cu
     rieng cho viec do, va cong cu do co nguoi doc.
  3. Vai cua nguoi noi duoc ghi kem, va prompt trinh bay loi hoc vien tu ke
     KHAC voi ghi chu cua doi ngu.

Phan Hermes co ma o day KHONG lay: agent tu viet skill moi. Mot skill do bot tu
sinh ra co the di vong qua chinh cac lop chan da dung — khong xac nhan thanh
toan, khong tra loi khi chua tra kho. Viec do phai co nguoi duyet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_cskh.logging_setup import get_logger
from agent_cskh.memory.buffer import DEFAULT_WINDOW
from agent_cskh.store.repo.bo_nho import MAX_KET_QUA, TOI_DA_KY_TU
from agent_cskh.tools.base import Tool

if TYPE_CHECKING:
    from agent_cskh.harness.turn import TurnContext

log = get_logger(__name__)


async def _tim_hoi_thoai(ctx: TurnContext, args: dict[str, Any]) -> str:
    tu_khoa = str(args.get("tu_khoa") or "").strip()
    if not tu_khoa:
        return "Thiếu tham số tu_khoa."

    hits = await ctx.bo_nho.tim(
        ctx.chat_id,
        tu_khoa,
        limit=MAX_KET_QUA,
        # Nhung tin nay model dang nhin thay roi — tra lai chi la nhieu.
        bo_qua_gan_nhat=DEFAULT_WINDOW + 1,
    )
    log.info("tim_hoi_thoai", chat_id=ctx.chat_id[:8], hits=len(hits))

    if not hits:
        return (
            f"Không tìm thấy tin nhắn cũ nào khớp '{tu_khoa}' trong cuộc trò chuyện này. "
            "Nghĩa là chuyện này chưa từng được nhắc tới ở đây — đừng suy đoán, "
            "hãy hỏi lại cho rõ."
        )

    dong = [f"{len(hits)} tin nhắn cũ khớp '{tu_khoa}':", ""]
    for t in hits:
        ai = "Người này nói" if t.huong == "in" else "Bạn đã trả lời"
        dong.append(f"[{t.luc[:10]}] {ai}: {t.van_ban[:300]}")
    dong.append("")
    dong.append("Đây là lời đã nói trong quá khứ, không phải thông tin đã kiểm chứng.")
    return "\n".join(dong)


async def _ghi_nho(ctx: TurnContext, args: dict[str, Any]) -> str:
    khoa = str(args.get("khoa") or "").strip()
    gia_tri = str(args.get("noi_dung") or "").strip()
    if not khoa or not gia_tri:
        return "Thiếu tham số khoa hoặc noi_dung."

    kq = await ctx.bo_nho.ghi(
        # Luon la nguoi dang noi. Khong co duong nao khac.
        user_id=ctx.principal.user_id,
        khoa=khoa,
        gia_tri=gia_tri,
        nguon_role=ctx.principal.role,
        nguon_chat_id=ctx.chat_id,
    )
    if kq == "rong":
        return "Nội dung rỗng, chưa ghi gì cả."
    da_lam = "Đã cập nhật" if kq == "cap_nhat" else "Đã ghi nhớ"
    return (
        f"{da_lam} '{khoa}'. Lần sau nói chuyện bạn sẽ thấy lại điều này. "
        "Đừng nhắc lại với người dùng rằng bạn vừa ghi chú — cứ tiếp tục trả lời bình thường."
    )


TIM_HOI_THOAI = Tool(
    name="tim_hoi_thoai",
    description=(
        "Tìm lại tin nhắn CŨ trong chính cuộc trò chuyện này, xa hơn phần lịch sử bạn "
        "đang nhìn thấy. Dùng khi người dùng nhắc tới điều đã bàn trước đây mà bạn không "
        "thấy trong hội thoại hiện tại ('lần trước em có nói...', 'cái link em gửi hôm nọ'). "
        "Tìm được cả khi gõ không dấu."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "tu_khoa": {
                "type": "string",
                "description": "Vài từ khoá, ví dụ 'link website' hoặc 'mỹ phẩm handmade'.",
            }
        },
        "required": ["tu_khoa"],
    },
    handler=_tim_hoi_thoai,
    min_role="stranger",
    # Doc lai loi cu KHONG phai la tra kho tri thuc. Neu tinh no la "luot da lam
    # viec that" thi model se hoc duoc mot duong vong: tim mot tu bat ky roi tra
    # loi tu tri thuc chung, va lop chan pham vi o reply() thanh vo dung.
    tinh_la_lam_viec=False,
)

GHI_NHO = Tool(
    name="ghi_nho",
    description=(
        "Ghi nhớ một điều về NGƯỜI ĐANG NÓI CHUYỆN để lần sau còn biết: ngành nghề, "
        "tệp khách hàng, sản phẩm đang bán, mục tiêu, khó khăn đang gặp. "
        "Chỉ ghi điều họ tự nói về bản thân và còn đúng ở lần trò chuyện sau. "
        "Không ghi chuyện vụn vặt của riêng cuộc trò chuyện này, không ghi lại những gì "
        "đã có sẵn trong phần thông tin học viên. Mỗi lần một ý."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "khoa": {
                "type": "string",
                "description": (
                    "Tên ngắn không dấu cho loại thông tin, ví dụ 'nganh', 'tep_khach', "
                    "'muc_tieu', 'san_pham'. Ghi lại cùng khoá sẽ thay giá trị cũ."
                ),
            },
            "noi_dung": {
                "type": "string",
                "description": f"Nội dung, tối đa {TOI_DA_KY_TU} ký tự. Viết ngắn gọn.",
            },
        },
        "required": ["khoa", "noi_dung"],
    },
    handler=_ghi_nho,
    min_role="student",
    writes=True,
    # Ghi chu ve nguoi dung cung khong phai lam viec that. Neu tinh, model chi
    # can goi ghi_nho mot phat la duoc mien tra kho tri thuc ca luot.
    tinh_la_lam_viec=False,
)

BO_NHO_TOOLS = [TIM_HOI_THOAI, GHI_NHO]
