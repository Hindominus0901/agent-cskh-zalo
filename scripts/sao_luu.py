"""Sao luu CSDL va kho tri thuc.

    uv run python scripts/sao_luu.py            # sao luu ngay
    uv run python scripts/sao_luu.py --xem      # liet ke ban da co

CAI BAY DA MAC PHAI (08/08/2026): SQLite chay che do WAL, nen phan ghi gan nhat
nam trong `app.db-wal` CHU KHONG trong `app.db`. Chep moi `app.db` thi mat du
lieu moi — VA KHONG CO LOI NAO BAO. Luc thu migration tren ban sao, bang
khoa_hoc "khong ton tai" du no da duoc tao truoc do.

Script nay dung `sqlite3.backup()` — API chinh thuc, gop ca WAL, an toan ngay ca
khi bot dang chay va dang ghi.

Sao luu ca `knowledge/` vi tu 08/08/2026 nhan vien sua duoc no thang tu Zalo.
Git da theo doi thu muc do, nhung git chi nam tren cung o dia — o dia hong thi
mat ca hai.

Sao luu ca `data/media/` — anh bien lai khach gui. Zalo chi dua mot URL TAM va
URL do DA HET HAN, nen file trong thu muc nay la ban duy nhat con lai tren doi.
Mat no la mat bang chung thanh toan, khong tai lai duoc tu bat cu dau.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_cskh.config import get_settings  # noqa: E402

GIU_LAI = 14  # so ban sao luu giu lai


def _thu_muc(settings) -> Path:
    d = settings.data_dir / "sao-luu"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sao_luu() -> int:
    settings = get_settings()
    dich = _thu_muc(settings)
    dau = datetime.now().strftime("%Y%m%d-%H%M")

    # --- CSDL ---
    nguon = settings.db_path
    if not nguon.exists():
        print(f"Khong thay CSDL o {nguon}")
        return 1

    db_dich = dich / f"app-{dau}.db"
    # Khong dung shutil.copy: bo qua WAL. backup() gop het, va chay duoc ngay ca
    # khi bot dang ghi.
    src = sqlite3.connect(f"file:{nguon}?mode=ro", uri=True)
    dst = sqlite3.connect(db_dich)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    kt = db_dich.stat().st_size
    print(f"CSDL      -> {db_dich.name}  ({kt / 1024:.0f} KB)")

    # --- Kho tri thuc ---
    kho = settings.knowledge_dir
    if kho.exists():
        kho_dich = dich / f"knowledge-{dau}"
        shutil.copytree(
            kho, kho_dich, ignore=shutil.ignore_patterns("*.md.bak", "raw", "__pycache__")
        )
        so_trang = len(list(kho_dich.rglob("*.md")))
        print(f"Kho       -> {kho_dich.name}  ({so_trang} trang)")

    # --- Anh bien lai ---
    # Khong the tai lai tu Zalo: URL goc da het han. Day la ban duy nhat.
    media = settings.media_dir
    if media.exists() and any(media.iterdir()):
        media_dich = dich / f"media-{dau}"
        shutil.copytree(media, media_dich, ignore=shutil.ignore_patterns("__pycache__"))
        so_anh = sum(1 for p in media_dich.rglob("*") if p.is_file())
        kt_mb = sum(p.stat().st_size for p in media_dich.rglob("*") if p.is_file()) / 1024 / 1024
        print(f"Ảnh       -> {media_dich.name}  ({so_anh} ảnh, {kt_mb:.1f} MB)")

    # --- Don ban cu ---
    da_xoa = _don_ban_cu(dich)
    if da_xoa:
        print(f"Da don    {da_xoa} bản cũ (giữ {GIU_LAI} bản gần nhất)")

    print(f"\nXong. Thư mục: {dich}")
    print("Chép thư mục này ra ổ khác hoặc lên đám mây — cùng một ổ đĩa thì hỏng cùng nhau.")
    return 0


def _don_ban_cu(dich: Path) -> int:
    n = 0
    for mau in ("app-*.db", "knowledge-*", "media-*"):
        ds = sorted(dich.glob(mau), key=lambda p: p.name, reverse=True)
        for cu in ds[GIU_LAI:]:
            if cu.is_dir():
                shutil.rmtree(cu, ignore_errors=True)
            else:
                cu.unlink(missing_ok=True)
            n += 1
    return n


def xem() -> int:
    dich = _thu_muc(get_settings())
    ds = sorted(dich.glob("app-*.db"), reverse=True)
    if not ds:
        print("Chưa có bản sao lưu nào.")
        return 0
    print(f"{len(ds)} bản sao lưu trong {dich}:\n")
    for p in ds:
        kb = p.stat().st_size / 1024
        print(f"  {p.name:<28} {kb:>8.0f} KB")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xem", action="store_true", help="liet ke ban da co")
    sys.exit(xem() if ap.parse_args().xem else sao_luu())
