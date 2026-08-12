"""Ban giao cho nguoi that — DUONG DUY NHAT.

Tach ra khoi `tools/handoff.py` ngay 11/08/2026, khi noi che do `tra_cuu` vao
Zalo. Luc do can ban giao tu mot cho khac (khong co model, khong co tool), va
lua chon la: viet ban thu hai, hay dung chung mot duong.

Viet ban thu hai la sai, va repo nay da co mot vet xe do dung y het:
`TurnContext.notify_staff()` tung khong kiem nguoi nhan trong khi
`Scheduler._bao_chu()` co kiem — mot lop bao ve khong doi xung con nguy hiem hon
khong co lop nao, vi nguoi doc tuong ca hai duong deu duoc canh.

Nhung thu ham nay ep, va se bi mat neu ai do viet duong ban giao thu hai:
  - Nguoi NOI BO thi khong ban giao (khong co ai o tren ho)
  - Da HUMAN_PENDING roi thi khong ban giao lan hai
  - Luon giao cho DUNG MOT tu van vien neu co danh sach
  - Luon bao kenh canh bao, va kiem nguoi nhan truoc khi gui noi dung noi bo
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from agent_cskh.logging_setup import get_logger

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

# Tren WEB, cau tren la mot LOI HUA KHONG GIU DUOC.
#
# Zalo co cuoc tro chuyen ton tai lau dai: tu van vien nhan lai duoc, va khach
# thay tin do ke ca vai tieng sau. Khach web thi dong tab la bien mat — khong co
# `chat_id` nao de nhan toi, khong co hop thu nao de tin nam cho. Bao khach "minh
# cho giup em" o day la hen mot cuoc hen khong ai den duoc.
#
# Nen o web ta doi huong: xin mot duong lien lac THAT (so dien thoai hoac Zalo),
# va noi ro vi sao can — khach chiu cho so khi hieu ly do.
MSG_DA_CHUYEN_WEB = (
    "Dạ em đã ghi nhận và báo cho anh/chị phụ trách rồi ạ. "
    "Anh/chị để lại số điện thoại hoặc Zalo giúp em để bên em liên hệ lại nhé — "
    "vì ở đây sau khi mình đóng trang thì em không nhắn lại được ạ."
)


def la_web(chat_id: str) -> bool:
    return chat_id.startswith("web:")


def loi_da_chuyen(chat_id: str) -> str:
    """Cau bao khach, tuy theo kenh.

    Mot ham nho thay vi hai duong ban giao — xem docstring dau file: duong ban
    giao thu hai la thu chinh module nay sinh ra de ngan.
    """
    return MSG_DA_CHUYEN_WEB if la_web(chat_id) else MSG_DA_CHUYEN


def them_xin_lien_lac(chat_id: str, text: str) -> str:
    """Tren web, ghep them cau xin so dien thoai vao cuoi cau tra loi."""
    if not la_web(chat_id):
        return text
    return text + "\n\n" + MSG_DA_CHUYEN_WEB


@dataclass(frozen=True, slots=True)
class KetQuaBanGiao:
    """`da_mo` False nghia la KHONG mo ban giao moi — xem `ly_do_bo_qua`."""

    da_mo: bool
    da_bao_duoc_nguoi: bool = False
    ly_do_bo_qua: str = ""


async def mo_ban_giao(ctx: TurnContext, *, ly_do: str, tom_tat: str) -> KetQuaBanGiao:
    """Chuyen cuoc tro chuyen sang nguoi that. Khong bao gio nem exception."""
    ctx.da_chuyen_nguoi = True

    # NGUOI NOI CHINH LA CHO DE LEO THANG — khong co ai o tren ho ca.
    #
    # Ngay 08/08/2026 chu bot hoi mot cau ngoai pham vi. Bot mo yeu cau ban giao,
    # va canh bao "CO 1 KHACH DANG CHO NGUOI" duoc gui ve chinh chu bot, noi rang
    # co khach dang cho — khach do la ho. Roi job nhac lap lai moi 2 tieng.
    if ctx.principal.at_least("staff"):
        log.info("bo_qua_handoff_nguoi_noi_bo", role=ctx.principal.role)
        return KetQuaBanGiao(da_mo=False, ly_do_bo_qua="noi_bo")

    # DA chuyen roi thi dung chuyen nua. Ngay 08/08/2026: khach hoi mot cau bot
    # khong tra loi duoc -> bot chuyen nguoi -> khach noi "khong thich" -> bot
    # CHUYEN LAN NUA va doc lai dung cau cu. Nguoi that nhan hai canh bao cho
    # cung mot viec, con khach thi nghe mot cau vo ich hai lan.
    if await ctx.repo.get_state(ctx.chat_id) == "HUMAN_PENDING":
        log.info("bo_qua_chuyen_nguoi_lap", chat_id=ctx.chat_id[:8])
        return KetQuaBanGiao(da_mo=False, ly_do_bo_qua="da_cho_nguoi")

    await ctx.repo.set_state(ctx.chat_id, "HUMAN_PENDING")
    handoff_id = await ctx.repo.open_handoff(ctx.chat_id, reason=ly_do, summary=tom_tat)

    ten = ctx.principal.display_name or "khách"
    than = (
        f"Khách: {ten}\n"
        f"Lý do: {LY_DO.get(ly_do, ly_do)}\n\n"
        f"Tóm tắt:\n{tom_tat}\n\n"
        f"chat_id: {ctx.chat_id}\n"
        f"Nhắn “tôi nhận chat này” trong cuộc trò chuyện đó để tiếp quản."
    )

    # Giao cho DUNG MOT nguoi neu da co danh sach tu van vien. Mot yeu cau roi
    # vao kenh chung thi ba nguoi cung doc va khong ai thay minh co trach nhiem.
    nguoi = await ctx.giao_cho_tu_van_vien(handoff_id, than)

    if nguoi is not None:
        # Van bao kenh chung, nhung noi ro ai dang cam viec.
        da_bao = await ctx.notify_staff(f"🔔 CẦN NGƯỜI TIẾP QUẢN → {nguoi.ho_ten}\n\n{than}")
    else:
        # Chua ai dang ky tu van vien: quay ve hanh vi cu. Khong co danh sach
        # khong duoc lam he thong ngung chay.
        da_bao = await ctx.notify_staff(f"🔔 CẦN NGƯỜI TIẾP QUẢN\n\n{than}")

    log.info(
        "yeu_cau_handoff",
        chat_id=ctx.chat_id[:8],
        ly_do=ly_do,
        giao_cho=nguoi.ho_ten if nguoi else None,
        da_bao=da_bao,
    )
    return KetQuaBanGiao(da_mo=True, da_bao_duoc_nguoi=da_bao)
