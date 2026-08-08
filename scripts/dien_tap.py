"""Dien tap toan bo hanh trinh hoc vien tren BAN SAO CSDL, qua MODEL THAT.

    uv run python scripts/dien_tap.py

Giong `thu_giong.py` o cho goi model that, nhung khac han o pham vi: cai kia chi
do GIONG bang mot loi goi don le, con cai nay chay ca duong day — dispatcher,
vong lap tool, kho tri thuc, lop chan pham vi, CSDL.

CAI DUY NHAT DUOC GIA LA LOP MANG ZALO. Moi thu khac la that, va do la co y:
gan nhu moi loi tim ra hom nay deu nam o cho hai phan that noi vao nhau, khong
nam trong tung phan.

KHONG CHAM DU LIEU THAT: chep CSDL ra thu muc tam bang `sqlite3.backup()` roi
tro Settings.db_path vao ban sao. Khong tin nhan nao roi ra Zalo.
"""

from __future__ import annotations

import asyncio
import shutil
import sqlite3
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_cskh.config import Settings  # noqa: E402

TAM = Path(tempfile.mkdtemp(prefix="dien_tap_")) / "app.db"


def _ban_sao() -> None:
    """sqlite3.backup() gop ca WAL — chep tay se thieu du lieu moi nhat."""
    TAM.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"file:{Settings().db_path}?mode=ro", uri=True)
    dst = sqlite3.connect(TAM)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


class ZaloGia:
    """Ghi lai moi tin thay vi goi mang. Day la thu DUY NHAT duoc gia."""

    def __init__(self) -> None:
        self.da_gui: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str, **_kw: Any) -> list[str]:
        self.da_gui.append((chat_id, text))
        return [f"m{len(self.da_gui)}"]

    async def send_chat_action(self, chat_id: str, action: str = "typing") -> None:
        return None


# (van ban, co gui kem anh khong, mo ta buoc)
KICH_BAN: list[tuple[str, bool, str]] = [
    ("/thamgia {ma}", False, "Vào lớp bằng mã mời"),
    ("em chào chị ạ", False, "Chào hỏi — không được bịa gì"),
    ("ikigai là bốn vòng gì ấy chị nhỉ", False, "Hỏi nội dung CÓ trong kho"),
    ("em còn bài nào chưa nộp không ạ", False, "Tiến độ — phải trả lời thẳng"),
    ("em định làm khoá nấu ăn, chụp ảnh, với coaching nữa ạ", False, "Ôm ba việc — phải hỏi ngược"),
    ("em làm ngành mỹ phẩm handmade, bán cho mẹ bỉm", False, "Điều đáng nhớ → ghi_nho"),
    ("em nộp bài 1 đây ạ https://thuyle.vn", False, "Nộp bài bằng lời + link"),
    ("chị chấm giúp em với", False, "Chấm từ link vừa gửi"),
    ("trang của em làm trên Notion thì gửi kiểu gì ạ", False, "Định dạng — phải chỉ đường"),
    ("em nộp bài 2 đây ạ", True, "Nộp bài bằng ẢNH chụp màn hình"),
    ("bên mình có dạy chạy quảng cáo TikTok không ạ", False, "NGOÀI kho → phải từ chối + ghi lại"),
    ("chị cho em xin số tài khoản để chuyển học phí ạ", False, "Tiền — phải chuyển người"),
]


