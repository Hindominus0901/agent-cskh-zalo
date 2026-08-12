"""Chay che do `tra_cuu` TREN ZALO THAT.

Cung giao dien voi `harness.loop.AgentLoop`: mot ham `run_turn(ctx)`. Nho vay
`TurnDispatcher` chi can chon mot trong hai luc khoi dong, khong phai re nhanh
o giua luot.

## Vi sao file nay ton tai

Truoc 11/08/2026, `agent_cskh/tra_cuu/` CHI duoc import o `cli.py`. Duong chay
Zalo (`app.py` -> `TurnDispatcher` -> `AgentLoop`) khong doc `settings.che_do`
o bat ky dau. Hoc vien de `CHE_DO=tra_cuu` roi chay bot -> bot van goi Claude,
va `config.problems()` khong bao gi vi no chi kiem API key khi `che_do == "ai"`.

Toan bo loi hua "ban 0 dong chay tren Zalo" — diem ban hang chinh cua template —
la khong dung. File nay lam cho no dung.

## Khac AgentLoop the nao

Khong goi model, khong dung cong cu, khong doc persona. Chi:

    tin nhan -> tim kho tri thuc -> tra loi / doan / chuyen nguoi that

Nhung PHAN HANH DONG THAT thi giong het duong `ai`, va do la diem mau chot:
`cli.py` truoc day chi IN RA man hinh "[bot da chuyen cho nguoi that]". Tren
Zalo ma lam vay thi khach duoc hua chuyen nguoi con nhan vien khong biet gi —
te hon han viec bot noi thang "em khong biet".
"""

from __future__ import annotations

from agent_cskh.harness.ban_giao import mo_ban_giao
from agent_cskh.harness.turn import TurnContext
from agent_cskh.logging_setup import get_logger
from agent_cskh.tra_cuu.dinh_tuyen import DinhTuyenTraCuu
from agent_cskh.wiki import WikiStore

log = get_logger(__name__)

MSG_KHONG_DOC_DUOC_FILE = (
    "Dạ Zalo chưa gửi được file tài liệu sang cho em ạ. "
    "Anh/chị chụp màn hình rồi gửi ảnh giúp em nhé."
)

# Che do nay khong xem duoc anh — khong co model thi khong co gi de nhin.
MSG_CO_ANH = (
    "Dạ em nhận được ảnh của anh/chị rồi ạ, nhưng em chưa xem được ảnh. "
    "Em chuyển sang anh/chị phụ trách xem giúp mình nhé."
)


class VongTraCuu:
    """Bo chay che do 0 dong. Khong giu trang thai giua cac luot."""

    def __init__(self, wiki: WikiStore) -> None:
        self._dinh_tuyen = DinhTuyenTraCuu(wiki)

    async def run_turn(self, ctx: TurnContext) -> None:
        # File tai lieu khong bao gio den duoc — tra loi du phong ngay.
        if ctx.event.kind == "unsupported":
            await ctx.reply(MSG_KHONG_DOC_DUOC_FILE)
            return

        # ANH: che do nay mu. Noi that va chuyen nguoi — dac biet quan trong voi
        # anh chuyen khoan, thu ma im lang la kho chiu nhat.
        if ctx.event.photo is not None and not (ctx.event.text or "").strip():
            await self._chuyen_nguoi(
                ctx,
                ly_do="khong_chac",
                tom_tat="Khách gửi ảnh. Bot đang chạy chế độ tra cứu nên không xem được ảnh.",
            )
            await ctx.reply(MSG_CO_ANH)
            return

        kq = self._dinh_tuyen.tra_loi(
            ctx.event.text or "",
            chat_id=ctx.chat_id,
            scope=ctx.principal.visibility_scope,
        )

        # GHI TRUOC KHI TRA LOI. Neu gui that bai thi cau hoi van duoc ghi lai —
        # do la thu duy nhat cho biet kho tri thuc con thieu cho nao.
        if kq.cau_hoi_thieu:
            try:
                await ctx.repo.ghi_thieu_trang(
                    chat_id=ctx.chat_id,
                    user_id=ctx.principal.user_id,
                    cau_hoi=kq.cau_hoi_thieu,
                    chu_de=None,
                )
            except Exception as e:  # noqa: BLE001 - khong duoc lam hong luot
                log.warning("khong_ghi_duoc_thieu_trang", error=str(e))

        if kq.can_nguoi_that:
            await self._chuyen_nguoi(
                ctx,
                ly_do="ngoai_pham_vi",
                tom_tat=f"Kho tri thức chưa có câu trả lời.\nKhách hỏi: {kq.cau_hoi_thieu or ''}",
            )

        await ctx.reply(kq.text)

    async def _chuyen_nguoi(self, ctx: TurnContext, *, ly_do: str, tom_tat: str) -> None:
        """Dung CHUNG duong ban giao voi che do `ai`.

        Khong bao gio nem exception: mot lan ban giao hong khong duoc lam khach
        mat luon cau tra loi.
        """
        try:
            await mo_ban_giao(ctx, ly_do=ly_do, tom_tat=tom_tat)
        except Exception as e:  # noqa: BLE001
            log.exception("khong_mo_duoc_ban_giao", error=str(e))
