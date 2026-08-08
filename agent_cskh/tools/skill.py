"""Cong cu doc thân bài mot skill.

DAY LA CHO BAN GOC BI HUT. Trong `C:\\TOM`, muc luc skill bao model "doc file
`skills/<ten>/SKILL.md` bang `doc_trang`" — nhung `doc_trang` chi quet thu muc
kho tri thuc, con `skills/` la thu muc anh em. Model thay ten skill trong prompt
va khong bao gio mo duoc thân bài. Muc luc do thanh mot danh sach trang tri.

Tach thanh cong cu rieng chu khong gop `skills/` vao kho tri thuc, vi hai thu do
co mo hinh quyen khac nhau:

    knowledge/wiki/   phan quyen theo thu muc public/hocvien/internal
    skills/           khong phan quyen — quy trinh noi bo, khach khong bao gio doc

Gop chung se buoc phai dat skill vao mot trong ba muc do, va bat ky lua chon nao
cung sai: `public/` thi khach doc duoc quy trinh ban hang, `internal/` thi bot
phuc vu khach lai khong doc duoc chinh quy trinh cua no.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_cskh.logging_setup import get_logger
from agent_cskh.tools.base import Tool

if TYPE_CHECKING:
    from agent_cskh.harness.turn import TurnContext

log = get_logger(__name__)


async def _doc_skill(ctx: TurnContext, args: dict[str, Any]) -> str:
    ten = str(args.get("ten") or "").strip()
    if not ten:
        return "Thiếu tham số ten."

    kho = getattr(ctx, "kho_skill", None)
    if kho is None:
        return "Chưa có kỹ năng nào được nạp."

    s = kho.doc(ten)
    if s is None:
        # Khong phan biet "khong ton tai" voi "chua duoc duyet" — y het cach
        # `doc_trang` khong phan biet "khong co" voi "ngoai quyen".
        co = ", ".join(x.ten for x in kho.duoc_nap()) or "(chưa có kỹ năng nào)"
        return f"Không có kỹ năng '{ten}'. Đang có: {co}"

    log.info("doc_skill", ten=s.ten, role=ctx.principal.role)
    return f"# Kỹ năng: {s.ten}\n\n{s.than_bai}"


DOC_SKILL = Tool(
    name="doc_skill",
    description=(
        "Đọc các bước của một kỹ năng đã có. Dùng khi gặp đúng tình huống mà kỹ năng đó "
        "mô tả — đọc rồi làm theo, đừng tự nghĩ lại quy trình. Tên lấy từ mục Kỹ năng "
        "trong hướng dẫn hệ thống."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "ten": {
                "type": "string",
                "description": "Tên kỹ năng, ví dụ 'lay-thong-tin-khach'.",
            }
        },
        "required": ["ten"],
    },
    handler=_doc_skill,
    min_role="stranger",
    # Doc quy trinh khong phai LAM viec. Tinh no la lam viec thi model hoc duoc
    # mot duong vong: goi `doc_skill` cho co roi tra loi tu tri thuc chung, va
    # lop chan `_chan_tra_loi_khong_co_goc` se cho di qua.
    tinh_la_lam_viec=False,
)

SKILL_TOOLS = [DOC_SKILL]
