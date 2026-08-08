"""Xu ly anh khach gui.

Bon kich ban: bien lai chuyen khoan, anh san pham, anh tai lieu (trich chu),
anh loi/bao hanh. Ba kich ban sau chi can model nhin anh — anh da duoc dinh kem
san vao luot, khong can cong cu gi.

Kich ban BIEN LAI thi khac, va day la cho nguy hiem nhat cua ca he thong.

## Vi sao trich_bien_lai tu mo ban giao

Anh bien lai chinh sua duoc bang dien thoai trong ba muoi giay. Chi sao ke ngan
hang moi la bang chung. Neu bot noi "da nhan duoc tien" mot lan sai, do la mat
tien that.

Nen thay vi dat luat trong prompt roi mong model nho, ta lam cho viec vi pham
BAT KHA THI VE CAU TRUC:

  1. Khong ton tai cong cu nao danh dau don "da thanh toan". Model khong co
     duong nao lam viec do, du bi du do the nao.
  2. Chinh trich_bien_lai tu mo ban giao va bao nguoi that — khong the trich
     xuat ma "quen" chuyen.
  3. payment_claims.verified_by chi nguoi dien, khong co code nao ghi vao.
  4. Neu cau tra loi cua bot van lot chu xac nhan, TurnContext.reply chan lai
     va thay bang mau an toan (xem turn.py).

Bon lop. Prompt la lop mong nhat trong so do.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import httpx

from agent_cskh.logging_setup import get_logger
from agent_cskh.tools.base import Tool

if TYPE_CHECKING:
    from agent_cskh.harness.turn import TurnContext

log = get_logger(__name__)

MAX_ANH_BYTES = 8 * 1024 * 1024
NGAN_HANG = re.compile(r"[A-Za-zÀ-ỹ ]{2,40}")

MAU_TRA_LOI = (
    "Dạ em đã nhận được ảnh chuyển khoản ạ. Em ghi nhận: {so_tien}"
    "{thoi_gian}{noi_dung}. "
    "Em đang chuyển sang bộ phận kế toán đối soát với sao kê, "
    "sẽ phản hồi lại anh/chị trong giờ làm việc ạ."
)


async def _tai_anh(ctx: TurnContext, url: str, claim_id: int) -> str | None:
    """Tai anh ve de nguoi doi soat con xem duoc sau khi URL cua Zalo het han."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            data = r.content[:MAX_ANH_BYTES]
    except Exception as e:  # noqa: BLE001 - tai anh hong khong duoc lam hong luot
        log.warning("khong_tai_duoc_anh", error=str(e)[:120])
        return None

    ctx.settings.media_dir.mkdir(parents=True, exist_ok=True)
    path = ctx.settings.media_dir / f"bienlai-{claim_id:06d}.jpg"
    try:
        path.write_bytes(data)
    except OSError as e:
        log.warning("khong_luu_duoc_anh", error=str(e))
        return None
    return str(path)


