"""Tai mot trang web ve dang van ban tho.

BE MAT TAN CONG MOI: day la lan dau bot di lay noi dung tu Internet theo yeu cau
cua nguoi dung. Hai rui ro tach biet, phai xu ly rieng:

  1. SSRF — nguoi dung dua URL tro vao mang noi bo ("http://192.168.1.1/",
     "http://localhost:8080/", hoac mot ten mien cong khai co ban ghi A tro ve
     127.0.0.1). Xu ly o day: giai ten mien roi TU CHOI moi dia chi khong cong
     khai, va kiem lai o TUNG CHANG redirect chu khong chi chang dau.

  2. Prompt injection tu noi dung trang. KHONG xu ly o day — xu ly bang cach
     khong bao gio dua noi dung nay vao ngu canh hoi thoai chinh. Xem
     `tools/cham_bai.py`.

Khong dung `follow_redirects=True` cua httpx: no se di theo redirect ma khong
cho ta co hoi kiem tung chang. Mot URL cong khai redirect ve 169.254.169.254
(metadata cua may ao) la duong tan cong kinh dien.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from agent_cskh.logging_setup import get_logger
from agent_cskh.tools.notion_fetch import doc_trang_notion, la_notion

log = get_logger(__name__)

TOI_DA_BYTE = 1_000_000
# Tran RIENG cho tep nhi phan (PDF, DOCX), va KHONG BAO GIO cat giua chung.
#
# Ngay 08/08/2026 PDF dung chung tran 1 MB voi HTML. Cat bot HTML thi van doc
# duoc phan dau; cat bot PDF thi HONG HAN, vi `startxref` — bang muc luc cua ca
# file — nam o CUOI. Do that tren mot ban PDF cua ISO: pypdf nem
# "incorrect startxref pointer". DOCX con te hon: no la file ZIP, cat mot byte
# la khong giai nen duoc.
#
# Vuot tran thi TU CHOI RO RANG ("file nang qua"), khong cat roi bao "file bi
# loi" — hai chuyen khac nhau can hai cau khac nhau, vi cach chua khac nhau.
TOI_DA_BYTE_TEP = 10_000_000
TOI_DA_GIAY = 10.0
TOI_DA_CHANG = 3
TOI_DA_KY_TU = 15_000

# `text/csv` co mat vi Google Sheets xuat ra dinh dang do — va `chuan_hoa_url`
# TU DOI link Sheets sang `?format=csv`. Thieu no thi tinh nang tu tu choi chinh
# no: ta viet lai URL cho nguoi dung roi chan dung cai URL vua viet.
LOAI_CHAP_NHAN = ("text/html", "text/plain", "text/csv", "text/markdown", "application/xhtml")
LOAI_PDF = "application/pdf"
LOAI_DOCX = "openxmlformats-officedocument.wordprocessingml"
# Doc toi da bao nhieu trang PDF. Bai tap cua khoa la mot trang dich, mot ban
# offer, mot ke hoach — khong phai mot cuon sach. Cat o day de mot file 500
# trang khong lam ket ca luot.
TOI_DA_TRANG_PDF = 20

# Duoi nguong nay THAN trang coi nhu rong.
#
# Trang dung bang JavaScript (Notion published, Wix, Framer, Canva) tra ve mot
# khung HTML gan nhu khong co chu — noi dung do trinh duyet dung len sau. Do
# 08/08/2026: notion.site tra 171 ky tu, va toan bo la meta description.
#
# Neu khong chan o day thi cham_bai se cham 171 ky tu boilerplate roi dua ra
# nhan xet day tu tin. Bao loi con hon tra ve mot cau tra loi sai ma nghe dung.
NGUONG_THAN_RONG = 200
# Nguong rieng cho tep. Mot ban offer mot trang co the chi 120 ky tu ma van hoan
# chinh — ap nguong cua HTML vao day se tu choi nham bai that.
NGUONG_TEP_RONG = 80

# The khong mang noi dung nguoi doc — bo ca phan ben trong.
THE_BO_HAN = {"script", "style", "noscript", "svg", "template", "iframe"}
# The tao ranh gioi doan.
THE_XUONG_DONG = {
    "p",
    "br",
    "div",
    "section",
    "article",
    "li",
    "tr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
}


class LoiTaiTrang(RuntimeError):
    """Khong tai duoc trang. Thong diep viet cho NGUOI DUNG doc, khong lo ky thuat."""


@dataclass(frozen=True, slots=True)
class TrangWeb:
    url: str
    tieu_de: str
    van_ban: str
    # So ky tu THUC SU nam trong than trang, khong tinh meta description.
    ky_tu_than: int = 0


class _BocText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.phan: list[str] = []
        # Tach RIENG khoi `phan`. Hai con so nay ke hai cau chuyen khac nhau:
        # mot trang dung bang JavaScript co meta description day du nhung than
        # trang rong tron — gop chung lai thi khong con phan biet duoc.
        self.mo_ta: list[str] = []
        self.tieu_de = ""
        self._bo_qua = 0
        self._trong_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in THE_BO_HAN:
            self._bo_qua += 1
        elif tag == "title":
            self._trong_title = True
        elif tag in THE_XUONG_DONG:
            self.phan.append("\n")
        # Mo ta trang thuong nam o meta description — voi trang landing thi day
        # la cau quan trong nhat, ma no khong nam trong body.
        if tag == "meta":
            d = dict(attrs)
            if (d.get("name") or "").lower() in ("description", "og:description"):
                if noi_dung := (d.get("content") or "").strip():
                    self.mo_ta.append(f"\n[mô tả trang] {noi_dung}\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in THE_BO_HAN and self._bo_qua:
            self._bo_qua -= 1
        elif tag == "title":
            self._trong_title = False

    def handle_data(self, data: str) -> None:
        if self._bo_qua:
            return
        if self._trong_title:
            self.tieu_de += data.strip()
            return
        if t := data.strip():
            self.phan.append(t + " ")


def _gon(text: str) -> str:
    dong = [d.strip() for d in text.split("\n")]
    return "\n".join(d for d in dong if d)


_GG_TAI_LIEU = re.compile(
    r"https?://docs\.google\.com/(document|spreadsheets|presentation)/d/([\w-]+)"
)
_GG_DRIVE = re.compile(r"https?://drive\.google\.com/file/d/([\w-]+)")


def chuan_hoa_url(url: str) -> str:
    """Doi link CHIA SE thanh link TAI DUOC. Khong doi duoc thi tra nguyen.

    Nguoi ta dan cai ho thay tren thanh dia chi, khong ai di tim "duong dan
    xuat ban". Bat hoc vien lam viec do la mot buoc ho se lam sai, roi bot bao
    loi, roi ho bo cuoc.

    Cac endpoint duoi day deu la duong XUAT BAN CHINH THUC cua Google — dung
    cho tai lieu chu so huu da chia se cong khai. Khong co gi vuot rao: tai lieu
    chua chia se thi chung tra ve trang dang nhap, va lop chan noi dung mong se
    tu choi.
    """
    u = (url or "").strip()

    if m := _GG_TAI_LIEU.match(u):
        loai, ma = m.group(1), m.group(2)
        # Sheets khong xuat txt; csv la dang van ban gan nhat.
        dinh_dang = "csv" if loai == "spreadsheets" else "txt"
        return f"https://docs.google.com/{loai}/d/{ma}/export?format={dinh_dang}"

    if m := _GG_DRIVE.match(u):
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"

    # Dropbox: dl=0 mo trinh xem (HTML rong), dl=1 tra file that.
    if "dropbox.com" in u and "dl=0" in u:
        return u.replace("dl=0", "dl=1")

    return u


def kiem_url_an_toan(url: str) -> str:
    """Tra ve host neu URL an toan. Nem LoiTaiTrang neu khong.

    Kiem TAT CA dia chi ma ten mien giai ra, khong chi cai dau tien — mot ten
    mien co the tra ve nhieu ban ghi A, va chi can mot cai tro vao mang noi bo
    la du.
    """
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise LoiTaiTrang("Chỉ đọc được đường dẫn http hoặc https.")
    if not p.hostname:
        raise LoiTaiTrang("Đường dẫn không hợp lệ.")

    try:
        thong_tin = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80))
    except OSError as e:
        raise LoiTaiTrang("Không tìm thấy trang này.") from e

    for muc in thong_tin:
        ip = ipaddress.ip_address(muc[4][0])
        if not ip.is_global or ip.is_loopback or ip.is_private or ip.is_link_local:
            log.warning("chan_url_noi_bo", host=p.hostname, ip=str(ip))
            raise LoiTaiTrang("Đường dẫn này không mở công khai nên em không đọc được.")
    return p.hostname


async def tai_trang(url: str) -> TrangWeb:
    """Tai va boc van ban. Di theo redirect TAY de kiem tung chang."""
    url = chuan_hoa_url(url)

    # Notion co duong RIENG: trang published tra ve khung HTML khong co chu,
    # noi dung nam sau mot loi goi API. Xem `tools/notion_fetch.py`.
    if la_notion(url):
        if (chu := await doc_trang_notion(url)) is not None:
            return TrangWeb(url=url, tieu_de="", van_ban=chu, ky_tu_than=len(chu))
        # Doc khong duoc thi di tiep duong HTML — no se tu choi kem huong dan.

    hien_tai = url
    async with httpx.AsyncClient(timeout=TOI_DA_GIAY, follow_redirects=False) as c:
        for _ in range(TOI_DA_CHANG + 1):
            kiem_url_an_toan(hien_tai)
            try:
                r = await c.get(hien_tai, headers={"User-Agent": "ZaloAgent/1.0"})
            except httpx.TimeoutException as e:
                raise LoiTaiTrang("Trang này tải lâu quá nên em chưa đọc được.") from e
            except httpx.HTTPError as e:
                raise LoiTaiTrang("Em không mở được đường dẫn này.") from e

            if r.is_redirect:
                ke_tiep = r.headers.get("location")
                if not ke_tiep:
                    raise LoiTaiTrang("Em không mở được đường dẫn này.")
                hien_tai = str(httpx.URL(hien_tai).join(ke_tiep))
                continue
            break
        else:
            raise LoiTaiTrang("Đường dẫn này chuyển hướng vòng vo quá nhiều lần.")

    if r.status_code >= 400:
        raise LoiTaiTrang(f"Trang trả về lỗi {r.status_code}.")

    loai = (r.headers.get("content-type") or "").lower()

    # TEP NHI PHAN: dung nguyen ven, khong cat. Xem ghi chu o TOI_DA_BYTE_TEP.
    la_tep = LOAI_PDF in loai or LOAI_DOCX in loai
    if la_tep:
        if len(r.content) > TOI_DA_BYTE_TEP:
            raise LoiTaiTrang(
                f"File này nặng quá ({len(r.content) // 1_000_000} MB) nên em chưa đọc được. "
                "Anh/chị gửi bản gọn hơn, hoặc chỉ phần cần em xem giúp nhé."
            )
        van_ban = _boc_pdf(r.content) if LOAI_PDF in loai else _boc_docx(r.content)
        log.info("da_tai_tep", url=hien_tai[:80], loai=loai[:40], ky_tu=len(van_ban))
        return TrangWeb(url=hien_tai, tieu_de="", van_ban=van_ban, ky_tu_than=len(van_ban))

    noi_dung = r.content[:TOI_DA_BYTE]

    if not any(t in loai for t in LOAI_CHAP_NHAN):
        raise LoiTaiTrang(
            "Đường dẫn này không phải trang web, PDF hay Word đọc được. "
            "Anh/chị xuất ra PDF rồi gửi lại link, hoặc chụp màn hình gửi ảnh giúp em nhé."
        )

    try:
        html = noi_dung.decode(r.encoding or "utf-8", errors="replace")
    except (LookupError, UnicodeDecodeError):
        html = noi_dung.decode("utf-8", errors="replace")

    boc = _BocText()
    boc.feed(html)
    than = _gon("".join(boc.phan))
    van_ban = _gon("".join(boc.mo_ta) + "".join(boc.phan))[:TOI_DA_KY_TU]

    if len(than) < NGUONG_THAN_RONG:
        # Khong phai "trang rong" — la "ta khong doc duoc trang nay". Hai chuyen
        # khac han nhau, va cau tra loi phai noi ro cach chua: hoc vien khong
        # biet trang cua ho dung bang JavaScript.
        log.info("trang_dung_bang_js", url=hien_tai[:80], ky_tu_than=len(than))
        raise LoiTaiTrang(
            "Trang này dựng bằng JavaScript nên em chỉ đọc được phần khung, không thấy nội dung. "
            "Hay gặp với Notion, Wix, Framer, Canva. Anh/chị xuất trang ra PDF rồi gửi link "
            "file đó, hoặc chụp màn hình gửi ảnh giúp em."
        )

    log.info("da_tai_trang", url=hien_tai[:80], ky_tu=len(van_ban), ky_tu_than=len(than))
    return TrangWeb(url=hien_tai, tieu_de=boc.tieu_de[:200], van_ban=van_ban, ky_tu_than=len(than))


def _boc_pdf(du_lieu: bytes) -> str:
    """Boc chu tu PDF. Chi TRICH VAN BAN — khong chay gi trong file.

    PDF chua duoc JavaScript va hanh dong tu mo. `extract_text()` khong dien
    giai chung, nen be mat tan cong o day la cua mot bo PHAN TICH CU PHAP, khong
    phai cua mot trinh thong dich.

    Chu boc ra van la DU LIEU KHONG TIN CAY, y het HTML: no di vao loi goi cham
    diem rieng co `tools=None`, khong bao gio vao ngu canh hoi thoai chinh.
    """
    import io

    from pypdf import PdfReader

    # `PyPdfError` la lop goc cua moi loi pypdf. KHONG dung `PdfError` — ten do
    # khong ton tai trong pypdf 6, va mot ImportError o day se lam ca luot chet
    # thay vi tra ve mot cau loi doc duoc.
    from pypdf.errors import PyPdfError

    try:
        doc = PdfReader(io.BytesIO(du_lieu))
        if doc.is_encrypted:
            raise LoiTaiTrang("File PDF này có mật khẩu nên em không mở được.")
        phan = [t for tr in doc.pages[:TOI_DA_TRANG_PDF] if (t := tr.extract_text())]
    except LoiTaiTrang:
        raise
    except (PyPdfError, ValueError, OSError, RecursionError, KeyError) as e:
        raise LoiTaiTrang("Em không đọc được file PDF này — có thể file bị lỗi.") from e

    van_ban = _gon("\n".join(phan))[:TOI_DA_KY_TU]
    if len(van_ban) < NGUONG_TEP_RONG:
        # PDF xuat tu ban scan hoac toan anh thi khong co lop chu nao ca.
        raise LoiTaiTrang(
            "File PDF này gần như không có chữ nào đọc được — có thể là bản scan "
            "hoặc toàn ảnh. Anh/chị chụp màn hình gửi ảnh trực tiếp cho em nhé."
        )
    return van_ban


def _boc_docx(du_lieu: bytes) -> str:
    """Boc chu tu .docx. CHI dung thu vien chuan — khong them phu thuoc nao.

    .docx la mot file ZIP chua XML; chu nam trong cac the <w:t>, gom theo doan
    <w:p>. `python-docx` khong mang lai gi hon cho viec chi doc chu, va mot phu
    thuoc them la mot thu nua phai vá khi co lo hong.

    Doc bang ElementTree co rui ro XML bom (billion laughs). O day rui ro thap
    hon binh thuong vi ta da chan kich thuoc o 10 MB truoc khi vao day, nhung
    van bat moi ParseError va tra ve loi doc duoc.
    """
    import io
    import xml.etree.ElementTree as ET
    import zipfile

    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with zipfile.ZipFile(io.BytesIO(du_lieu)) as z:
            xml = z.read("word/document.xml")
        goc = ET.fromstring(xml)  # noqa: S314 - da chan 10MB o tren, moi loi deu bat
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError, ValueError) as e:
        raise LoiTaiTrang(
            "Em không đọc được file Word này. Anh/chị xuất ra PDF rồi gửi lại link giúp em nhé."
        ) from e

    dong = []
    for p in goc.iter(W + "p"):
        chu = "".join(t.text or "" for t in p.iter(W + "t")).strip()
        if chu:
            dong.append(chu)

    van_ban = _gon("\n".join(dong))[:TOI_DA_KY_TU]
    if len(van_ban) < NGUONG_TEP_RONG:
        raise LoiTaiTrang(
            "File Word này gần như không có chữ nào — có thể nội dung toàn là ảnh. "
            "Anh/chị chụp màn hình gửi ảnh cho em nhé."
        )
    return van_ban
