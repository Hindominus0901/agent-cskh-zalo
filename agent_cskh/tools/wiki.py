"""Hai cong cu tra cuu kho tri thuc.

Bot da co san `index.md` trong system prompt (phan duoc cache), nen thuong no
biet ngay can doc trang nao va chi ton MOT vong goi cong cu. `tim_trang` chi
dung khi index khong du ro.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_cskh.logging_setup import get_logger
from agent_cskh.tools.base import Tool

if TYPE_CHECKING:
    from agent_cskh.harness.turn import TurnContext

log = get_logger(__name__)

MAX_KET_QUA = 5


async def _doc_trang(ctx: TurnContext, args: dict[str, Any]) -> str:
    slug = str(args.get("ten_trang") or "").strip()
    if not slug:
        return "Thiếu tham số ten_trang."

    page = ctx.wiki.read(slug, ctx.principal.visibility_scope)
    if page is None:
        # Khong phan biet "khong ton tai" voi "ngoai quyen" — nguoi la khong duoc
        # biet trang noi bo co ton tai hay khong.
        goi_y = ctx.wiki.search(slug, ctx.principal.visibility_scope, limit=3)
        if goi_y:
            ds = ", ".join(p.slug for p in goi_y)
            return f"Không có trang '{slug}'. Trang gần giống: {ds}"
        return f"Không có trang '{slug}' trong kho tri thức."

    # Chi bat co khi doc duoc trang THAT. Doc trang khong ton tai roi tra loi
    # tiep thi van la bia — va do chinh la duong vong ma lop chan o reply() phai
    # bit lai.
    ctx.da_tra_kho = True
    log.info("doc_trang", slug=page.slug, role=ctx.principal.role)
    return page.render()


async def _tim_trang(ctx: TurnContext, args: dict[str, Any]) -> str:
    query = str(args.get("tu_khoa") or "").strip()
    if not query:
        return "Thiếu tham số tu_khoa."

    hits = ctx.wiki.search(query, ctx.principal.visibility_scope, limit=MAX_KET_QUA)
    log.info("tim_trang", query=query[:50], hits=len(hits), role=ctx.principal.role)

    if not hits:
        # GHI LAI, khong chi tra loi roi thoi.
        #
        # Day la khoanh khac duy nhat ta biet chac kho tri thuc con thieu cho
        # nao: model da chu dong di tim va khong thay gi. Khong ghi thi chu bot
        # khong bao gio biet hoc vien dang hoi nhung gi ma bot khong dap duoc,
        # va kho tri thuc se mai dung o cho no dang dung.
        #
        # Ghi TU DONG chu khong lam mot cong cu rieng: mot cong cu thi model
        # phai nho goi, con day thi khong the quen.
        try:
            await ctx.repo.ghi_thieu_trang(
                chat_id=ctx.chat_id,
                user_id=ctx.principal.user_id,
                cau_hoi=(ctx.event.text or "")[:500],
                chu_de=query[:100],
            )
        except Exception as e:  # noqa: BLE001 - ghi nhat ky khong duoc lam hong luot
            log.warning("khong_ghi_duoc_thieu_trang", error=str(e))
        return (
            f"Không tìm thấy trang nào cho '{query}'. "
            "Kho tri thức chưa có thông tin này — hãy nói thật với khách và đề nghị "
            "chuyển sang người phụ trách."
        )

    q_norm = query.lower()
    lines = [f"Tìm thấy {len(hits)} trang cho '{query}':", ""]
    for p in hits:
        lines.append(f"[[{p.slug}]] — {p.summary}")
        lines.append(f"   ...{p.snippet(q_norm)}...")
        lines.append("")
    lines.append("Dùng doc_trang để đọc toàn văn trang cần thiết trước khi trả lời.")
    return "\n".join(lines)


DOC_TRANG = Tool(
    name="doc_trang",
    description=(
        "Đọc toàn văn một trang trong kho tri thức. Dùng công cụ này TRƯỚC KHI trả lời "
        "bất kỳ câu hỏi nào về dịch vụ, giá, quy trình, chính sách. Tên trang lấy từ "
        "danh mục kho tri thức trong hướng dẫn hệ thống, viết dạng [[ten-trang]]."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "ten_trang": {
                "type": "string",
                "description": "Tên trang, ví dụ 'bang-gia-2026'. Không kèm đuôi .md.",
            }
        },
        "required": ["ten_trang"],
    },
    handler=_doc_trang,
    min_role="stranger",
    tinh_la_lam_viec=False,
)

TIM_TRANG = Tool(
    name="tim_trang",
    description=(
        "Tìm trang trong kho tri thức theo từ khoá, khi danh mục chưa đủ rõ để biết "
        "nên đọc trang nào. Trả về tên trang kèm đoạn trích. Tìm được không dấu."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "tu_khoa": {
                "type": "string",
                "description": "Từ khoá tìm kiếm, ví dụ 'giá gói standard'.",
            }
        },
        "required": ["tu_khoa"],
    },
    handler=_tim_trang,
    min_role="stranger",
    tinh_la_lam_viec=False,
)

WIKI_TOOLS = [DOC_TRANG, TIM_TRANG]
