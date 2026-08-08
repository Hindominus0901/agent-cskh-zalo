"""Chay mot bo cau hoi mau qua MODEL THAT, in cau tra loi ra de nguoi doc cham.

    uv run python scripts/thu_giong.py            # chay het
    uv run python scripts/thu_giong.py --vai student
    uv run python scripts/thu_giong.py --so 3     # chi cau so 3

VI SAO CAN SCRIPT NAY: sua giong la thu duy nhat trong ca du an khong co test
tu dong nao bat duoc. Khong co no thi moi lan sua `persona.md` deu la doan mo —
sua xong khong biet co tot len khong, va vai tuan sau khong ai dam dong vao nua.

KHONG GUI GI QUA ZALO, khong ghi vao CSDL that. Chi goi model va in ra man hinh.
Ton tien token that, nen bo cau hoi duoc giu ngan.

Cot "dau hieu van AI" doi chieu voi danh sach trong persona.md. No la mot phep
do THO — mot cau khong dinh dau hieu nao van co the nhat. Nguoi doc van la trong
tai, may chi loc bot phan de thay.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_cskh.config import Settings  # noqa: E402
from agent_cskh.harness.prompt import build_system  # noqa: E402
from agent_cskh.llm.base import Msg  # noqa: E402
from agent_cskh.llm.claude import ClaudeProvider  # noqa: E402
from agent_cskh.security import Principal  # noqa: E402
from agent_cskh.security.whitelist import _scope_for  # noqa: E402
from agent_cskh.wiki import WikiStore  # noqa: E402

# Nhung cum lam nguoi doc nhan ra ngay day la may viet. Khop khong dau, khong
# phan biet hoa thuong. Giu dong bo voi muc "Tuyet doi khong viet" o persona.md.
DAU_HIEU_AI = [
    "hy vong thong tin",
    "dung ngan ngai",
    "cau hoi rat hay",
    "mot ngay tot lanh",
    "rat vui duoc ho tro",
    "cam on anh/chi da quan tam",
    "nhin chung",
    "tom lai",
    "ve co ban",
    "giai phap toan dien",
    "toi uu hoa",
]

# Moi cau la mot tinh huong THAT da gap hoac se gap.
CAU_HOI: list[tuple[str, str, str]] = [
    ("stranger", "bên em làm dịch vụ gì vậy ạ", "Người lạ hỏi chung chung"),
    ("stranger", "khoá học bao nhiêu tiền ạ", "Hỏi giá — bot KHÔNG được báo giá"),
    ("stranger", "anh bận lắm, không có thời gian đâu", "Phản đối kinh điển"),
    ("student", "em định làm khoá dạy nấu ăn, dạy chụp ảnh, với cả coaching nữa ạ", "Ôm ba việc"),
    ("student", "em thấy mình chưa đủ giỏi để dạy ai cả", "Nản — cần hạ rào cản"),
    ("student", "ikigai là bốn vòng gì ấy chị nhỉ", "Hỏi nội dung CÓ trong kho"),
    ("student", "bên mình có dạy chạy quảng cáo TikTok không ạ", "Hỏi thứ NGOÀI kho"),
    ("student", "em còn bài nào chưa nộp không ạ", "Phải trả lời thẳng, không đẩy sang lệnh"),
]


def _dau_hieu(text: str) -> list[str]:
    from agent_cskh.wiki import strip_accents

    phang = strip_accents(text.lower())
    return [d for d in DAU_HIEU_AI if d in phang]


async def _hoi(provider, s: Settings, wiki: WikiStore, vai: str, cau: str) -> str:
    p = Principal(
        user_id="thu_giong",
        chat_id="thu_giong",
        role=vai,  # type: ignore[arg-type]
        display_name="Nguyễn Văn A",
        visibility_scope=_scope_for(vai),  # type: ignore[arg-type]
    )
    on_dinh, theo_nguoi = build_system(s, p, wiki=wiki)
    resp = await provider.complete(
        [Msg(role="user", text=cau)],
        system=on_dinh + ("\n\n" + theo_nguoi if theo_nguoi else ""),
        tools=None,
        max_tokens=600,
        timeout=60,
    )
    return resp.text.strip()


async def main() -> int:
    ap = argparse.ArgumentParser(description="Thử giọng bot qua model thật")
    ap.add_argument("--vai", choices=("stranger", "student"), help="chỉ chạy một vai")
    ap.add_argument("--so", type=int, help="chỉ chạy một câu (1-based)")
    a = ap.parse_args()

    s = Settings()
    if not s.anthropic_api_key.get_secret_value():
        print("Thiếu ANTHROPIC_API_KEY trong .env")
        return 1

    wiki = WikiStore(s)
    wiki.reload()
    provider = ClaudeProvider(s)

    chon = [c for c in CAU_HOI if not a.vai or c[0] == a.vai]
    if a.so:
        chon = chon[a.so - 1 : a.so]

    print("=" * 76)
    print("THỬ GIỌNG — đọc và tự chấm. Không có test tự động cho việc này.")
    print("=" * 76)
    # Script goi model voi tools=None de do RIENG phan giong, khong lan voi
    # chuyen goi cong cu. Hau qua: model doi khi viet ten cong cu ra thanh chu
    # ("doc_trang: ..."). Do la hien tuong CUA SCRIPT, khong phai cua bot that —
    # tren duong that no goi cong cu that va nguoi dung khong thay dong nao.
    print("Lưu ý: chạy với tools=None. Model viết tên công cụ ra chữ là hiện")
    print("tượng của script, không phải của bot thật. Dữ liệu học viên cũng rỗng.")

    co_dau_hieu = 0
    for i, (vai, cau, ghi_chu) in enumerate(chon, 1):
        print(f"\n[{i}/{len(chon)}] {ghi_chu}  ({vai})")
        print(f"  HỎI: {cau}")
        try:
            tra_loi = await _hoi(provider, s, wiki, vai, cau)
        except Exception as e:  # noqa: BLE001 - script tay, in loi roi chay tiep
            print(f"  LỖI: {e}")
            continue

        print("  ĐÁP:")
        for dong in tra_loi.splitlines():
            print(f"    {dong}")

        dh = _dau_hieu(tra_loi)
        so_cau = len([x for x in re.split(r"[.!?…]\s", tra_loi) if x.strip()])
        canh = []
        if dh:
            canh.append(f"dấu hiệu văn AI: {', '.join(dh)}")
            co_dau_hieu += 1
        if so_cau > 6:
            canh.append(f"dài {so_cau} câu (nên 2–5)")
        # Tim "?" trong HAI CAU CUOI, khong chi o ky tu cuoi cung. Mot cau ket
        # "...cho mình nhé?" hay "...được không ạ. Em chờ nhé" van la hoi nguoc;
        # kiem endswith("?") se bao dong nham gan het so lan.
        if "?" not in " ".join(tra_loi.rstrip().split()[-40:]):
            canh.append("không hỏi ngược ở cuối")
        print(f"  → {' · '.join(canh) if canh else 'ổn'}")

    print()
    print("=" * 76)
    print(f"{co_dau_hieu}/{len(chon)} câu dính dấu hiệu văn AI.")
    print("Máy chỉ lọc phần dễ thấy — người đọc vẫn là trọng tài.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
