"""TurnContext — moi thu mot luot can biet, gom trong mot cho."""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent_cskh.config import Settings
from agent_cskh.health import Health
from agent_cskh.llm.base import ToolSpec
from agent_cskh.llm.router import ModelRouter, RouteContext
from agent_cskh.logging_setup import get_logger
from agent_cskh.memory import ConversationBuffer
from agent_cskh.security import Principal, PrincipalResolver, QuotaGuard
from agent_cskh.skills import KhoSkill
from agent_cskh.store.repo import BoNhoRepo, ChatRepo, TuVanRepo
from agent_cskh.store.repo.tu_van import TuVanVien
from agent_cskh.tools.base import ToolRegistry
from agent_cskh.transport.base import InboundEvent
from agent_cskh.transport.zalo_client import ZaloClient
from agent_cskh.wiki import WikiStore, strip_accents

log = get_logger(__name__)

MSG_CHUA_CO_TRONG_KHO = (
    "Dạ phần này em chưa nắm chắc nên chưa dám trả lời anh/chị ạ. "
    "Em chuyển sang anh/chị phụ trách để trả lời chính xác cho mình nhé."
)

# Cau tra loi dai hon nguong nay ma khong co goc thi moi bi chan. Cau ngan
# thuong la chao hoi, hoi lai cho ro, hoac tu choi — deu vo hai.
NGUONG_TRA_LOI_DAI = 200

# Tu de hoi tieng Viet, dang bo dau. Dung de nhan ra khach dang thuc su hoi.
_TU_DE_HOI = re.compile(
    r"\b(gi|nao|sao|dau|bao nhieu|bao lau|bao gio|the nao|khi nao|ai|may|"
    r"co khong|duoc khong|co the|giup|huong dan|giai thich|tu van|hoi|xin)\b"
)

# Chu de NGHIEP VU: nhung thu ma tra loi sai se ton tien hoac mat khach.
#
# Can rieng danh sach nay vi khong phai cau hoi nghiep vu nao cung co tu de hoi.
# "gia goi standard" va "cho em bang gia" deu la cau hoi that ma khong khop mau
# nao o tren — de lot thi bot co the bia ra mot con so.
#
# TUY BIEN THEO NGANH: day la danh sach chung cho CSKH. Nganh cua ban co the co
# tu khac ma tra loi sai la mat tien — them vao day, dung them vao prompt. Mot
# tu o day la mot lop chan that; mot cau trong prompt chi la mot loi de nghi.
_CHU_DE_NGHIEP_VU = re.compile(
    r"\b(gia|bang gia|goi |phi |chi phi|cam ket|chinh sach|hoan tien|doi tra|"
    r"uu dai|khuyen mai|giam gia|thanh toan|bao hanh|hop dong|"
    r"giao hang|ship|van chuyen|con hang|het hang|ton kho)\b"
)

# Model DANG tu choi dung cach. Phat no o day thi khac nao day no di bia.
_DANG_TU_CHOI = re.compile(
    r"\b(chua nam|chua ro|khong chac|chua co thong tin|de em (hoi|kiem tra)|"
    r"em chuyen|chuyen sang|phu trach|khong tu van duoc|ngoai pham vi)\b"
)

MSG_BIEN_LAI_AN_TOAN = (
    "Dạ em đã nhận được ảnh chuyển khoản của anh/chị ạ. "
    "Em đang chuyển sang bộ phận kế toán đối soát với sao kê ngân hàng, "
    "sẽ phản hồi lại anh/chị trong giờ làm việc ạ."
)