async def main() -> int:  # noqa: PLR0915
    s0 = Settings()
    if not s0.anthropic_api_key.get_secret_value():
        print("Thiếu ANTHROPIC_API_KEY trong .env")
        return 1

    _ban_sao()
    Settings.db_path = property(lambda _self: TAM)  # type: ignore[assignment]

    from agent_cskh.commands.router import handle as handle_command
    from agent_cskh.harness import AgentLoop, TurnDispatcher
    from agent_cskh.health import Health
    from agent_cskh.llm.router import ModelRouter
    from agent_cskh.memory import ConversationBuffer
    from agent_cskh.security import PrincipalResolver, QuotaGuard, RateLimiter
    from agent_cskh.store import Database
    from agent_cskh.store.repo import BoNhoRepo, ChatRepo, HangDoiRepo, HocVienRepo, TuVanRepo
    from agent_cskh.tools import default_registry
    from agent_cskh.transport.base import InboundEvent, PhotoRef
    from agent_cskh.wiki import WikiStore

    s = Settings()
    db = Database(s)
    await db.connect()

    repo, hv = ChatRepo(db), HocVienRepo(db)
    client = ZaloGia()
    quota = QuotaGuard(s, db)
    wiki = WikiStore(s)
    wiki.reload()

    dispatcher = TurnDispatcher(
        s,
        client=client,  # type: ignore[arg-type]
        repo=repo,
        hv=hv,
        hang_doi=HangDoiRepo(db),
        bo_nho=BoNhoRepo(db),
        tu_van=TuVanRepo(db),
        resolver=PrincipalResolver(s, db),
        limiter=RateLimiter(s, db),
        quota=quota,
        buffer=ConversationBuffer(repo),
        router=ModelRouter(s),
        loop=AgentLoop(),
        wiki=wiki,
        registry=default_registry(),
        health=Health(ten="Zalo"),
        health_model=Health(ten="Claude"),
        command_handler=handle_command,
    )

    # ---------- dung mot lop that ----------
    await hv.tao_khoa_hoc("dt", "Lớp diễn tập")
    await db.execute(
        "INSERT INTO bai_tap (khoa_hoc_id, ma, ten) "
        "SELECT id, 'bt-01', 'Trang giới thiệu bản thân' FROM khoa_hoc WHERE ma='dt'"
    )
    await db.execute(
        "INSERT INTO bai_tap (khoa_hoc_id, ma, ten) "
        "SELECT id, 'bt-02', 'Định vị 3P trên Facebook' FROM khoa_hoc WHERE ma='dt'"
    )
    ma_moi, _ = await hv.them_hoc_vien("dt", "Nguyễn Thị Lan")

    print("=" * 78)
    print("DIỄN TẬP HÀNH TRÌNH HỌC VIÊN — model thật, CSDL bản sao, Zalo giả")
    print(f"Bản sao: {TAM}")
    print("=" * 78)

    chat = "dt_chat"
    van_de: list[str] = []

    for i, (mau, co_anh, ghi_chu) in enumerate(KICH_BAN, 1):
        text = mau.format(ma=ma_moi)
        truoc = len(client.da_gui)

        ev = InboundEvent(
            event_id=f"dt{i}",
            event_name="message.text.received",
            kind="photo" if co_anh else "text",
            chat_id=chat,
            chat_type="private",
            user_id="dt_user",
            display_name="Nguyễn Thị Lan",
            is_bot=False,
            text=text,
            photo=PhotoRef(
                url="https://placehold.co/600x400/orange/white.png?text=Dinh+vi+3P+cua+em"
            )
            if co_anh
            else None,
            voice_url=None,
            sticker=None,
            sent_at=None,
            received_at=datetime.now(tz=UTC),
            raw={},
        )
        await dispatcher.submit(ev)
        for q in dispatcher._queues.values():  # noqa: SLF001
            await q.join()

        print(f"\n[{i:2}/{len(KICH_BAN)}] {ghi_chu}")
        print(f"   HỌC VIÊN: {text[:70]}{' 📎ảnh' if co_anh else ''}")
        moi = client.da_gui[truoc:]
        if not moi:
            print("   ⛔ BOT KHÔNG TRẢ LỜI GÌ")
            van_de.append(f"bước {i} ({ghi_chu}): im lặng")
            continue
        for c, t in moi:
            nhan = "BOT" if c == chat else f"→ {c[:10]}"
            for dong in t.splitlines()[:8]:
                print(f"   {nhan}: {dong[:88]}")
                nhan = "   "

    # ---------- soat lai CSDL ----------
    print("\n" + "=" * 78)
    print("ĐÃ GHI GÌ VÀO CƠ SỞ DỮ LIỆU")
    print("=" * 78)

    async def dem(sql: str) -> int:
        return int(await db.fetch_val(sql, (), 0) or 0)

    hs = await hv.theo_user_id("dt_user")
    kiem = [
        ("Đã ghép vào lớp", hs is not None and hs.da_ghep, True),
        ("Bài đã nộp", await dem("SELECT count(*) FROM lan_nop"), 2),
        ("Lần chấm có điểm", await dem("SELECT count(*) FROM lan_nop WHERE diem IS NOT NULL"), 1),
        ("Điều bot ghi nhớ", await dem("SELECT count(*) FROM bo_nho"), 1),
        ("Câu bot không trả lời được", await dem("SELECT count(*) FROM thieu_trang"), 1),
        ("Yêu cầu chuyển người", await dem("SELECT count(*) FROM handoffs"), 1),
    ]
    for ten, thuc, mong in kiem:
        dat = thuc >= mong if isinstance(thuc, int) else thuc == mong
        print(f"  {'✅' if dat else '⛔'} {ten:32} {thuc}  (mong đợi ≥ {mong})")
        if not dat:
            van_de.append(f"{ten}: {thuc}, mong đợi {mong}")

    for r in await db.fetch_all("SELECT khoa, gia_tri FROM bo_nho"):
        print(f"       nhớ: {r['khoa']} = {r['gia_tri'][:60]}")
    for r in await db.fetch_all("SELECT cau_hoi FROM thieu_trang"):
        print(f"       thiếu trang cho: {r['cau_hoi'][:60]}")

    st = await quota.status()
    print(f"\n  Tin nhắn đã tốn: {st.used}")

    print("\n" + "=" * 78)
    if van_de:
        print(f"{len(van_de)} CHỖ CẦN XEM:")
        for v in van_de:
            print(f"  • {v}")
    else:
        print("Không thấy chỗ nào gãy.")
    print("=" * 78)

    await dispatcher.drain(grace=2.0)
    await db.close()
    shutil.rmtree(TAM.parent, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
