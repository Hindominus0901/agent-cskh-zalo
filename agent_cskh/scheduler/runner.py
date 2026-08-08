"""Cong viec chay nen.

Sau viec, deu la thu ma neu khong tu dong thi se khong ai lam:
  1. Canh mat ket noi Zalo — bai hoc tu su co 05/08/2026
  2. Canh model chet — bai hoc tu su co khoa API 07/08/2026
  3. Nhac yeu cau ban giao dang treo
  4. Bao cao hang ngay cho chu bot
  5. Canh bao khi sap het han muc tin nhan thang
  6. Don ban ghi chong trung cu

KHONG CO JOB GUI CHU DONG. Zalo co cua so gui chu dong nhung chua ai do duoc
no, va moi tin chu dong an vao han muc 3.000 tin/thang cua chinh ban. Mot
template khong duoc bat mac dinh mot thu chua kiem chung tren OA that cua nguoi
khac. Xem README muc "Chua lam".
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agent_cskh.config import Settings
from agent_cskh.health import Health
from agent_cskh.logging_setup import get_logger
from agent_cskh.outbound.bao_cao import dung_bao_cao
from agent_cskh.security import PrincipalResolver, QuotaGuard
from agent_cskh.store import Database
from agent_cskh.store.repo import ChatRepo, TuVanRepo
from agent_cskh.store.repo.tu_van import TOI_DA_NHAC
from agent_cskh.transport.zalo_client import ZaloClient

log = get_logger(__name__)

# Zalo im lang lau hon nguong nay thi coi la mat ket noi.
NGUONG_MAT_KET_NOI = timedelta(minutes=10)
# Model hong bao nhieu luot lien tiep thi bao chu.
#
# Dem theo SO LOI chu khong theo THOI GIAN — khac han cach canh Zalo. Ly do:
# polling goi Zalo lien tuc du co khach hay khong, nen "lau khong goi duoc" la
# tin hieu that; con model chi duoc goi khi co nguoi nhan tin, nen mot dem yen
# ang cung se ra "lau roi khong goi thanh cong" du khoa van tot.
NGUONG_LOI_MODEL = 3
# Yeu cau ban giao treo lau hon nguong nay thi nhac lai.
NGUONG_NHAC_HANDOFF = timedelta(minutes=30)
# Gian cach giua hai lan nhac cung mot yeu cau.
GIAN_CACH_NHAC = timedelta(hours=2)
# Nhac bao nhieu lan roi thoi han.
#
# Phai co tran. Mot yeu cau treo tu 07/08 15:34 den 08/08 13:29 da sinh ra hon
# chuc canh bao giong het nhau. Canh bao lap lai ma khong ai xu ly duoc thi
# khong con la canh bao — no thanh nhieu, roi nguoi ta tat thong bao di, ke ca
# nhung canh bao that su quan trong.
TOI_DA_NHAC_CHUNG = 3


class Scheduler:
    def __init__(
        self,
        settings: Settings,
        *,
        client: ZaloClient,
        repo: ChatRepo,
        quota: QuotaGuard,
        health: Health,
        health_model: Health | None = None,
        resolver: PrincipalResolver | None = None,
        tu_van: TuVanRepo | None = None,
        db: Database | None = None,
    ) -> None:
        self._s = settings
        self._client = client
        self._repo = repo
        self._quota = quota
        self._health = health
        self._health_model = health_model or Health(ten="Claude")
        self._resolver = resolver
        self._tu_van = tu_van
        self._db = db
        self._sched = AsyncIOScheduler(timezone=settings.timezone)

    def start(self) -> None:
        self._sched.add_job(
            self._canh_ket_noi, "interval", minutes=5, id="canh_ket_noi", max_instances=1
        )
        self._sched.add_job(
            self._canh_model, "interval", minutes=5, id="canh_model", max_instances=1
        )
        self._sched.add_job(
            self._nhac_handoff, "interval", minutes=15, id="nhac_handoff", max_instances=1
        )
        self._sched.add_job(
            self._bao_cao_ngay, "cron", hour=20, minute=0, id="bao_cao_ngay", max_instances=1
        )
        self._sched.add_job(
            self._canh_quota, "cron", hour=9, minute=0, id="canh_quota", max_instances=1
        )
        self._sched.add_job(self._don_dep, "cron", hour=3, minute=0, id="don_dep", max_instances=1)
        self._sched.start()
        log.info("scheduler_bat_dau", so_job=len(self._sched.get_jobs()))

    def shutdown(self) -> None:
        if self._sched.running:
            self._sched.shutdown(wait=False)
            log.info("scheduler_dung")

    # ---------- cong viec ----------
    async def _bao_chu(self, text: str) -> bool:
        """Gui noi dung NOI BO. Cua duy nhat — moi canh bao deu di qua day.

        Kiem tra nguoi nhan truoc khi gui, khong tin ALERT_CHAT_ID vo dieu kien.
        Noi dung qua day gom ca tom tat khach hang va chat_id cua ho; gui nham
        cho mot khach khac vua lo du lieu khach vua lo cach van hanh ben trong.
        """
        target = self._s.alert_chat_id.strip()
        if not target:
            return False
        if self._resolver is not None and not await self._resolver.la_kenh_noi_bo(target):
            # Im lang o day con hon gui nham. Khong gui, va noi that to trong log.
            log.error(
                "alert_chat_id_khong_phai_noi_bo",
                chat_id=target[:8],
                huong_dan="Nhan /whoami cho bot de lay chat_id dung, hoac them chat vao trusted_chats",
            )
            return False
        try:
            # Khong dem quota o day — ZaloClient.send_message da dem roi.
            await self._client.send_message(target, text)
            return True
        except Exception as e:  # noqa: BLE001 - job khong duoc chet
            log.error("job_khong_gui_duoc", error=str(e))
            return False

    async def _canh_ket_noi(self) -> None:
        h = self._health
        if not h.mat_ket_noi_lau_hon(NGUONG_MAT_KET_NOI):
            return
        if h.da_bao_mat_ket_noi:
            return  # da bao roi, khong spam

        phut = int(NGUONG_MAT_KET_NOI.total_seconds() // 60)
        log.error("mat_ket_noi_zalo", so_loi=h.so_loi_lien_tiep)
        # Chinh viec gui canh bao cung di qua Zalo — neu Zalo chet han thi khong
        # gui duoc, nhung neu chi rieng getUpdates chet (nhu su co 05/08) thi
        # sendMessage van chay va canh bao van den noi.
        if await self._bao_chu(
            f"⚠️ BOT MẤT KẾT NỐI VỚI ZALO\n\n"
            f"Không gọi được getUpdates quá {phut} phút.\n\n{h.tom_tat()}\n\n"
            f"Bot vẫn đang chạy và sẽ tự nhận lại tin khi Zalo hồi phục."
        ):
            h.da_bao_mat_ket_noi = True

    async def _canh_model(self) -> None:
        """Model chet thi khach van duoc tra loi — bang cau du phong, hang loat.

        Do la kieu hong nguy hiem nhat: nhin tu ngoai bot van "chay", log van
        chay, chi co dieu khong ai duoc phuc vu. Va cau du phong con hua "em da
        bao cho anh/chi phu trach roi" — loi hua nay chi that neu job nay chay.
        """
        h = self._health_model
        if h.so_loi_lien_tiep < NGUONG_LOI_MODEL:
            return
        if h.da_bao_mat_ket_noi:
            return  # da bao roi, khong spam

        log.error("model_hong", so_loi=h.so_loi_lien_tiep, loi_cuoi=h.loi_cuoi)
        # Zalo van khoe (neu khong thi job canh ket noi da bao), nen tin nay den duoc.
        if await self._bao_chu(
            f"🔴 BOT KHÔNG TRẢ LỜI ĐƯỢC — MODEL HỎNG\n\n"
            f"{h.so_loi_lien_tiep} lượt liên tiếp gọi {h.ten} thất bại. "
            f"Khách vẫn nhắn được nhưng chỉ nhận câu xin lỗi.\n\n"
            f"{h.tom_tat()}\n\n"
            f"Hay gặp nhất: khoá API hết hạn, bị thu hồi, hoặc hết tiền trong tài khoản.\n"
            f"Sửa: thay ANTHROPIC_API_KEY trong .env rồi khởi động lại bot."
        ):
            h.da_bao_mat_ket_noi = True

    async def _bao_cao_ngay(self) -> None:
        """Gui THANG qua _bao_chu.

        Canh bao ve viec he thong hong khong bao gio duoc di qua bat ky hang doi
        nao cua chinh he thong do — hang doi ket la mat luon bao cao noi rang no
        ket.
        """
        try:
            text = await dung_bao_cao(
                repo=self._repo,
                quota=self._quota,
                health_tom_tat=self._health.tom_tat(),
                health_model_tom_tat=self._health_model.tom_tat(),
            )
        except Exception as e:  # noqa: BLE001
            log.exception("dung_bao_cao_loi", error=str(e))
            return
        await self._bao_chu(text)

    async def _nhac_nguoi_duoc_giao(self) -> int:
        """Nhac DUNG nguoi dang cam viec. Tra ve so viec da xu ly o luot nay.

        Khac han `_nhac_handoff`: cai kia keu vao kenh chung, ai doc cung duoc va
        vi vay ai cung tuong nguoi khac lam. Cai nay goi ten mot nguoi.

        Sau TOI_DA_NHAC lan khong phan hoi thi leo len chu bot VA giao cho nguoi
        khac. Chi leo thang ma khong giao lai thi khach van khong co ai — chu bot
        biet them mot tin xau chu khong giai quyet duoc gi.
        """
        if self._tu_van is None:
            return 0
        phut = int(NGUONG_NHAC_HANDOFF.total_seconds() // 60)
        try:
            cho = await self._tu_van.dang_cho(cu_hon_phut=phut)
        except Exception as e:  # noqa: BLE001 - job khong duoc chet
            log.exception("doc_phan_cong_loi", error=str(e))
            return 0

        for v in cho:
            lan = await self._tu_van.ghi_da_nhac(v.phan_cong_id)
            if lan <= TOI_DA_NHAC:
                await self._nhan_rieng(
                    v.tvv.chat_id,
                    f"⏰ NHẮC LẦN {lan} — khách vẫn đang chờ\n\n"
                    f"{v.tom_tat[:400]}\n\n"
                    f"chat_id: {v.chat_id}\n"
                    f"Gõ /nhan trong cuộc trò chuyện đó. Bận thì /nghituvan để bot giao người khác.",
                )
                continue

            nguoi_moi = await self._tu_van.giao_lai(
                v.phan_cong_id, handoff_id=v.handoff_id, chat_id=v.chat_id
            )
            if nguoi_moi is not None:
                await self._nhan_rieng(
                    nguoi_moi.chat_id,
                    f"🔔 VIỆC CHUYỂN SANG ANH/CHỊ — {nguoi_moi.ho_ten}\n\n"
                    f"{v.tom_tat[:400]}\n\n"
                    f"chat_id: {v.chat_id}\n"
                    f"Gõ /nhan trong cuộc trò chuyện đó.",
                )
            await self._bao_chu(
                f"🚨 {v.tvv.ho_ten} KHÔNG PHẢN HỒI sau {lan - 1} lần nhắc\n\n"
                f"Khách đã chờ hơn {phut * lan} phút.\n"
                f"chat_id: {v.chat_id}\n\n"
                + (
                    f"Đã chuyển sang {nguoi_moi.ho_ten}."
                    if nguoi_moi
                    else "KHÔNG còn tư vấn viên nào rảnh — cần người vào ngay."
                )
            )
            log.warning("leo_thang_phan_cong", cu=v.tvv.ho_ten, chat_id=v.chat_id[:8])
        return len(cho)

    async def _nhan_rieng(self, chat_id: str, text: str) -> bool:
        """Nhan rieng cho mot tu van vien. Cung cong kiem nguoi nhan nhu _bao_chu."""
        if self._resolver is not None and not await self._resolver.la_kenh_noi_bo(chat_id):
            log.error("tu_van_vien_khong_phai_kenh_noi_bo", chat_id=chat_id[:8])
            return False
        try:
            await self._client.send_message(chat_id, text)
            return True
        except Exception as e:  # noqa: BLE001 - job khong duoc chet
            log.error("khong_nhan_duoc_tu_van_vien", chat_id=chat_id[:8], error=str(e))
            return False

    async def _nhac_handoff(self) -> None:
        # Viec DA CO nguoi cam duoc nhac rieng, khong keu vao kenh chung nua.
        await self._nhac_nguoi_duoc_giao()

        treo = await self._repo.pending_handoffs()
        if not treo:
            return

        da_co_nguoi_cam = await self._tu_van.chat_dang_giao() if self._tu_van else set()

        gio = datetime.now(tz=UTC)
        can_nhac, lan_cuoi = [], []
        for h in treo:
            if h["chat_id"] in da_co_nguoi_cam:
                continue
            try:
                luc = datetime.fromisoformat(h["requested_at"])
            except (TypeError, ValueError):
                continue
            if gio - luc < NGUONG_NHAC_HANDOFF:
                continue
            # Gian cach giua hai lan nhac, doc tu CSDL chu khong tu bo nho.
            try:
                truoc = datetime.fromisoformat(h["nhac_cuoi_luc"]) if h["nhac_cuoi_luc"] else None
            except (TypeError, ValueError):
                truoc = None
            if truoc and gio - truoc < GIAN_CACH_NHAC:
                continue

            so_lan = int(h["so_lan_nhac"] or 0)
            if so_lan >= TOI_DA_NHAC_CHUNG:
                continue  # da noi lan cuoi roi, thoi
            moi = await self._repo.ghi_da_nhac_handoff(str(h["chat_id"]))
            (lan_cuoi if moi >= TOI_DA_NHAC_CHUNG else can_nhac).append(h)

        for h in can_nhac + lan_cuoi:
            gio_cho = int((gio - datetime.fromisoformat(h["requested_at"])).total_seconds() // 3600)
            cuoi = h in lan_cuoi
            dong = [
                "🔕 LẦN NHẮC CUỐI — KHÁCH VẪN CHƯA CÓ AI" if cuoi else "⏰ CÓ KHÁCH ĐANG CHỜ NGƯỜI",
                "",
                f"{h['summary'][:200]}",
                "",
                f"Đã chờ {gio_cho} tiếng · chat_id: {h['chat_id']}",
                "Gõ /nhan trong cuộc trò chuyện đó để tiếp quản, hoặc /tha để đóng lại.",
            ]
            if cuoi:
                # Noi thang la se im. Mot canh bao lap lai mai ma khong ai xu ly
                # duoc thi khong con la canh bao — no thanh nhieu, va roi nguoi
                # ta tat thong bao di, ke ca nhung canh bao that su quan trong.
                dong.append("")
                dong.append("Em sẽ không nhắc việc này nữa. Nó vẫn nằm trong /baocao.")
            await self._bao_chu("\n".join(dong))

        if can_nhac or lan_cuoi:
            log.info("nhac_handoff", nhac=len(can_nhac), lan_cuoi=len(lan_cuoi))

    async def _canh_quota(self) -> None:
        st = await self._quota.should_warn_owner()
        if st is None:
            return
        await self._bao_chu(
            f"📊 SẮP HẾT HẠN MỨC ZALO\n\n"
            f"Đã dùng {st.used}/{st.limit} tin ({st.pct:.0f}%) trong tháng {st.period}.\n"
            f"Còn {st.remaining} tin.\n\n"
            f"Chạm {self._s.quota_hard_pct}% thì bot chỉ phục vụ người nội bộ."
        )
        log.warning("canh_bao_quota", pct=round(st.pct, 1))

    async def _don_dep(self) -> None:
        n = await self._repo.prune_processed()
        if n:
            log.info("don_dedup_cu", rows=n)
        # Yeu cau ban giao treo qua lau la xac chet: `/baocao` va bang theo doi
        # deu dem "khach dang cho nguoi", va mot dong ba tuan tuoi lam con so do
        # mat nghia.
        cu = await self._repo.dong_handoff_qua_han()
        if cu:
            log.info("dong_handoff_qua_han", rows=cu)