# Cac cach noi mang nghia "tien da vao". Viet dang bo dau de bat duoc ca khi bot
# tra loi khong dau. KHONG bat "nhan duoc anh" — cau do la an toan.
_MAU_XAC_NHAN_TIEN = [
    re.compile(p)
    for p in (
        r"\bnhan\s+(?:duoc\s+)?tien\b",
        r"\bda\s+nhan\s+(?:duoc\s+)?(?:so\s+)?tien\b",
        r"\bxac\s+nhan\s+(?:da\s+)?thanh\s+toan\b",
        r"\bthanh\s+toan\s+(?:da\s+)?thanh\s+cong\b",
        r"\bchuyen\s+khoan\s+thanh\s+cong\b",
        r"\bda\s+thanh\s+toan\b",
        r"\btien\s+da\s+(?:ve|vao)\b",
        r"\bda\s+vao\s+tai\s+khoan\b",
        r"\bdon\s+(?:hang\s+)?da\s+duoc\s+thanh\s+toan\b",
    )
]


@dataclass(slots=True)
class TurnContext:
    settings: Settings
    event: InboundEvent
    principal: Principal
    session_id: str

    client: ZaloClient
    repo: ChatRepo
    bo_nho: BoNhoRepo
    tu_van: TuVanRepo
    buffer: ConversationBuffer
    router: ModelRouter
    quota: QuotaGuard
    wiki: WikiStore
    registry: ToolRegistry
    # Hai nhip tim tach roi: Zalo co the khoe trong khi model chet, va nguoc lai.
    # Gop chung thi mot ben hong se che mat ben kia.
    health: Health
    health_model: Health
    # Dung de kiem nguoi nhan truoc khi gui noi dung noi bo. None chi trong test
    # khong dung toi notify_staff.
    resolver: PrincipalResolver | None = None
    # Kho quy trinh. None trong test khong dung toi `doc_skill`.
    kho_skill: KhoSkill | None = None

    turn_index: int = 0
    escalation_signal: bool = False
    daily_cost_exceeded: bool = False
    # Bat len khi luot nay vua ghi nhan mot anh chuyen khoan. reply() se soi ky
    # cau tra loi truoc khi gui.
    co_bien_lai_cho_doi_soat: bool = False
    # Bat len khi model DA doc duoc mot trang wiki that trong luot nay. Do la
    # bang chung cau tra loi co goc, khong phai bia.
    da_tra_kho: bool = False
    # Bat len khi model da chuyen viec cho nguoi that.
    da_chuyen_nguoi: bool = False
    # Bat len khi bat ky cong cu nao chay trong luot nay.
    da_chay_cong_cu: bool = False

    @property
    def tools(self) -> list[ToolSpec]:
        """Cong cu principal nay duoc dung. Loc o day, truoc khi gui len model."""
        return self.registry.specs(self.principal.role)

    @property
    def chat_id(self) -> str:
        return self.event.chat_id

    def route_context(self) -> RouteContext:
        text = self.event.text or ""
        return RouteContext(
            text=text,
            has_image=self.event.photo is not None,
            is_stranger=self.principal.is_stranger,
            needs_write_tools=False,  # Phase 3: bat khi co tool ghi
            turn_index=self.turn_index,
            skill_model_hint=None,  # Phase 2: skill selector dien "deep" khi can
            skill_confidence=0.0,
            is_ambiguous=len(text) > 400,
            daily_cost_exceeded=self.daily_cost_exceeded,
        )

    async def bo_nho_da_biet(self) -> str:
        """Nhung gi bot da nho ve nguoi nay, nap vao khoi system THEO NGUOI.

        Chi tu `student` tro len. Nguoi la khong co bo nho: ho la lead, va da co
        cong cu rieng cho viec do — mot cong cu co nguoi doc.

        Loi HO TU KE va ghi chu cua DOI NGU duoc trinh bay tach nhau, va phan tu
        ke duoc noi ro la loi ke. Bot khong duoc dung "em chuyen khoan roi ma"
        cua chinh khach lam can cu de xac nhan bat cu dieu gi.
        """
        if not self.principal.at_least("student"):
            return ""
        try:
            ds = await self.bo_nho.danh_sach(self.principal.user_id)
        except Exception as e:  # noqa: BLE001
            # Thieu bo nho thi bot van tra loi duoc — khong duoc lam hong ca luot.
            log.warning("khong_lay_duoc_bo_nho", error=str(e))
            return ""
        if not ds:
            return ""

        tu_ke = [n for n in ds if not n.do_doi_ngu_ghi]
        doi_ngu = [n for n in ds if n.do_doi_ngu_ghi]

        dong: list[str] = ["# Bạn đã biết gì về người này"]
        if tu_ke:
            dong += ["", "Họ tự kể (là lời kể, KHÔNG phải thông tin đã kiểm chứng —"]
            dong += ["không dùng làm căn cứ cho thanh toán, ghi danh hay ưu đãi):"]
            dong += [f"- {n.khoa}: {n.gia_tri}" for n in tu_ke]
        if doi_ngu:
            dong += ["", "Đội ngũ ghi chú:"]
            dong += [f"- {n.khoa}: {n.gia_tri}" for n in doi_ngu]
        return "\n".join(dong)

    async def _chan_xac_nhan_thanh_toan(self, text: str) -> str:
        """Lop chan cuoi cung cho quy tac 'khong bao gio tu xac nhan da nhan tien'.

        Chi chay trong luot vua ghi nhan mot anh chuyen khoan. Neu cau tra loi lot
        chu mang nghia da nhan tien, thay bang mau an toan va bao ngay cho chu bot —
        vi day la dau hieu prompt hoac model dang truot khoi rang chan.

        Luu y ky thuat: "đã nhận được ẢNH chuyển khoản" la cau AN TOAN va chinh la
        mau ta muon bot dung, nen cac mau do duoi day phai bat "tien" chu khong
        duoc bat "nhan duoc".
        """
        phang = strip_accents(text)
        for mau in _MAU_XAC_NHAN_TIEN:
            if mau.search(phang):
                log.error(
                    "chan_xac_nhan_thanh_toan",
                    chat_id=self.chat_id[:8],
                    mau=mau.pattern,
                    cau_bi_chan=text[:200],
                )
                await self.notify_staff(
                    "🚨 BOT SUÝT XÁC NHẬN ĐÃ NHẬN TIỀN\n\n"
                    f"Câu bị chặn:\n«{text[:400]}»\n\n"
                    f"chat_id: {self.chat_id}\n\n"
                    "Đã thay bằng câu an toàn. Cần xem lại persona/kho tri thức."
                )
                return MSG_BIEN_LAI_AN_TOAN
        return text

    async def _chan_tra_loi_khong_co_goc(self, text: str) -> str:
        """LOP 1 cua viec siet pham vi: bo doi cau tra loi khong co goc.

        Y tuong: kiem soat pham vi manh nhat khong phai mot bo loc doan xem cau
        tra loi co lac de khong — ma la CAT KHA NANG TRA LOI. Voi mot cau hoi
        thuc su, model phai hoac da doc mot trang kho tri thuc, hoac da chuyen
        cho nguoi that. Khong ca hai ma van tra loi dai dong nghia la no dang
        noi tu tri thuc chung, tuc la bia trong ngu canh nay.

        Cung khuon mau voi `_chan_xac_nhan_thanh_toan`: re, dieu kien hep, va
        hong thi keu to.

        DUONG TINH GIA LA RUI RO CHINH, khong phai bo lot. Chan nham nhieu qua
        thi nhan vien se thay bot tu choi lung tung roi tat han no di — luc do
        khong con lop nao ca. Vi vay co RAT NHIEU cua thoat ben duoi, va nguong
        do dai de rong tay.
        """
        if self.da_tra_kho or self.da_chuyen_nguoi:
            return text
        # Nhan vien va chu tu chiu trach nhiem voi cau tra loi ho nhan.
        if self.principal.at_least("staff"):
            return text
        # Luot co chay cong cu khac (luu lead, trich bien lai) la luot co viec
        # that, khong phai luot tra loi suong.
        if self.da_chay_cong_cu:
            return text
        if not self._trong_giong_cau_hoi():
            return text
        if len(text) < NGUONG_TRA_LOI_DAI:
            return text
        if _DANG_TU_CHOI.search(strip_accents(text)):
            # Model DANG noi "em chua nam duoc, de em hoi lai" — do chinh la
            # hanh vi ta muon. Phat no o day thi khac nao day no di bia.
            return text

        log.warning(
            "chan_tra_loi_khong_co_goc",
            chat_id=self.chat_id[:8],
            role=self.principal.role,
            cau_hoi=(self.event.text or "")[:120],
            cau_bi_chan=text[:200],
        )
        # Bot tra loi ma khong co goc = kho tri thuc thieu cho nay. Ghi lai de
        # bao cao 20:00 bien no thanh mot dong trong danh sach viec.
        try:
            await self.repo.ghi_thieu_trang(
                chat_id=self.chat_id,
                user_id=self.principal.user_id,
                cau_hoi=(self.event.text or "")[:500],
                chu_de=None,
            )
        except Exception as e:  # noqa: BLE001
            log.warning("khong_ghi_duoc_thieu_trang", error=str(e))

        await self.repo.set_state(self.chat_id, "HUMAN_PENDING")
        await self.repo.open_handoff(
            self.chat_id,
            reason="ngoai_pham_vi",
            summary=f"Bot trả lời mà không tra kho tri thức.\nKhách hỏi: {(self.event.text or '')[:300]}",
        )
        await self.notify_staff(
            "⚠️ BOT TRẢ LỜI MÀ KHÔNG TRA KHO TRI THỨC\n\n"
            f"Khách hỏi:\n«{(self.event.text or '')[:300]}»\n\n"
            f"Câu bị chặn:\n«{text[:400]}»\n\n"
            f"chat_id: {self.chat_id}\n\n"
            "Đã thay bằng câu an toàn. Nếu câu hỏi này hợp lệ, hãy bổ sung trang "
            "vào kho tri thức để lần sau bot trả lời được."
        )
        return MSG_CHUA_CO_TRONG_KHO

    def _trong_giong_cau_hoi(self) -> bool:
        """Loc tho: chi cong nay bat khi khach thuc su dang hoi mot dieu gi do.

        "Dạ vâng ạ", "cảm ơn em" di thang — chung khong can goc gac nao ca.

        NGAY 08/08/2026 HAM NAY TRA True CHO MOI TIN DAI HON 25 KY TU, va do la
        mot loi that. Dien tap bat duoc: hoc vien viet "em dinh lam khoa nau an,
        chup anh, voi coaching nua a" — mot CAU KE — va bi tinh la cau hoi chi
        vi no dai 52 ky tu. Bot dua ra dung loi khuyen ma persona vua day
        ("ba cai mot luc thi thuong khong cai nao toi noi dau a"), roi bi chan,
        mo ban giao, va bao dong nhan vien.

        Hai duong tinh gia trong 12 tin la 17%. Do la ti le khien nhan vien tat
        han tinh nang di, va luc do khong con lop nao ca — dung cai rui ro da
        viet ra o docstring cua `_chan_tra_loi_khong_co_goc`.

        Do dai KHONG phai dau hieu cua cau hoi. Thay bang hai dau hieu that:
        cach dat cau hoi, hoac chu de nghiep vu (noi tra loi sai ton tien).
        """
        t = strip_accents((self.event.text or "").strip().lower())
        if not t:
            return False
        if "?" in t:
            return True
        if _TU_DE_HOI.search(t):
            return True
        # Cau ke nhung cham vao nghiep vu thi van phai co goc: "gia goi standard"
        # khong co tu de hoi nao ma van la mot cau hoi that.
        return bool(_CHU_DE_NGHIEP_VU.search(t))

    async def notify_staff(self, text: str) -> bool:
        """Gui canh bao cho chu bot / nhom noi bo. False neu chua gui duoc.

        Khong bao gio nem exception — mot canh bao gui hong khong duoc lam hong
        ca luot dang phuc vu khach.

        Kiem nguoi nhan y het `Scheduler._bao_chu()`. Hai ham nay cung mang noi
        dung noi bo (tom tat khach hoi gi, chat_id cua ho, ho ten hoc vien) nen
        phai co cung mot cua. Ngay 07/08/2026 chi lop o scheduler duoc dung, de
        lai duong nay khong canh — mot lop bao ve khong doi xung con nguy hiem
        hon khong co, vi nguoi doc tuong da duoc bao ve ca hai.
        """
        target = ""
        if self.resolver is not None:
            target = (await self.resolver.alert_chat_id()) or ""
        target = (target or self.settings.alert_chat_id).strip()
        if not target:
            log.warning("chua_cau_hinh_kenh_canh_bao")
            return False
        if self.resolver is not None and not await self.resolver.la_kenh_noi_bo(target):
            log.error("alert_chat_id_khong_phai_noi_bo", chat_id=target[:8])
            return False
        try:
            # Khong dem quota o day — ZaloClient.send_message da dem roi.
            await self.client.send_message(target, text)
            return True
        except Exception as e:  # noqa: BLE001
            log.error("khong_gui_duoc_canh_bao", target=target[:8], error=str(e))
            return False

    async def giao_cho_tu_van_vien(self, handoff_id: int, than_tin: str) -> TuVanVien | None:
        """Giao yeu cau ban giao cho nguoi toi luot va nhan tin RIENG cho ho.

        None nghia la chua ai dang ky tu van vien, hoac dia chi cua nguoi duoc
        chon khong con dang tin. Ca hai truong hop nguoi goi phai quay ve bao
        vao kenh chung — mot danh sach rong khong duoc lam he thong ngung chay.

        Tin nay mang ten khach va chat_id cua ho, nen phai qua dung cai cong ma
        notify_staff() va Scheduler._bao_chu() dang dung. Mot ban ghi tu van vien
        cu (nguoi da nghi viec, chat_id go nham) khong duoc thanh duong ro.
        """
        try:
            nguoi = await self.tu_van.giao_viec(handoff_id=handoff_id, chat_id=self.chat_id)
        except Exception as e:  # noqa: BLE001
            log.warning("khong_giao_duoc_viec", error=str(e))
            return None
        if nguoi is None:
            return None

        if self.resolver is not None and not await self.resolver.la_kenh_noi_bo(nguoi.chat_id):
            log.error(
                "tu_van_vien_khong_phai_kenh_noi_bo",
                ho_ten=nguoi.ho_ten,
                chat_id=nguoi.chat_id[:8],
                huong_dan="Nguoi nay can go /nhantuvan lai trong chat rieng voi bot",
            )
            return None

        try:
            await self.client.send_message(
                nguoi.chat_id, f"🔔 VIỆC CỦA ANH/CHỊ — {nguoi.ho_ten}\n\n{than_tin}"
            )
        except Exception as e:  # noqa: BLE001
            log.error("khong_gui_duoc_cho_tu_van_vien", ho_ten=nguoi.ho_ten, error=str(e))
            return None
        return nguoi

    async def reply(self, text: str) -> None:
        """Gui tra loi va ghi lai. Tu cat neu qua 2000 ky tu."""
        text = (text or "").strip()
        if not text:
            log.warning("bo_qua_tra_loi_rong", chat_id=self.chat_id[:8])
            return

        if self.co_bien_lai_cho_doi_soat:
            text = await self._chan_xac_nhan_thanh_toan(text)

        text = await self._chan_tra_loi_khong_co_goc(text)

        # Quota duoc dem BEN TRONG ZaloClient, mot lan cho moi phan da gui. Dem
        # them o day la dem gap doi — loi da ton tai va lam bo dem doc gap ~2 lan
        # thuc te (kiem chung 07/08/2026: sent=29 trong khi chi gui 13 tin).
        ids = await self.client.send_message(self.chat_id, text)
        await self.repo.save_outbound(self.chat_id, self.session_id, text)
        log.info(
            "da_tra_loi",
            chat_id=self.chat_id[:8],
            chars=len(text),
            parts=max(1, len(ids)),
        )
