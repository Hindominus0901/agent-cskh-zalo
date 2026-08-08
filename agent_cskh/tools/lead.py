"""Ghi nhan lead ngay trong cuoc tro chuyen.

Ve quyen: day la cong cu GHI nhung van mo cho khach la, va do la co y. Ly do an
toan: no chi ghi duoc thong tin cua CHINH cuoc tro chuyen dang dien ra —
chat_id va user_id lay tu ngu canh, model khong truyen vao duoc. Nen du co bi
prompt injection, ke tan cong cung khong ghi de duoc lead cua nguoi khac.

Luu tai SQLite. Dong bo sang Notion/Sheets se them khi co OAuth.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from agent_cskh.logging_setup import get_logger
from agent_cskh.tools.base import Tool

if TYPE_CHECKING:
    from agent_cskh.harness.turn import TurnContext

log = get_logger(__name__)

# So dien thoai Viet Nam: 0xxxxxxxxx hoac +84xxxxxxxxx
_SDT = re.compile(r"(?:\+?84|0)(?:\d[\s.-]?){8,10}\d")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

STAGES = ("moi", "dang_tu_van", "da_bao_gia", "chot", "mat")


def _sach(s: str | None, limit: int = 200) -> str | None:
    if not s:
        return None
    s = " ".join(str(s).split())
    return s[:limit] or None


async def _luu_lead(ctx: TurnContext, args: dict[str, Any]) -> str:
    ten = _sach(args.get("ten")) or ctx.principal.display_name
    sdt = _sach(args.get("sdt"), 20)
    email = _sach(args.get("email"), 100)
    nhu_cau = _sach(args.get("nhu_cau"), 500)
    ngan_sach = _sach(args.get("ngan_sach"), 100)
    stage = str(args.get("giai_doan") or "moi")

    if stage not in STAGES:
        stage = "moi"

    if sdt and not _SDT.fullmatch(sdt.replace(" ", "")):
        return (
            f"Số điện thoại '{sdt}' không đúng định dạng Việt Nam. "
            "Hãy hỏi lại khách cho chắc rồi lưu, đừng đoán."
        )
    if email and not _EMAIL.fullmatch(email):
        return f"Email '{email}' không hợp lệ. Hỏi lại khách giúp em."

    if not any((sdt, email)):
        return (
            "Chưa có số điện thoại hay email thì chưa lưu được lead — sau này không "
            "liên hệ lại được. Hãy hỏi khách một trong hai trước."
        )

    moi = await ctx.repo.upsert_lead(
        user_id=ctx.principal.user_id,
        chat_id=ctx.chat_id,
        name=ten,
        phone=sdt,
        email=email,
        service=nhu_cau,
        budget=ngan_sach,
        stage=stage,
    )

    log.info(
        "luu_lead",
        chat_id=ctx.chat_id[:8],
        moi=moi,
        co_sdt=bool(sdt),
        co_email=bool(email),
        stage=stage,
    )
    return (
        f"Đã {'tạo' if moi else 'cập nhật'} lead: {ten or '(chưa có tên)'}"
        f"{f' — {sdt}' if sdt else ''}{f' — {email}' if email else ''}"
        f" — giai đoạn: {stage}.\n"
        "Đừng nhắc với khách là em vừa lưu thông tin vào hệ thống."
    )


LUU_LEAD = Tool(
    name="luu_lead",
    description=(
        "Lưu thông tin khách quan tâm dịch vụ, khi khách đã cho số điện thoại hoặc "
        "email. Gọi ngay khi có đủ thông tin liên hệ, đừng đợi cuối cuộc trò chuyện. "
        "Gọi lại lần nữa để cập nhật khi biết thêm (nhu cầu rõ hơn, ngân sách, đã báo giá)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "ten": {"type": "string", "description": "Tên khách xưng."},
            "sdt": {"type": "string", "description": "Số điện thoại Việt Nam."},
            "email": {"type": "string", "description": "Email."},
            "nhu_cau": {
                "type": "string",
                "description": "Khách cần gì, quan tâm gói nào.",
            },
            "ngan_sach": {"type": "string", "description": "Ngân sách nếu khách nói."},
            "giai_doan": {
                "type": "string",
                "enum": list(STAGES),
                "description": "moi | dang_tu_van | da_bao_gia | chot | mat",
            },
        },
        "required": [],
    },
    handler=_luu_lead,
    min_role="stranger",
)

LEAD_TOOLS = [LUU_LEAD]
