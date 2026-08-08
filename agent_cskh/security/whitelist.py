"""Phan quyen. Ep o TANG THUC THI, khong phai bang prompt.

Bon vai, xep theo thu bac:
  stranger — khach la. Chi doc kho `public`, khong co tool ghi.
  student  — hoc vien da ghep bang ma moi. Them kho `hocvien`.
  staff    — nhan vien trong whitelist, hoac dang o trong nhom tin cay.
  owner    — chu bot (OWNER_USER_IDS trong .env).

Nguyen tac: mac dinh phai la an toan. Ai khong ro rang la stranger.

VI SAO `student` NAM TRONG THU BAC chu khong phai mot bang rieng: moi cua da
duoc ep san deu loc bang `role_at_least` — ToolRegistry.specs(), COMMANDS,
Principal.can_write, la_kenh_noi_bo(). Nam trong thu bac thi hoc vien tu dong
thua huong dung nhung gi nguoi la co, va tu dong KHONG BAO GIO thanh dich nhan
canh bao noi bo. Mien phi, khong phai viet them dong nao.

Neu tach bang rieng thi moi quyet dinh phai tra them mot luot, va cho nao quen
tra la cho do ro.

NHUNG `visibility` KHONG phai thu bac — no la TAP HOP. Hoc vien thay tai lieu
khoa hoc nhung khong thay tai lieu noi bo, con nhan vien thay ca hai. Vi vay
`_scope_for` liet ke tuong minh cho tung vai chu khong cong don theo rank.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from agent_cskh.config import Settings
from agent_cskh.logging_setup import get_logger
from agent_cskh.store import Database
from agent_cskh.transport.base import InboundEvent

log = get_logger(__name__)

Role = Literal["stranger", "student", "staff", "owner"]

_RANK: dict[Role, int] = {"stranger": 0, "student": 1, "staff": 2, "owner": 3}


def role_at_least(role: Role, minimum: Role) -> bool:
    """So sanh thu bac vai. Dung o tang cong cu, noi chi co ten vai chu khong co Principal."""
    return _RANK.get(role, 0) >= _RANK.get(minimum, 0)


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    chat_id: str
    role: Role
    display_name: str | None = None
    # Nhan hien thi duoc phep truy hoi. Dung thang trong menh de filter LanceDB.
    visibility_scope: frozenset[str] = field(default_factory=lambda: frozenset({"public"}))

    @property
    def is_stranger(self) -> bool:
        return self.role == "stranger"

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"

    def at_least(self, role: Role) -> bool:
        return _RANK[self.role] >= _RANK[role]

    @property
    def can_write(self) -> bool:
        """Tool ghi (Notion, Sheets, lich...) chi danh cho noi bo."""
        return self.at_least("staff")

    def visibility_sql(self) -> str:
        """Menh de filter cho LanceDB. Loc TRONG truy van, khong loc sau."""
        vals = ", ".join(f"'{v}'" for v in sorted(self.visibility_scope))
        return f"visibility IN ({vals})"


def _scope_for(role: Role) -> frozenset[str]:
    """Nhan hien thi duoc phep doc. Liet ke tuong minh, KHONG cong don theo rank.

    Hoc vien co thu bac cao hon nguoi la nhung van khong duoc thay `internal` —
    do la ly do khong the viet ham nay bang mot phep so sanh rank.
    """
    if role == "stranger":
        return frozenset({"public"})
    if role == "student":
        return frozenset({"public", "hocvien"})
    return frozenset({"public", "hocvien", "internal"})


class PrincipalResolver:
    """Tra vai tro tu .env + bang principals + bang trusted_chats."""

    def __init__(self, settings: Settings, db: Database) -> None:
        self._s = settings
        self._db = db
        self._owners = {u.strip() for u in settings.owner_user_ids if u.strip()}

    async def resolve(self, event: InboundEvent) -> Principal:
        role: Role = "stranger"

        if event.user_id in self._owners:
            role = "owner"
        else:
            row = await self._db.fetch_one(
                "SELECT role FROM principals WHERE user_id = ?", (event.user_id,)
            )
            if row and row["role"] in _RANK:
                role = row["role"]  # type: ignore[assignment]

            # Nhom tin cay nang quyen cho moi nguoi trong do — chi dat nhung
            # nhom thuc su noi bo vao bang nay.
            if role == "stranger" and event.chat_type == "group":
                grp = await self._db.fetch_one(
                    "SELECT role FROM trusted_chats WHERE chat_id = ?", (event.chat_id,)
                )
                if grp and grp["role"] in _RANK:
                    role = grp["role"]  # type: ignore[assignment]

        return Principal(
            user_id=event.user_id,
            chat_id=event.chat_id,
            role=role,
            display_name=event.display_name,
            visibility_scope=_scope_for(role),
        )

    async def la_kenh_noi_bo(self, chat_id: str) -> bool:
        """Chat nay co du tin cay de nhan noi dung NOI BO khong?

        Dung truoc moi lan gui canh bao. Noi dung noi bo khong chi la loi ky
        thuat — nhac handoff con kem tom tat khach hoi gi va chat_id cua ho.
        Dat sai mot ky tu trong ALERT_CHAT_ID la thong tin khach A roi vao cuoc
        tro chuyen voi khach B.

        Zalo tra 410 cho chat_id khong ton tai, nen go nham thuong hong an toan.
        Nguy hiem la chat_id GO NHAM MA CO THAT — luc do bot gui that su.

        Mac dinh phai la tu choi: khong chac chan thi coi nhu khong phai noi bo.
        """
        chat_id = (chat_id or "").strip()
        if not chat_id:
            return False

        # Chat rieng: Zalo dung luon user_id lam chat_id (da kiem chung 07/08/2026).
        if chat_id in self._owners:
            return True

        row = await self._db.fetch_one("SELECT role FROM principals WHERE user_id = ?", (chat_id,))
        if row and role_at_least(row["role"], "staff"):
            return True

        grp = await self._db.fetch_one(
            "SELECT role FROM trusted_chats WHERE chat_id = ?", (chat_id,)
        )
        return bool(grp and role_at_least(grp["role"], "staff"))

    async def alert_chat_id(self) -> str | None:
        """Noi gui canh bao. Bang trusted_chats truoc, roi moi den .env.

        Vi sao uu tien CSDL hon .env: kenh canh bao phai dat duoc TU TRONG CHAT,
        bang lenh /datkenhcanhbao chay ngay trong nhom se nhan. Bat nguoi ta mo
        file .env de doi mot chat_id la cach chac chan de ho khong doi, va roi
        canh bao cu the o cho cu — thuong la chat rieng cua chu bot, noi ma no
        chen ngang giua cuoc tro chuyen that.

        Ngay 08/08/2026: tin "CAN NGUOI TIEP QUAN" kem ten khach va chat_id hien
        ngay giua doan chat cua chu bot voi bot. O chat rieng thi chi kho chiu;
        trong mot nhom hoc vien thi la ro ri that.
        """
        row = await self._db.fetch_one(
            "SELECT chat_id FROM trusted_chats WHERE is_alert_target = 1 LIMIT 1"
        )
        if row:
            return str(row["chat_id"])
        return self._s.alert_chat_id or None

    async def dat_kenh_canh_bao(self, chat_id: str, label: str = "") -> None:
        """Dat chat nay lam noi nhan canh bao, go bo danh dau o cac chat khac.

        Chi MOT kenh canh bao tai mot thoi diem. Hai kenh nghia la mot nua canh
        bao di mot noi — kieu hong ma khong ai phat hien cho den luc can nhat.
        """
        gio = datetime.now(tz=UTC).isoformat()
        await self._db.execute("UPDATE trusted_chats SET is_alert_target = 0")
        await self._db.execute(
            "INSERT INTO trusted_chats (chat_id, label, role, is_alert_target, created_at) "
            "VALUES (?, ?, 'staff', 1, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET is_alert_target = 1, label = excluded.label",
            (chat_id, label or "kenh canh bao", gio),
        )
