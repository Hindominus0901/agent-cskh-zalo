"""Dung lai knowledge/index.md tu cac trang trong wiki/, va SOAT LOI.

Bot khong doc file index nay — no dung danh muc dung trong bo nho. File nay danh
cho NGUOI: mo ra de nhin toan canh kho tri thuc.

Phan dang gia hon la phan soat loi. Kho tri thuc hong khong bao gio bao loi: no
chi im lang khien bot tra loi "em chua nam chac" cho mot cau ma cau tra loi dang
nam ngay trong kho.

    uv run python scripts/wiki_index.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_cskh.config import get_settings  # noqa: E402
from agent_cskh.wiki import WikiStore, strip_accents  # noqa: E402
from agent_cskh.wiki.store import HU_TU, MUC_HIEN_THI  # noqa: E402

LINK = re.compile(r"\[\[([^\]]+)\]\]")
MOI_MUC = frozenset(MUC_HIEN_THI)
# Bot cat than bai o day khi tra loi. Dai hon = phan sau khong toi duoc khach.
MAX_THAN_BAI = 1400


def _soat_ten_file(goc: Path) -> list[str]:
    """Ten file la TEN TRANG. Co dau hay khoang trang thi lien ket se gay.

    Doc thang tu dia chu khong qua WikiStore: store da chuan hoa mat roi, va cai
    ta can biet chinh la ten GOC tren dia.
    """
    van_de: list[str] = []
    for muc in MUC_HIEN_THI:
        thu_muc = goc / muc
        if not thu_muc.is_dir():
            continue
        for path in sorted(thu_muc.rglob("*.md")):
            ten = path.stem
            if ten != strip_accents(ten):
                van_de.append(f"  [{ten}] ten file CO DAU — dat lai khong dau, noi bang gach ngang")
            elif " " in ten:
                van_de.append(f"  [{ten}] ten file co KHOANG TRANG — thay bang gach ngang")
            elif ten != ten.lower():
                van_de.append(f"  [{ten}] ten file co CHU HOA — dung chu thuong het")
    return van_de


def _soat_trung_slug(goc: Path) -> list[str]:
    """Hai file cung ten o hai muc khac nhau: mot trong hai KHONG BAO GIO duoc doc.

    `WikiStore.reload()` co log canh bao, nhung nguoi chay script nay khong nhin
    log. Ma day la loi im lang nguy hiem: dat mot trang `internal/gia-von.md` va
    mot trang `public/gia-von.md` thi ban tuong minh co ca hai.
    """
    thay: dict[str, list[str]] = {}
    for muc in MUC_HIEN_THI:
        thu_muc = goc / muc
        if not thu_muc.is_dir():
            continue
        for path in sorted(thu_muc.rglob("*.md")):
            thay.setdefault(path.stem, []).append(muc)
    return [
        f"  [{ten}] TRUNG TEN o {', '.join(cac_muc)} — chi ban o '{cac_muc[0]}' duoc doc, "
        f"ban con lai bi bo qua hoan toan"
        for ten, cac_muc in sorted(thay.items())
        if len(cac_muc) > 1
    ]


def _soat_frontmatter_hong(goc: Path) -> list[str]:
    """YAML hong thi store nuot loi va coi nhu khong co frontmatter.

    Hau qua: trang mat `summary` va `tu_khoa`, thanh gan nhu vo hinh — ma khong
    ai duoc bao gi.
    """
    import yaml

    van_de: list[str] = []
    for muc in MUC_HIEN_THI:
        thu_muc = goc / muc
        if not thu_muc.is_dir():
            continue
        for path in sorted(thu_muc.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            if not text.lstrip().startswith("---"):
                van_de.append(f"  [{path.stem}] KHONG CO frontmatter — thieu summary va tu_khoa")
                continue
            phan = text.lstrip().split("---", 2)
            if len(phan) < 3:
                van_de.append(f"  [{path.stem}] frontmatter khong dong (thieu dong '---' thu hai)")
                continue
            try:
                yaml.safe_load(phan[1])
            except yaml.YAMLError as e:
                dong_dau = str(e).split("\n", 1)[0]
                van_de.append(f"  [{path.stem}] frontmatter HONG: {dong_dau}")
    return van_de


def main() -> int:
    settings = get_settings()
    store = WikiStore(settings)
    n = store.reload()
    goc = settings.knowledge_dir / "wiki"

    # Cac phep soat doc thang tu dia — chay duoc ca khi kho rong.
    van_de: list[str] = []
    van_de += _soat_trung_slug(goc)
    van_de += _soat_ten_file(goc)
    van_de += _soat_frontmatter_hong(goc)

    all_pages = sorted(store.visible(MOI_MUC), key=lambda p: p.slug)
    if not all_pages:
        print("Kho tri thuc trong. Them file .md vao knowledge/wiki/public/.")
        print("Can mot trang mau de chep theo? Xem docs/vi-du-trang-wiki.md")
        for v in van_de:
            print(v)
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

    # ---------- soat noi dung tung trang ----------
    slugs = {p.slug for p in all_pages}
    for p in all_pages:
        if p.summary == p.title or not p.summary.strip():
            van_de.append(f"  [{p.slug}] thieu summary rieng — bot se kho tim ra trang nay")

        if not p.tu_khoa:
            van_de.append(
                f"  [{p.slug}] thieu `tu_khoa` — che do tra_cuu se truot trang nay "
                f"khi khach hoi bang tu khac"
            )
        else:
            # `tu_khoa` toan hu tu thi bi loc sach luc tim -> vo dung, nhung
            # truoc day script bao "co tu_khoa" la dat. Loi im lang.
            co_ich = [
                k
                for k in p.tu_khoa
                if any(t not in HU_TU and len(t) > 1 for t in strip_accents(k).split())
            ]
            if not co_ich:
                van_de.append(
                    f"  [{p.slug}] `tu_khoa` toan hu tu ({p.tu_khoa}) — bi loc sach khi tim, "
                    f"coi nhu khong khai gi"
                )

        if len(p.body) > MAX_THAN_BAI:
            van_de.append(
                f"  [{p.slug}] dai {len(p.body)} ky tu — bot cat o {MAX_THAN_BAI}, "
                f"phan sau khong toi duoc khach. Nen tach trang (xem docs/vi-du-trang-wiki.md)."
            )

        for target in LINK.findall(p.body):
            if target not in slugs:
                van_de.append(f"  [{p.slug}] lien ket gay toi [[{target}]]")

    dem = {v: sum(1 for p in all_pages if p.visibility == v) for v in MUC_HIEN_THI}
    print(
        f"Da ghi {out}  ({n} trang: "
        f"{dem['public']} cong khai, {dem['hocvien']} khach quen, {dem['internal']} noi bo)"
    )
    if van_de:
        print(f"\nCan xem lai ({len(van_de)}):")
        for v in van_de:
            print(v)
    else:
        print("Khong thay van de nao.")
    return 0


if __name__ == "__main__":
    # Console Windows mac dinh la cp1252 — in tieng Viet co dau se chet.
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass
    sys.exit(main())
