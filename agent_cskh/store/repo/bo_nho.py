"""Tri nho lau dai: tim lai tin nhan cu (FTS5) va bo nho do agent tu soan.

Hai thu tach biet, chung mot muc dich — cho bot biet nhung gi da xay ra ngoai
12 tin gan nhat:

  tim()       — tra nguyen van tin nhan cu. Khong ton token LLM nao de tao ra,
                khong mat mat thong tin, va luon dung vi no la loi noi that.
  ghi()/...   — nhung y da duoc chat loc, nap san vao prompt moi luot.

Gioi han duoc EP O DAY chu khong nhac trong prompt: mot bo nho khong tran duoc
la mot bo nho khong lam phinh hoa don token thang sau.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from agent_cskh.logging_setup import get_logger
from agent_cskh.store import Database

log = get_logger(__name__)

# Moi nguoi toi da bao nhieu ghi nho. Cham tran thi don cai cu nhat.
#
# 20 x 200 ky tu ~ 1.000 token o truong hop toi da. Do la phan KHONG duoc cache
# (no doi theo tung nguoi), nen no la chi phi that moi luot — phai co tran.
TOI_DA_MOI_NGUOI = 20
TOI_DA_KY_TU = 200
TOI_DA_KHOA = 40

MAX_KET_QUA = 5

# FTS5 coi ", *, -, NEAR, AND... la cu phap. Tin nhan nguoi dung day nhung ky tu
# do, va mot dau ngoac kep le lam ca cau truy van nem loi. Bam lay tu, bo phan
# con lai — nguoi dung khong bao gio duoc viet truc tiep vao ngon ngu truy van.
_TU = re.compile(r"\w+", re.UNICODE)


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


@dataclass(frozen=True, slots=True)
class TinCu:
    huong: str  # 'in' = nguoi do noi, 'out' = bot noi
    van_ban: str
    luc: str


@dataclass(frozen=True, slots=True)
class MotNho:
    khoa: str
    gia_tri: str
    nguon_role: str
    updated_at: str

    @property
    def do_doi_ngu_ghi(self) -> bool:
        return self.nguon_role in ("staff", "owner")


def lam_sach_truy_van(truy_van: str) -> str:
    """Doi van ban tu do thanh mot bieu thuc FTS5 an toan. Rong = khong tim duoc."""
    tu = _TU.findall(truy_van)[:8]
    return " OR ".join(f'"{t}"' for t in tu)


class BoNhoRepo:
    def __init__(self, db: Database) -> None:
        self._db = db

    # ---------- tim tin nhan cu ----------
    async def tim(
        self,
        chat_id: str,
        truy_van: str,
        *,
        limit: int = MAX_KET_QUA,
        bo_qua_gan_nhat: int = 0,
    ) -> list[TinCu]:
        """Tim toan van trong lich su cua DUNG cuoc tro chuyen nay.

        `chat_id` la tham so bat buoc va khong co duong nao bo qua no — day la
        rang buoc quan trong nhat cua ham. Mot bo tim kiem tren toan bang
        `messages` se tra ve doan chat cua khach khac cho bat ky ai biet hoi
        dung tu khoa.

        `bo_qua_gan_nhat` bo N tin moi nhat ra khoi ket qua: chung da nam san
        trong cua so hoi thoai ma model dang nhin thay, tra lai chi la nhieu —
        va tin vua den se luon tu khop voi chinh no.
        """
        bieu_thuc = lam_sach_truy_van(truy_van)
        if not bieu_thuc:
            return []

        rows = await self._db.fetch_all(
            "SELECT m.direction, m.text, m.created_at "
            "FROM messages_fts "
            "JOIN messages m ON m.id = messages_fts.rowid "
            "WHERE messages_fts MATCH ? "
            "  AND m.chat_id = ? "
            "  AND m.id NOT IN ("
            "        SELECT id FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?) "
            "ORDER BY bm25(messages_fts) "
            "LIMIT ?",
            (bieu_thuc, chat_id, chat_id, bo_qua_gan_nhat, limit),
        )
        return [TinCu(huong=r["direction"], van_ban=r["text"], luc=r["created_at"]) for r in rows]

    # ---------- bo nho ----------
    async def ghi(
        self,
        *,
        user_id: str,
        khoa: str,
        gia_tri: str,
        nguon_role: str,
        nguon_chat_id: str,
    ) -> str:
        """Ghi mot y. Tra ve 'moi' | 'cap_nhat' | 'rong'.

        Ghi de theo `khoa` chu khong chong them: bot doi y ("nganh: my pham" ->
        "nganh: my pham handmade") thi ta muon mot dong dung, khong phai hai
        dong mau thuan de model tu chon.
        """
        khoa = _chuan_hoa_khoa(khoa)
        gia_tri = " ".join((gia_tri or "").split())[:TOI_DA_KY_TU]
        if not khoa or not gia_tri:
            return "rong"

        now = _now()
        da_co = await self._db.fetch_val(
            "SELECT 1 FROM bo_nho WHERE user_id = ? AND khoa = ?", (user_id, khoa)
        )
        await self._db.execute(
            "INSERT INTO bo_nho "
            "(user_id, khoa, gia_tri, nguon_role, nguon_chat_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, khoa) DO UPDATE SET "
            "  gia_tri = excluded.gia_tri, "
            "  nguon_role = excluded.nguon_role, "
            "  nguon_chat_id = excluded.nguon_chat_id, "
            "  updated_at = excluded.updated_at",
            (user_id, khoa, gia_tri, nguon_role, nguon_chat_id, now, now),
        )
        await self._cat_bot(user_id)
        log.info("ghi_nho", user_id=user_id[:8], khoa=khoa, moi=not da_co)
        return "cap_nhat" if da_co else "moi"

    async def _cat_bot(self, user_id: str) -> int:
        """Giu toi da TOI_DA_MOI_NGUOI dong, bo cai lau nhat khong duoc dong toi.

        Quen dan la hanh vi dung. Cai thay the — tu choi ghi khi day — se lam bot
        ket lai o hieu biet cua tuan dau tien va khong bao gio cap nhat duoc nua.
        """
        return await self._db.execute_rowcount(
            "DELETE FROM bo_nho WHERE user_id = ? AND id NOT IN ("
            "  SELECT id FROM bo_nho WHERE user_id = ? ORDER BY updated_at DESC, id DESC LIMIT ?)",
            (user_id, user_id, TOI_DA_MOI_NGUOI),
        )

    async def danh_sach(self, user_id: str) -> list[MotNho]:
        rows = await self._db.fetch_all(
            "SELECT khoa, gia_tri, nguon_role, updated_at FROM bo_nho "
            "WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
            (user_id,),
        )
        return [
            MotNho(
                khoa=r["khoa"],
                gia_tri=r["gia_tri"],
                nguon_role=r["nguon_role"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def xoa(self, user_id: str, khoa: str) -> int:
        return await self._db.execute_rowcount(
            "DELETE FROM bo_nho WHERE user_id = ? AND khoa = ?", (user_id, _chuan_hoa_khoa(khoa))
        )

    async def xoa_het(self, user_id: str) -> int:
        return await self._db.execute_rowcount("DELETE FROM bo_nho WHERE user_id = ?", (user_id,))


def _chuan_hoa_khoa(khoa: str) -> str:
    """Khoa la dinh danh, khong phai cau van. Gon lai de UNIQUE lam dung viec."""
    return "_".join((khoa or "").lower().split())[:TOI_DA_KHOA]


__all__ = [
    "MAX_KET_QUA",
    "TOI_DA_KY_TU",
    "TOI_DA_MOI_NGUOI",
    "BoNhoRepo",
    "MotNho",
    "TinCu",
    "lam_sach_truy_van",
]
