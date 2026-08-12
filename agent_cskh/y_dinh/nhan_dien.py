"""Nhan ra Y DINH tu cau noi thuong, roi goi dung handler lenh co san.

## Vi sao co file nay

Khach hang that khong bao gio go `/baocao`. Chu shop cung khong — ho la nguoi
ban hang, khong phai nguoi dung terminal. Bat ho hoc thuoc mot bang lenh la cach
chac chan nhat de ho bo bot sau tuan dau.

## Cach lam: VIET LAI CAU NOI THANH LENH

`InboundEvent.is_command` / `command` / `command_args` deu suy ra tu `text`. Nen
thay vi sua tang lenh, ta chi doi `text` roi tha vao dung duong cu:

    "báo cáo hôm nay"  ->  text = "/baocao"  ->  cmd_baocao (khong doi mot dong)

Nho vay:
  - Toan bo handler trong `commands/` giu nguyen, da duoc test ky
  - MA TRAN QUYEN giu nguyen: `commands/router.handle()` van kiem
    `principal.at_least(min_role)`. Nguoi la noi "bao cao hom nay" thi khong
    chay gi ca, y het nhu ho go `/baocao`.
  - `tests/test_authz.py` van dung nguyen gia tri

## Lenh `/...` van chay ngam

Khong tai lieu nao nhac toi chung, khong bot nao goi y chung, khong ai *can*
chung. Giu lai vi hai ly do:
  - Nhan dien y dinh la doan, va doan thi co luc sai. Phai con mot duong chinh xac.
  - Dat nham kenh canh bao vao nhom khach hang la lo du lieu khach that.

## Nguyen tac khop: THA BO SOT CON HON BAT NHAM

Bat nham mot cau noi binh thuong thanh lenh thi bot lam mot viec khong ai yeu
cau — voi `xoa trang` thi do la mat du lieu. Bo sot thi nguoi ta chi noi lai
mot lan.

Vi vay: cum phai nam o DAU cau, va cau khong duoc qua dai (tru cac y dinh von
mang noi dung dai nhu them trang).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent_cskh.wiki import strip_accents

# Cau dai hon nguong nay thi khong coi la y dinh dieu khien nua — nguoi ta dang
# ke chuyen chu khong ra lenh. Tru cac y dinh co `mang_noi_dung`.
MAX_KY_TU = 70


@dataclass(frozen=True, slots=True)
class YDinh:
    lenh: str
    # Cac cach noi, dang DA BO DAU. Khop o dau cau.
    cach_noi: tuple[str, ...]
    # Viec nay co the mat du lieu hoac lo du lieu -> phai hoi lai truoc khi lam.
    nguy_hiem: bool = False
    # Y dinh mang theo noi dung dai (vd: them trang) -> bo gioi han do dai.
    mang_noi_dung: bool = False


# Thu tu QUAN TRONG: cum dai hon phai dung truoc cum ngan hon de khong bi nuot.
# Vi du "xoa trang" phai dung truoc "xoa", "nap lai kho" truoc "nap".
Y_DINH: tuple[YDinh, ...] = (
    # ---------- viec nguy hiem: hoi lai truoc khi lam ----------
    YDinh(
        "datkenhcanhbao",
        (
            "dat kenh canh bao",
            "gui canh bao ve day",
            "nhan canh bao o day",
            "dat cho nay lam kenh canh bao",
        ),
        nguy_hiem=True,
    ),
    YDinh("xoatrang", ("xoa trang", "bo trang", "go trang"), nguy_hiem=True),
    YDinh("suatrang", ("sua trang", "sua lai trang", "cap nhat trang"), nguy_hiem=True, mang_noi_dung=True),
    YDinh("xoatuvan", ("xoa tu van vien", "bo ai do khoi danh sach tu van"), nguy_hiem=True),
    # ---------- sua kho tri thuc ----------
    YDinh("themtrang", ("them trang", "tao trang", "viet trang moi"), mang_noi_dung=True),
    YDinh("xemtrang", ("xem trang", "doc trang", "mo trang")),
    YDinh("dstrang", ("co nhung trang nao", "danh sach trang", "kho co gi", "liet ke trang")),
    YDinh("nap", ("nap lai kho", "doc lai kho", "cap nhat kho", "nap lai kien thuc")),
    # ---------- van hanh hang ngay ----------
    YDinh("baocao", ("bao cao", "hom nay co viec gi", "co viec gi can lam")),
    YDinh("trangthai", ("con bao nhieu tin", "han muc", "trang thai han muc", "dung het bao nhieu")),
    YDinh("lead", ("khach moi", "ai de lai thong tin", "danh sach khach quan tam")),
    YDinh("bienlai", ("bien lai", "anh chuyen khoan cho doi soat")),
    YDinh("suckhoe", ("suc khoe", "bot con chay khong", "he thong the nao")),
    # ---------- tiep quan hoi thoai ----------
    YDinh("nhan", ("toi nhan chat nay", "de toi tra loi", "toi tiep quan", "toi lo chat nay")),
    YDinh("tha", ("tra lai cho bot", "bot tra loi tiep", "toi xong roi")),
    YDinh("quen", ("bat dau lai", "quen cuoc tro chuyen nay", "lam moi hoi thoai")),
    YDinh("nhantuvan", ("toi nhan tu van", "cho toi vao danh sach tu van")),
    YDinh("nghituvan", ("toi tam nghi", "khong nhan don moi")),
    YDinh("dstuvan", ("ai dang nhan khach", "danh sach tu van vien")),
    YDinh("kenhcanhbao", ("canh bao gui ve dau", "kenh canh bao dang o dau")),
    # ---------- ai cung dung duoc ----------
    YDinh("whoami", ("id cua toi", "toi la ai", "user id cua toi", "ma cua toi")),
    YDinh("nhogi", ("nho gi ve toi", "biet gi ve toi", "luu gi ve toi")),
    YDinh("xoanho", ("quen gium toi", "xoa cai da nho", "dung nho nua")),
    YDinh(
        "lienhe",
        ("gap nguoi that", "cho gap nhan vien", "noi chuyen voi nguoi", "cho gap chu shop"),
    ),
    YDinh("help", ("ban lam duoc gi", "giup duoc gi", "em lam duoc nhung gi")),
)

# "huong dan <chu de>" -> `/help <chu de>`.
#
# KHONG bat "huong dan" khong thoi: cau that cua khach — "hướng dẫn sử dụng sản
# phẩm", "hướng dẫn đặt hàng" — se bi nuot thanh lenh tro giup thay vi di tra
# kho tri thuc. Chi nhan khi phan con lai dung la mot chu de CO THAT.
_CHU_DE_HELP = {
    "kho": "kho",
    "kho tri thuc": "kho",
    "viec": "viec",
    "chia viec": "viec",
    "he thong": "hethong",
    "hethong": "hethong",
}

# Ten muc hien thi noi bang loi -> ten thu muc. De chu shop khoi phai nho
# "public/hocvien/internal".
_MUC = {
    "cong khai": "public",
    "ai cung xem": "public",
    "khach quen": "hocvien",
    "thanh vien": "hocvien",
    "noi bo": "internal",
    "chi nhan vien": "internal",
}

# Cac cach noi DONG Y. Dung cho cong xac nhan viec nguy hiem.
DONG_Y = frozenset(
    """
    dong y ok oke okie duoc ung u co dung chuan xac nhan lam di tiep tuc
    """.split()
)


def _dich_muc(phan_con_lai: str) -> str:
    """Doi "cong khai" -> "public" trong tham so, giu nguyen phan con lai."""
    thap = strip_accents(phan_con_lai.lower())
    for noi, thu_muc in _MUC.items():
        if thap.startswith(noi):
            return f"{thu_muc} {phan_con_lai[len(noi) :].strip()}".strip()
    return phan_con_lai


def doan_y_dinh(text: str) -> tuple[str, str] | None:
    """Tra ve (ten_lenh, tham_so) neu nhan ra y dinh, None neu khong.

    Ham THUAN — khong doc CSDL, khong biet nguoi noi la ai. Viec kiem quyen do
    `commands/router.handle()` lo, y het duong lenh `/...`.
    """
    goc = (text or "").strip()
    if not goc or goc.startswith("/"):
        return None

    # So khop tren DONG DAU: "them trang cong khai bang-gia\n<noi dung>" thi
    # y dinh nam o dong dau, con lai la noi dung.
    dong_dau = goc.split("\n", 1)[0]
    phang = strip_accents(dong_dau.lower()).strip()

    # "huong dan kho" -> ("help", "kho"). Xem ghi chu o `_CHU_DE_HELP`.
    for mo_dau in ("huong dan ", "tro giup "):
        if phang.startswith(mo_dau):
            chu_de = _CHU_DE_HELP.get(phang[len(mo_dau) :].strip(" ?."))
            if chu_de is not None:
                return "help", chu_de
            break

    for y in Y_DINH:
        for cum in y.cach_noi:
            if not phang.startswith(cum):
                continue
            if not y.mang_noi_dung and len(dong_dau) > MAX_KY_TU:
                # Cau dai ma bat dau bang cum nay thi nhieu kha nang la ke
                # chuyen, khong phai ra lenh.
                continue

            # Tham so = phan con lai cua CAU GOC (giu dau), cong ca phan xuong
            # dong neu y dinh nay mang noi dung.
            con_lai = dong_dau[len(cum) :].strip(" :,.-—")
            if y.mang_noi_dung:
                con_lai = _dich_muc(con_lai)
                phan_sau = goc.split("\n", 1)[1] if "\n" in goc else ""
                if phan_sau:
                    con_lai = f"{con_lai}\n{phan_sau}"
            return y.lenh, con_lai
    return None


def la_nguy_hiem(lenh: str) -> bool:
    return any(y.lenh == lenh and y.nguy_hiem for y in Y_DINH)


def la_dong_y(text: str) -> bool:
    """Nguoi dung vua xac nhan? Chi nhan cau NGAN va ro rang.

    "ok" thi dong y; "ok nhung ma khoan da" thi khong. Cho nay tha bo sot con
    hon bat nham: bat nham mot cau lung chung thanh "dong y xoa trang" la mat
    du lieu that.
    """
    phang = strip_accents((text or "").lower()).strip(" .!?,")
    if not phang or len(phang) > 20:
        return False
    return all(tu in DONG_Y for tu in re.split(r"\s+", phang) if tu)
