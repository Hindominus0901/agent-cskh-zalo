"""Bay dau vao: nhung nhom cau hoi khong bao gio duoc tra loi.

Day la LOP 2 trong ba lop siet pham vi. No hep va chinh xac cao — chi bat nhung
nhom ma cau tra loi sai co the gay hai that (y te, phap ly, dau tu) hoac ro rang
khong phai viec cua bot (lam ho bai mon khac, chinh tri, do system prompt).

Chay TRUOC khi goi LLM nen tiet kiem ca quota Zalo lan tien token.

NGUYEN TAC KHI THEM MAU MOI: moi mau la them mot rui ro chan nham. Truoc khi
them, hay viet cau hop le gan no nhat va kiem tra `khong_duoc_chan` van sach.
Danh sach ngan ma dung tot hon danh sach dai ma hay bat oan — mot khach bi tu
choi oan la mot khach mat, con mot cau y te tra loi bua la mot rui ro that.

CO Y BO QUA: cac cau chi "kho" chu khong "cam". Bot khong biet gia thi da co lop
1 (bo doi cau tra loi khong tra kho tri thuc) lo. Lop nay chi danh cho thu ma
KHONG BAO GIO duoc tra loi, du kho tri thuc co day du den may.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent_cskh.wiki import strip_accents


@dataclass(frozen=True, slots=True)
class Nhom:
    ten: str
    mau: re.Pattern[str]
    tra_loi: str


def _p(*mau: str) -> re.Pattern[str]:
    return re.compile("|".join(mau))


# Cau tra loi phai LICH SU va CHI DUONG. Tu choi coc loc lam khach thay minh hoi
# sai; tu choi kem loi de nghi thi ho biet di dau tiep.
_Y_TE = (
    "Dạ phần này liên quan sức khoẻ nên em không tư vấn được ạ. "
    "Anh/chị hỏi bác sĩ hoặc cơ sở y tế giúp em nhé."
)
_PHAP_LY = (
    "Dạ phần này cần ý kiến pháp lý nên em không tư vấn được ạ. "
    "Anh/chị hỏi luật sư để chắc chắn nhé."
)
_DAU_TU = (
    "Dạ em không tư vấn đầu tư hay tài chính được ạ. "
    "Bên em chỉ hỗ trợ phần thương hiệu cá nhân thôi."
)
_HO_BAI = (
    "Dạ em chỉ hỗ trợ nội dung của khoá học thôi ạ, không làm bài hộ hay hỗ trợ môn khác được."
)
_CHINH_TRI = "Dạ chuyện này em không bàn được ạ. Mình quay lại phần khoá học nhé."
_DO_HE_THONG = "Dạ em chỉ hỗ trợ được phần nội dung khoá học và dịch vụ bên em thôi ạ."

# Mau viet o dang DA BO DAU va viet thuong. Xem `ngoai_pham_vi()`.
NHOM_CAM: tuple[Nhom, ...] = (
    Nhom(
        "y_te",
        _p(
            r"\btrieu chung\b",
            r"\buong thuoc (gi|nao)\b",
            r"\b(em|toi|minh|anh|chi) (bi )?(dau|om|sot|benh) ",
            r"\bkham (benh|o dau)\b",
            r"\bchua (benh|khoi)\b",
            r"\blieu (luong|trinh) thuoc\b",
        ),
        _Y_TE,
    ),
    Nhom(
        "phap_ly",
        _p(
            r"\b(co|bi) (kien|phat|truy to)\b",
            r"\bkien (ra toa|len toa|ho)\b",
            r"\bvi pham phap luat\b",
            r"\btrach nhiem hinh su\b",
            r"\bdieu \d+ (bo luat|luat)\b",
            r"\btron thue\b",
        ),
        _PHAP_LY,
    ),
    Nhom(
        "dau_tu",
        _p(
            r"\bnen mua (co phieu|chung khoan|coin|bitcoin|vang|dat)\b",
            r"\bdau tu (gi|vao dau|coin|chung khoan|forex)\b",
            r"\b(ma )?co phieu nao\b",
            r"\bchoi (chung khoan|forex|coin)\b",
            r"\blai suat ngan hang nao\b",
        ),
        _DAU_TU,
    ),
    Nhom(
        "ho_bai_mon_khac",
        _p(
            r"\b(giai|lam) (ho |giup )?(bai|de) (toan|ly|hoa|van|sinh|su|dia|tieng anh)\b",
            r"\bviet (ho|giup) (bai )?(luan van|tieu luan|khoa luan)\b",
            r"\blam ho bai tap\b",
            r"\bdich (ho|giup) (doan|bai) nay\b",
        ),
        _HO_BAI,
    ),
    Nhom(
        "chinh_tri",
        _p(
            r"\bdang cong san\b",
            r"\bchinh phu (sai|dung|tham nhung)\b",
            r"\bbau cu\b",
            r"\bbieu tinh\b",
        ),
        _CHINH_TRI,
    ),
    Nhom(
        "do_he_thong",
        _p(
            r"\bbo qua (moi )?(huong dan|chi dan|quy tac|lenh)\b",
            # Khoang giua de mo vi cau that hay chen tu ("all previous", "the
            # above"). Gioi han 30 ky tu de khong nuot ca cau dai vo tinh chua
            # ca hai tu.
            r"\bignore\b.{0,30}\binstructions?\b",
            r"\b(system )?prompt cua (ban|may|bot)\b",
            r"\bin ra (system prompt|toan bo huong dan)\b",
            r"\bban dang dung (model|api key) (gi|nao)\b",
            r"\bquen (het )?(moi thu|nhung gi) (o )?tren\b",
        ),
        _DO_HE_THONG,
    ),
)


def ngoai_pham_vi(text: str | None) -> Nhom | None:
    """Tra ve nhom bi cam neu cau hoi roi vao do, None neu khong.

    Bo dau truoc khi khop: khach Viet go khong dau rat nhieu, va ke muon vuot
    rao cung hay bo dau. Mot bo mau viet o dang khong dau bat duoc ca hai.
    """
    if not text or not text.strip():
        return None
    phang = strip_accents(text)
    for nhom in NHOM_CAM:
        if nhom.mau.search(phang):
            return nhom
    return None
