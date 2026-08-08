"""Chia don cho tu van vien theo luot, va theo dau viec da giao.

Mot yeu cau ban giao roi vao kenh chung thi ba nguoi cung doc va khong ai thay
minh co trach nhiem. O day moi yeu cau co DUNG MOT nguoi duoc giao, co ten, va
co dong ho — 2 lan khong nhan thi leo len chu bot va giao lai nguoi khac.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from agent_cskh.logging_setup import get_logger
from agent_cskh.store import Database

log = get_logger(__name__)

# Nhac bao nhieu lan khong ai nhan thi leo len chu bot va giao nguoi khac.
TOI_DA_NHAC = 2


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


@dataclass(frozen=True, slots=True)
class TuVanVien:
    id: int
    user_id: str
    chat_id: str
    ho_ten: str
    dang_nhan: bool
    so_da_giao: int
    lan_cuoi_giao: str | None


@dataclass(frozen=True, slots=True)
class ViecDaGiao:
    phan_cong_id: int
    handoff_id: int
    chat_id: str
    giao_luc: str
    nhac_lan: int
    tvv: TuVanVien
    tom_tat: str


def _doc_tvv(r) -> TuVanVien:  # noqa: ANN001
    return TuVanVien(
        id=int(r["id"]),
        user_id=r["user_id"],
        chat_id=r["chat_id"],
        ho_ten=r["ho_ten"],
        dang_nhan=bool(r["dang_nhan"]),
        so_da_giao=int(r["so_da_giao"]),
        lan_cuoi_giao=r["lan_cuoi_giao"],
    )


class TuVanRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    # ---------- danh sach tu van vien ----------
    async def dang_ky(self, *, user_id: str, chat_id: str, ho_ten: str) -> bool:
        """Ghi danh mot tu van vien. True = moi, False = cap nhat nguoi da co.

        `chat_id` phai la chat RIENG cua chinh nguoi do, da duoc chung minh bang
        viec ho tu go lenh. Nguoi goi ham nay chiu trach nhiem kiem dieu do.
        """
        now = _now()
        da_co = await self._db.fetch_val("SELECT 1 FROM tu_van_vien WHERE user_id = ?", (user_id,))
        await self._db.execute(
            "INSERT INTO tu_van_vien (user_id, chat_id, ho_ten, dang_nhan, created_at) "
            "VALUES (?, ?, ?, 1, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "  chat_id = excluded.chat_id, ho_ten = excluded.ho_ten, dang_nhan = 1",
            (user_id, chat_id, ho_ten, now),
        )
        return not da_co

    async def dat_dang_nhan(self, user_id: str, *, bat: bool) -> int:
        return await self._db.execute_rowcount(
            "UPDATE tu_van_vien SET dang_nhan = ? WHERE user_id = ?", (int(bat), user_id)
        )

    async def xoa(self, khoa: str) -> int:
        """Xoa theo user_id hoac ho ten. Ban ghi phan_cong cu giu nguyen lam lich su."""
        return await self._db.execute_rowcount(
            "DELETE FROM tu_van_vien WHERE user_id = ? OR ho_ten = ?", (khoa, khoa)
        )

    async def danh_sach(self) -> list[TuVanVien]:
        rows = await self._db.fetch_all(
            "SELECT * FROM tu_van_vien ORDER BY dang_nhan DESC, ho_ten COLLATE NOCASE"
        )
        return [_doc_tvv(r) for r in rows]

    async def theo_user_id(self, user_id: str) -> TuVanVien | None:
        r = await self._db.fetch_one("SELECT * FROM tu_van_vien WHERE user_id = ?", (user_id,))
        return _doc_tvv(r) if r else None

    # ---------- chia luot ----------
    async def _nguoi_toi_luot(self, *, tru_id: int | None = None) -> TuVanVien | None:
        """Nguoi dang nhan don va LAU NHAT chua duoc giao.

        Xep theo BO DEM `luot_thu`, khong theo dong ho.

        Ngay 08/08/2026 ham nay xep theo `lan_cuoi_giao` — mot moc thoi gian.
        Tren Windows `datetime.now()` chi phan giai khoang 15ms, nen hai lan
        giao sat nhau nhan dung cung mot moc; thu tu sup ve `id ASC` va nguoi co
        id nho nhat duoc giao lien tiep. Round-robin bien thanh "ai vao truoc om
        het", va no hong y het tren may that khi hai khach nhan tin cach nhau
        vai mili giay.

        Bo dem thi khong co do phan giai. `luot_thu IS NOT NULL` dat truoc trong
        ORDER BY de nguoi chua bao gio duoc giao luon len dau.
        """
        rows = await self._db.fetch_all(
            "SELECT * FROM tu_van_vien WHERE dang_nhan = 1 AND id IS NOT ? "
            "ORDER BY luot_thu IS NOT NULL, luot_thu ASC, id ASC LIMIT 1",
            (tru_id,),
        )
        return _doc_tvv(rows[0]) if rows else None

    async def giao_viec(
        self, *, handoff_id: int, chat_id: str, tru_id: int | None = None
    ) -> TuVanVien | None:
        """Giao mot yeu cau ban giao cho nguoi toi luot. None = chua co ai nhan don.

        None KHONG phai loi: chua ai dang ky tu van vien thi he thong quay ve
        hanh vi cu (bao vao kenh chung), va do van la mot he thong chay duoc.
        """
        nguoi = await self._nguoi_toi_luot(tru_id=tru_id)
        if nguoi is None:
            return None

        now = _now()
        # INSERT OR IGNORE + unique index tren handoff_id: job nhac chay chong
        # len nhau cung khong the giao mot khach cho hai nguoi.
        moi = await self._db.execute_rowcount(
            "INSERT OR IGNORE INTO phan_cong "
            "(handoff_id, tu_van_vien_id, chat_id, giao_luc, trang_thai) "
            "VALUES (?, ?, ?, ?, 'da_giao')",
            (handoff_id, nguoi.id, chat_id, now),
        )
        if not moi:
            return None

        # `luot_thu` lay so lon hon MOI so da cap — de sau nguoi nay trong hang.
        await self._db.execute(
            "UPDATE tu_van_vien SET "
            "  luot_thu = (SELECT COALESCE(MAX(luot_thu), 0) + 1 FROM tu_van_vien), "
            "  lan_cuoi_giao = ?, so_da_giao = so_da_giao + 1 "
            "WHERE id = ?",
            (now, nguoi.id),
        )
        log.info("giao_viec", tvv=nguoi.ho_ten, handoff=handoff_id, chat_id=chat_id[:8])
        return nguoi

    async def giao_lai(
        self, phan_cong_id: int, *, handoff_id: int, chat_id: str
    ) -> TuVanVien | None:
        """Nguoi cu khong phan hoi — danh dau leo thang roi giao cho nguoi khac."""
        cu = await self._db.fetch_val(
            "SELECT tu_van_vien_id FROM phan_cong WHERE id = ?", (phan_cong_id,)
        )
        # Index unique la TUNG PHAN, chi tren 'da_giao'. Doi trang thai o day
        # vua ghi lai lich su vua giai phong cho de giao lai — khong phai xoa gi.
        await self._db.execute(
            "UPDATE phan_cong SET trang_thai = 'leo_thang' WHERE id = ?", (phan_cong_id,)
        )
        return await self.giao_viec(
            handoff_id=handoff_id, chat_id=chat_id, tru_id=int(cu) if cu else None
        )

    # ---------- theo dau ----------
    async def dang_cho(self, *, cu_hon_phut: int = 0) -> list[ViecDaGiao]:
        """Viec da giao ma chua ai nhan, cu hon nguong. Kem tom tat cua handoff.

        MOI COT DEU PHAI CO BI DANH RO RANG. Ngay 08/08/2026 truy van nay viet
        `pc.chat_id, tv.*` — hai bang deu co cot `chat_id`, va `sqlite3.Row` tra
        ve cai DAU TIEN khop. Nghia la dia chi cua tu van vien am tham bien thanh
        dia chi cua KHACH, va tin nhac viec — kem ten khach, kem chat_id — suyt
        duoc gui thang cho chinh nguoi khach do.

        `la_kenh_noi_bo()` la thu chan lai. Nhung mot lop chan bat duoc loi khong
        co nghia la loi da duoc sua: no chi bien mot vu ro du lieu thanh mot dong
        log do. Hai lop deu can dung.
        """
        moc = datetime.fromtimestamp(
            datetime.now(tz=UTC).timestamp() - cu_hon_phut * 60, tz=UTC
        ).isoformat()
        rows = await self._db.fetch_all(
            "SELECT pc.id AS pc_id, pc.handoff_id AS pc_handoff_id, "
            "       pc.chat_id AS khach_chat_id, pc.giao_luc, pc.nhac_lan, "
            "       tv.id AS tv_id, tv.user_id AS tv_user_id, tv.chat_id AS tv_chat_id, "
            "       tv.ho_ten AS tv_ho_ten, tv.dang_nhan AS tv_dang_nhan, "
            "       tv.so_da_giao AS tv_so_da_giao, tv.lan_cuoi_giao AS tv_lan_cuoi_giao, "
            "       COALESCE(h.summary, '') AS tom_tat "
            "FROM phan_cong pc "
            "JOIN tu_van_vien tv ON tv.id = pc.tu_van_vien_id "
            "LEFT JOIN handoffs h ON h.id = pc.handoff_id "
            "WHERE pc.trang_thai = 'da_giao' AND pc.giao_luc <= ? "
            "ORDER BY pc.giao_luc",
            (moc,),
        )
        return [
            ViecDaGiao(
                phan_cong_id=int(r["pc_id"]),
                handoff_id=int(r["pc_handoff_id"]),
                chat_id=r["khach_chat_id"],
                giao_luc=r["giao_luc"],
                nhac_lan=int(r["nhac_lan"]),
                tvv=TuVanVien(
                    id=int(r["tv_id"]),
                    user_id=r["tv_user_id"],
                    chat_id=r["tv_chat_id"],
                    ho_ten=r["tv_ho_ten"],
                    dang_nhan=bool(r["tv_dang_nhan"]),
                    so_da_giao=int(r["tv_so_da_giao"]),
                    lan_cuoi_giao=r["tv_lan_cuoi_giao"],
                ),
                tom_tat=r["tom_tat"],
            )
            for r in rows
        ]

    async def chat_dang_giao(self) -> set[str]:
        """Cac chat da co nguoi cam viec. Job nhac chung phai BO QUA chung.

        Thieu buoc nay thi mot khach sinh ra hai tin: mot tin rieng cho nguoi
        duoc giao, mot tin nua vao kenh chung — dung cai canh "ai cung thay nen
        khong ai lam" ma ca tinh nang nay sinh ra de bo.
        """
        rows = await self._db.fetch_all(
            "SELECT DISTINCT chat_id FROM phan_cong WHERE trang_thai = 'da_giao'"
        )
        return {r["chat_id"] for r in rows}

    async def ghi_da_nhac(self, phan_cong_id: int) -> int:
        await self._db.execute(
            "UPDATE phan_cong SET nhac_lan = nhac_lan + 1 WHERE id = ?", (phan_cong_id,)
        )
        return int(
            await self._db.fetch_val(
                "SELECT nhac_lan FROM phan_cong WHERE id = ?", (phan_cong_id,), 0
            )
        )

    async def danh_dau_da_nhan(self, chat_id: str) -> int:
        """Goi khi co nguoi go /nhan. Khop theo chat_id vi do la thu /nhan biet."""
        return await self._db.execute_rowcount(
            "UPDATE phan_cong SET trang_thai = 'da_nhan', nhan_luc = ? "
            "WHERE chat_id = ? AND trang_thai = 'da_giao'",
            (_now(), chat_id),
        )


__all__ = ["TOI_DA_NHAC", "TuVanRepo", "TuVanVien", "ViecDaGiao"]
