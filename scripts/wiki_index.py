"""Dung lai knowledge/index.md tu cac trang trong wiki/.

Bot khong doc file nay — no dung danh muc dung trong bo nho. File nay danh cho
NGUOI: mo trong Obsidian de nhin toan canh kho tri thuc, va de soat xem trang nao
thieu summary hay lien ket gay.

    uv run python scripts/wiki_index.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_cskh.config import get_settings  # noqa: E402
from agent_cskh.wiki import WikiStore  # noqa: E402

LINK = re.compile(r"\[\[([^\]]+)\]\]")


def main() -> int:
    settings = get_settings()
    store = WikiStore(settings)
    n = store.reload()

    # PHAI liet ke ca ba muc. Bo sot `hocvien` thi nhung trang do vo hinh voi
    # nguoi doc index — con bot van doc duoc chung, nen khong ai phat hien ra.
    all_pages = sorted(
        store.visible(frozenset({"public", "hocvien", "internal"})), key=lambda p: p.slug
    )
    if not all_pages:
        print("Kho tri thuc trong. Them file .md vao knowledge/wiki/public/.")
        return 0

    lines = [
        "# Danh mục kho tri thức",
        "",
        "*File này do `scripts/wiki_index.py` sinh ra. Đừng sửa tay — sửa trang wiki rồi chạy lại.*",
        "",
    ]
    for vis, tieu_de in (
        ("public", "Công khai — khách đọc được"),
        ("hocvien", "Khách quen — cần được nhận diện mới đọc được"),
        ("internal", "Nội bộ — chỉ nhân viên và chủ"),
    ):
        group = [p for p in all_pages if p.visibility == vis]
        if not group:
            continue
        lines += [f"## {tieu_de}", ""]
        for p in group:
            lines.append(f"- [[{p.slug}]] — {p.summary}")
        lines.append("")

    out = settings.knowledge_dir / "index.md"
    out.write_text("\n".join(lines), encoding="utf-8")

    # Soat loi thuong gap
    slugs = {p.slug for p in all_pages}
    van_de: list[str] = []
    for p in all_pages:
        if p.summary == p.title or not p.summary.strip():
            van_de.append(f"  [{p.slug}] thieu summary rieng — bot se kho tim ra trang nay")
        if not p.tu_khoa:
            # O che do `tra_cuu` day khong phai loi nho: tim kiem la regex, nen
            # trang khong co `tu_khoa` chi tim ra duoc khi khach go trung chu
            # trong tieu de. Khach that hiem khi go trung.
            van_de.append(
                f"  [{p.slug}] thieu `tu_khoa` — che do tra_cuu se truot trang nay "
                f"khi khach hoi bang tu khac"
            )
        if len(p.body) > 1400:
            van_de.append(
                f"  [{p.slug}] dai {len(p.body)} ky tu — bot cat o 1400, "
                f"phan sau khong toi duoc khach. Nen tach trang."
            )
        for target in LINK.findall(p.body):
            if target not in slugs:
                van_de.append(f"  [{p.slug}] lien ket gay toi [[{target}]]")

    dem = {v: sum(1 for p in all_pages if p.visibility == v) for v in ("public", "hocvien", "internal")}
    print(
        f"Da ghi {out}  ({n} trang: "
        f"{dem['public']} cong khai, {dem['hocvien']} khach quen, {dem['internal']} noi bo)"
    )
    if van_de:
        print(f"\nCan xem lai ({len(van_de)}):")
        for v in van_de:
            print(v)
    return 0


if __name__ == "__main__":
    sys.exit(main())
