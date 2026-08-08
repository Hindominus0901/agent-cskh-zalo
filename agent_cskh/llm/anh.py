"""Tai anh ve roi gui thang byte cho model, thay vi dua URL de model tu tai.

TAI SAO PHAI TU TAI — kiem chung 08/08/2026:

    URL cua httpbin      -> HTTP 400 "Unable to download the file"
    URL cua Wikipedia    -> HTTP 400 "Unable to download the file"
    URL cua placehold.co -> HTTP 400 "disallowed by the website's robots.txt"
    Cung tam anh, gui base64 -> HTTP 200, model mo ta dung

Cau bao loi cua placehold.co noi ro nguyen nhan: bo tai cua Anthropic TON TRONG
robots.txt. CDN cua Zalo gan nhu chac chan chan crawler, va URL anh cua ho co
chu ky het han. Nghia la duong `source.type = "url"` KHONG BAO GIO chay duoc voi
anh Zalo — khong phai thinh thoang hong, ma la khong bao gio chay.

Truoc ban va nay, moi tinh nang doc anh cua bot deu hong ma khong ai biet: doc
bien lai chuyen khoan, xem anh san pham, va cham bai tu anh chup man hinh. Bot
tra ve cau du phong "he thong dang truc trac", va do la tat ca dau vet.

`tools/vision.py` da tai anh ve dia tu truoc — de nguoi doi soat con xem duoc
sau khi URL het han. Tuc la bot van luon TAI DUOC anh; chi la chua bao gio dua
so byte do cho model.

BO NHO DEM: cua so hoi thoai 12 tin duoc dung lai o MOI luot, nen mot tam anh se
bi tai lai moi lan neu khong nho. Khoa theo URL, gioi han so muc — anh Zalo co
chu ky nen URL khac nhau la anh khac nhau.
"""

from __future__ import annotations

import base64
from collections import OrderedDict

import httpx

from agent_cskh.logging_setup import get_logger

log = get_logger(__name__)

# Tran cua Anthropic cho mot anh. Vuot thi API tu choi ca yeu cau.
TOI_DA_BYTE = 5_000_000
TOI_DA_GIAY = 20.0
# Giu bao nhieu anh trong bo nho dem. Cua so hoi thoai la 12 tin nen 16 la du,
# va 16 anh x 5MB = 80MB o truong hop toi te nhat — chap nhan duoc.
TOI_DA_DEM = 16

# Bon dinh dang Anthropic nhan.
_HOP_LE = ("image/jpeg", "image/png", "image/gif", "image/webp")
# Nhan dang bang byte dau file, dung khi content-type sai hoac thieu. Zalo tra
# ve `application/octet-stream` cho anh kha thuong xuyen.
_CHU_KY = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)

_dem: OrderedDict[str, dict] = OrderedDict()


def _loai_anh(du_lieu: bytes, content_type: str) -> str | None:
    for chu_ky, loai in _CHU_KY:
        if du_lieu.startswith(chu_ky):
            return loai
    # WEBP: "RIFF" + 4 byte kich thuoc + "WEBP"
    if du_lieu[:4] == b"RIFF" and du_lieu[8:12] == b"WEBP":
        return "image/webp"
    ct = (content_type or "").split(";")[0].strip().lower()
    return ct if ct in _HOP_LE else None


async def khoi_anh(url: str) -> dict | None:
    """Tai anh va tra ve khoi noi dung dang base64. None neu khong dung duoc.

    None la duong lui BINH THUONG — URL het han, anh qua nang, dinh dang la.
    Nguoi goi phai thay bang mot dong chu, khong duoc am tham bo di: model khong
    thay anh ma cung khong biet la co anh se tra loi lac de.
    """
    if not url or not url.startswith(("http://", "https://")):
        return None
    if (san := _dem.get(url)) is not None:
        _dem.move_to_end(url)
        return san

    try:
        async with httpx.AsyncClient(timeout=TOI_DA_GIAY, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": "ZaloAgent/1.0"})
            r.raise_for_status()
            du_lieu = r.content
    except httpx.HTTPError as e:
        log.warning("khong_tai_duoc_anh", url=url[:60], error=str(e)[:100])
        return None

    if len(du_lieu) > TOI_DA_BYTE:
        log.warning("anh_qua_nang", url=url[:60], byte=len(du_lieu))
        return None

    loai = _loai_anh(du_lieu, r.headers.get("content-type", ""))
    if loai is None:
        log.warning("dinh_dang_anh_la", url=url[:60], ct=r.headers.get("content-type", "")[:40])
        return None

    khoi = {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": loai,
            "data": base64.standard_b64encode(du_lieu).decode(),
        },
    }
    _dem[url] = khoi
    while len(_dem) > TOI_DA_DEM:
        _dem.popitem(last=False)
    log.info("da_tai_anh_cho_model", loai=loai, kb=len(du_lieu) // 1024)
    return khoi


def xoa_dem() -> None:
    """Chi dung trong test."""
    _dem.clear()


__all__ = ["TOI_DA_BYTE", "TOI_DA_DEM", "khoi_anh", "xoa_dem"]
