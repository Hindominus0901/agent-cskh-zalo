"""Cong xac nhan cho viec nguy hiem.

Nhan dien y dinh la DOAN. Doan sai mot cau hoi thi chi kho chiu; doan sai thanh
"xoa trang" thi mat du lieu, doan sai thanh "dat kenh canh bao" thi tu do tro di
moi canh bao — kem ten khach va chat_id cua ho — chay vao mot nhom khach hang.

Nen nhung viec do khong duoc lam ngay. Bot hoi lai mot cau, nguoi dung noi
"đồng ý" thi moi chay.

Duong lenh `/...` KHONG di qua cong nay: go dung `/xoatrang bang-gia` la mot
hanh dong co y thuc, khong phai mot cau doan.

Trang thai nam trong RAM. Mat khi khoi dong lai — va do la huong sai an toan:
mat mot xac nhan dang cho thi nguoi dung noi lai mot lan, con giu lai qua lan
khoi dong thi co the chay mot viec ho da quen mat.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from agent_cskh.logging_setup import get_logger

log = get_logger(__name__)

# Qua han nay thi cho xac nhan bi huy. Nguoi ta di lam viec khac roi quay lai
# noi "ok" cho mot chuyen khac han.
HAN_CHO = timedelta(minutes=3)


@dataclass(frozen=True, slots=True)
class DangCho:
    lenh: str
    tham_so: str
    mo_ta: str
    luc: datetime


class CongXacNhan:
    def __init__(self) -> None:
        self._cho: dict[str, DangCho] = {}

    def dat(self, chat_id: str, *, lenh: str, tham_so: str, mo_ta: str) -> str:
        """Ghi nho viec dang cho, tra ve cau hoi lai de gui cho nguoi dung."""
        self._cho[chat_id] = DangCho(lenh, tham_so, mo_ta, datetime.now(UTC))
        log.info("cho_xac_nhan", chat_id=chat_id[:8], lenh=lenh)
        return f"{mo_ta}\n\nAnh/chị xác nhận giúp em nhé — nhắn “đồng ý” là em làm ngay ạ."

    def lay(self, chat_id: str) -> DangCho | None:
        """Lay viec dang cho va XOA khoi hang doi. Qua han thi coi nhu khong co."""
        cho = self._cho.pop(chat_id, None)
        if cho is None:
            return None
        if datetime.now(UTC) - cho.luc > HAN_CHO:
            log.info("xac_nhan_qua_han", chat_id=chat_id[:8], lenh=cho.lenh)
            return None
        return cho

    def huy(self, chat_id: str) -> None:
        self._cho.pop(chat_id, None)

    def dang_cho(self, chat_id: str) -> bool:
        return chat_id in self._cho


# Cau hoi lai cho tung viec. Phai noi ro HAU QUA, khong chi hoi "co chac khong".
MO_TA = {
    "datkenhcanhbao": (
        "Đặt cuộc trò chuyện này làm nơi nhận cảnh báo nghĩa là từ giờ mọi thông "
        "báo — kèm tên khách và mã cuộc trò chuyện của họ — sẽ gửi về đây.\n\n"
        "⚠️ Đừng làm việc này trong nhóm có khách hàng."
    ),
    "xoatrang": "Em sẽ xoá trang “{tham_so}” khỏi kho tri thức. Bản cũ vẫn được giữ lại.",
    "suatrang": "Em sẽ ghi đè nội dung trang “{tham_so}”. Bản cũ vẫn được giữ lại.",
    "xoatuvan": "Em sẽ bỏ “{tham_so}” khỏi danh sách nhận khách.",
}


def mo_ta_viec(lenh: str, tham_so: str) -> str:
    khuon = MO_TA.get(lenh, "Em sẽ thực hiện việc này.")
    ten = (tham_so.split("\n", 1)[0] or "…").strip()
    return khuon.replace("{tham_so}", ten)