async def _trich_bien_lai(ctx: TurnContext, args: dict[str, Any]) -> str:
    if ctx.event.photo is None or not ctx.event.photo.url:
        return (
            "Lượt này không có ảnh nào. Chỉ dùng công cụ này khi khách vừa gửi ảnh "
            "biên lai chuyển khoản."
        )

    def lay(k: str) -> str | None:
        v = args.get(k)
        if v is None or str(v).strip() in ("", "null", "None"):
            return None
        return " ".join(str(v).split())[:200]

    so_tien_raw = args.get("so_tien")
    so_tien: int | None = None
    if so_tien_raw is not None:
        chi_so = re.sub(r"\D", "", str(so_tien_raw))
        so_tien = int(chi_so) if chi_so else None

    thoi_gian = lay("thoi_gian")
    noi_dung = lay("noi_dung")
    ngan_hang = lay("ngan_hang")
    bon_so_cuoi = lay("bon_so_cuoi")

    if so_tien is None and not noi_dung:
        return (
            "Không đọc được số tiền lẫn nội dung chuyển khoản. Đừng đoán — hãy xin "
            "khách chụp lại rõ hơn, và đừng gọi lại công cụ này cho tới khi có ảnh mới."
        )

    claim_id = await ctx.repo.save_payment_claim(
        chat_id=ctx.chat_id,
        user_id=ctx.principal.user_id,
        media_url=ctx.event.photo.url,
        amount=so_tien,
        txn_time=thoi_gian,
        memo=noi_dung,
        bank=ngan_hang,
        acct_last4=bon_so_cuoi,
    )
    duong_dan = await _tai_anh(ctx, ctx.event.photo.url, claim_id)
    if duong_dan:
        await ctx.repo.set_payment_media_path(claim_id, duong_dan)

    tien_str = f"{so_tien:,}đ".replace(",", ".") if so_tien else "(không đọc được số tiền)"

    # Ban giao la BAT BUOC va nam ngay trong cong cu nay — khong the trich xuat
    # roi "quen" chuyen cho nguoi.
    tom_tat = (
        f"Khách gửi ảnh chuyển khoản.\n"
        f"Số tiền: {tien_str}\n"
        f"Thời gian: {thoi_gian or '(không đọc được)'}\n"
        f"Nội dung: {noi_dung or '(không đọc được)'}\n"
        f"Ngân hàng: {ngan_hang or '(không đọc được)'}\n"
        f"4 số cuối: {bon_so_cuoi or '(không đọc được)'}\n"
        f"Ảnh: {duong_dan or ctx.event.photo.url}\n\n"
        f"CẦN ĐỐI SOÁT VỚI SAO KÊ NGÂN HÀNG. Bot đã KHÔNG xác nhận gì với khách."
    )
    await ctx.repo.set_state(ctx.chat_id, "HUMAN_PENDING")
    await ctx.repo.open_handoff(ctx.chat_id, reason="thanh_toan", summary=tom_tat)
    await ctx.notify_staff(
        f"💰 CÓ ẢNH CHUYỂN KHOẢN CẦN ĐỐI SOÁT\n\n{tom_tat}\n\nchat_id: {ctx.chat_id}"
    )

    ctx.co_bien_lai_cho_doi_soat = True

    log.info(
        "trich_bien_lai",
        claim_id=claim_id,
        chat_id=ctx.chat_id[:8],
        co_so_tien=so_tien is not None,
        da_luu_anh=duong_dan is not None,
    )

    mau = MAU_TRA_LOI.format(
        so_tien=tien_str,
        thoi_gian=f" lúc {thoi_gian}" if thoi_gian else "",
        noi_dung=f", nội dung «{noi_dung}»" if noi_dung else "",
    )
    return (
        f"Đã ghi nhận (mã {claim_id}) và chuyển bộ phận đối soát.\n\n"
        f"Bây giờ trả lời khách ĐÚNG nội dung này, không thêm bớt:\n«{mau}»\n\n"
        "TUYỆT ĐỐI không nói đã nhận được tiền, đã xác nhận thanh toán, hay đơn đã "
        "được thanh toán. Ảnh biên lai không phải bằng chứng."
    )


TRICH_BIEN_LAI = Tool(
    name="trich_bien_lai",
    description=(
        "Dùng khi khách gửi ảnh biên lai / màn hình chuyển khoản ngân hàng. "
        "Bạn đọc ảnh rồi truyền vào những gì ĐỌC ĐƯỢC — trường nào không rõ thì bỏ "
        "trống, tuyệt đối không đoán. Công cụ sẽ tự lưu và chuyển bộ phận đối soát. "
        "Bạn KHÔNG có thẩm quyền xác nhận đã nhận tiền."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "so_tien": {
                "type": "string",
                "description": "Số tiền đọc được, ví dụ '1.500.000' hoặc '1500000'.",
            },
            "thoi_gian": {"type": "string", "description": "Thời gian giao dịch trên ảnh."},
            "noi_dung": {"type": "string", "description": "Nội dung chuyển khoản."},
            "ngan_hang": {"type": "string", "description": "Tên ngân hàng."},
            "bon_so_cuoi": {"type": "string", "description": "4 số cuối tài khoản nhận."},
        },
        "required": [],
    },
    handler=_trich_bien_lai,
    min_role="stranger",
)

VISION_TOOLS = [TRICH_BIEN_LAI]
