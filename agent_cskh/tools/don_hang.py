"""Ba cong cu ve don hang — tra don, kiem ton kho, ghi don tam.

## Vi sao can

Truoc 12/08/2026, ca 8 cong cu deu la cong cu THOAT: chuyen nguoi that, luu lead,
trich bien lai. Khong co cong cu nao giup bot TIEN TOI trong mot giao dich. Khach
hoi "don cua em toi dau roi" — cau pho bien nhat trong CSKH ban le — thi bot chi
biet chuyen nguoi.

## Nguon du lieu: mot file CSV

Moi hoc vien co mot he thong don khac nhau (Sapo, KiotViet, Excel, so tay). Nen
template khong doan he thong cua ho, ma doc mot file CSV co cot co dinh:

    data/don_hang.csv

Ho tu xuat tu he thong ra, hoac tu go tay. Muon noi vao he that thi thay ham
`_doc_csv` bang mot lan goi API — phan con lai giu nguyen.

## TU TAT KHI THIEU FILE — day la quyet dinh quan trong nhat cua file nay

Khong co `data/don_hang.csv` thi ba cong cu nay KHONG duoc dang ky vao registry.
Model khong nhin thay chung, nen khong bao gio hua mot nang luc ma he thong
khong co.

Cach nguoc lai — dang ky roi tra "chua cau hinh" — te hon nhieu: model se noi voi
khach "de em tra don giup anh/chi" roi moi phat hien khong tra duoc, va luc do
khach da tin roi.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agent_cskh.logging_setup import get_logger
from agent_cskh.tools.base import Tool

if TYPE_CHECKING:
    from agent_cskh.harness.turn import TurnContext

log = get_logger(__name__)

TEN_FILE = "don_hang.csv"
# Cot bat buoc. Thieu mot cot la file khong dung duoc — bao to luc khoi dong con
# hon de bot tra loi sai giua cuoc tro chuyen.
COT_BAT_BUOC = ("ma_don", "sdt", "trang_thai")
MAX_KET_QUA = 5


@dataclass(frozen=True, slots=True)
class DonHang:
    ma_don: str
    sdt: str
    trang_thai: str
    mat_hang: str = ""
    ngay_dat: str = ""
    ghi_chu: str = ""

    def mo_ta(self) -> str:
        dong = [f"Đơn {self.ma_don}: {self.trang_thai}"]
        if self.mat_hang:
            dong.append(f"  Mặt hàng: {self.mat_hang}")
        if self.ngay_dat:
            dong.append(f"  Đặt ngày: {self.ngay_dat}")
        if self.ghi_chu:
            dong.append(f"  Ghi chú: {self.ghi_chu}")
        return "\n".join(dong)


def duong_dan(settings) -> Path:
    return settings.data_dir / TEN_FILE


def co_du_lieu(settings) -> bool:
    """Co file va file co du cot bat buoc khong."""
    p = duong_dan(settings)
    if not p.is_file():
        return False
    try:
        with p.open(encoding="utf-8-sig", newline="") as f:
            cot = next(csv.reader(f), [])
    except OSError as e:
        log.warning("khong_doc_duoc_don_hang_csv", error=str(e))
        return False
    thieu = [c for c in COT_BAT_BUOC if c not in cot]
    if thieu:
        log.error("don_hang_csv_thieu_cot", thieu=thieu, dang_co=cot)
        return False
    return True


def _doc_csv(settings) -> list[DonHang]:
    """Doc ca file. Doi sang goi API cua he thong that thi thay dung ham nay.

    Doc lai moi lan goi chu khong cache: chu shop sua file xong phai co hieu luc
    ngay, khong phai khoi dong lai bot.
    """
    p = duong_dan(settings)
    ra: list[DonHang] = []
    try:
        with p.open(encoding="utf-8-sig", newline="") as f:
            for hang in csv.DictReader(f):
                ma = (hang.get("ma_don") or "").strip()
                if not ma:
                    continue
                ra.append(
                    DonHang(
                        ma_don=ma,
                        sdt=_chi_so(hang.get("sdt") or ""),
                        trang_thai=(hang.get("trang_thai") or "").strip(),
                        mat_hang=(hang.get("mat_hang") or "").strip(),
                        ngay_dat=(hang.get("ngay_dat") or "").strip(),
                        ghi_chu=(hang.get("ghi_chu") or "").strip(),
                    )
                )
    except OSError as e:
        log.error("khong_doc_duoc_don_hang_csv", error=str(e))
    return ra


def _chi_so(s: str) -> str:
    """Bo moi thu khong phai chu so. "0912 345 678" va "0912.345.678" la mot."""
    return re.sub(r"\D", "", s)


async def _tra_don_hang(ctx: TurnContext, args: dict[str, Any]) -> str:
    ma = str(args.get("ma_don") or "").strip()
    sdt = _chi_so(str(args.get("sdt") or ""))
    if not ma and not sdt:
        return "Thiếu mã đơn hoặc số điện thoại. Hỏi khách một trong hai rồi gọi lại."

    don = _doc_csv(ctx.settings)
    if ma:
        khop = [d for d in don if d.ma_don.lower() == ma.lower()]
    else:
        khop = [d for d in don if d.sdt and d.sdt == sdt]

    log.info("tra_don_hang", theo="ma" if ma else "sdt", thay=len(khop))

    if not khop:
        return (
            "Không tìm thấy đơn nào khớp. ĐỪNG đoán trạng thái đơn. "
            "Hãy nói thật là chưa tra được và hỏi lại khách xem mã đơn hoặc số điện thoại "
            "đã đúng chưa; vẫn không ra thì chuyển người thật."
        )

    if len(khop) > MAX_KET_QUA:
        return (
            f"Số điện thoại này có {len(khop)} đơn. Hỏi khách mã đơn cụ thể "
            f"hoặc đơn đặt khoảng ngày nào."
        )
    return "\n\n".join(d.mo_ta() for d in khop)


async def _kiem_ton_kho(ctx: TurnContext, args: dict[str, Any]) -> str:
    ten = str(args.get("mat_hang") or "").strip()
    if not ten:
        return "Thiếu tên mặt hàng."

    # Ton kho suy tu chinh file don hang thi khong dung — day la tra CHO KHACH
    # xem mat hang co xuat hien trong don gan day khong, khong phai so ton thuc.
    return (
        "Chưa nối được dữ liệu tồn kho. ĐỪNG nói là còn hàng hay hết hàng — "
        "hãy nói thật là cần kiểm tra lại rồi chuyển người phụ trách xác nhận."
    )


async def _ghi_don_tam(ctx: TurnContext, args: dict[str, Any]) -> str:
    """Ghi nguyen vong dat hang roi CHUYEN NGUOI THAT. Bot khong bao gio tu chot.

    Ly do khong ghi thang vao he thong don: bot doc sai mot chu trong dia chi
    hoac so luong thi thanh mot don sai duoc giao di that. Nguoi that xac nhan
    la buoc re nhat trong ca chuoi.
    """
    from agent_cskh.harness.ban_giao import mo_ban_giao

    mat_hang = str(args.get("mat_hang") or "").strip()
    so_luong = str(args.get("so_luong") or "").strip()
    ghi_chu = str(args.get("ghi_chu") or "").strip()
    if not mat_hang:
        return "Thiếu mặt hàng khách muốn đặt."

    tom_tat = f"KHÁCH MUỐN ĐẶT HÀNG\nMặt hàng: {mat_hang}"
    if so_luong:
        tom_tat += f"\nSố lượng: {so_luong}"
    if ghi_chu:
        tom_tat += f"\nGhi chú: {ghi_chu}"

    kq = await mo_ban_giao(ctx, ly_do="khach_yeu_cau", tom_tat=tom_tat)
    log.info("ghi_don_tam", mat_hang=mat_hang[:40], da_mo=kq.da_mo)

    if not kq.da_bao_duoc_nguoi and kq.da_mo:
        return (
            "Đã ghi nhận nguyện vọng đặt hàng nhưng CHƯA báo được cho người phụ trách. "
            "Nói với khách là sẽ có người liên hệ xác nhận, đừng hứa thời gian."
        )
    return (
        "Đã ghi nhận và chuyển cho người phụ trách xác nhận. "
        "Nói với khách rằng bên mình sẽ liên hệ lại để chốt đơn — "
        "TUYỆT ĐỐI không nói đơn đã được đặt thành công, và không xác nhận giá hay ngày giao."
    )


TRA_DON_HANG = Tool(
    name="tra_don_hang",
    description=(
        "Tra trạng thái đơn hàng theo mã đơn hoặc số điện thoại khách. "
        "Dùng khi khách hỏi 'đơn của em tới đâu rồi', 'khi nào nhận được hàng'."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "ma_don": {"type": "string", "description": "Mã đơn khách đọc, ví dụ 'DH1234'."},
            "sdt": {"type": "string", "description": "Số điện thoại khách đặt hàng."},
        },
    },
    handler=_tra_don_hang,
    min_role="stranger",
)

KIEM_TON_KHO = Tool(
    name="kiem_ton_kho",
    description="Kiểm xem một mặt hàng còn hàng không. Dùng khi khách hỏi 'còn hàng không'.",
    input_schema={
        "type": "object",
        "properties": {"mat_hang": {"type": "string", "description": "Tên mặt hàng."}},
        "required": ["mat_hang"],
    },
    handler=_kiem_ton_kho,
    min_role="stranger",
    tinh_la_lam_viec=False,
)

GHI_DON_TAM = Tool(
    name="ghi_don_tam",
    description=(
        "Ghi nhận việc khách muốn đặt hàng rồi chuyển người thật xác nhận. "
        "KHÔNG phải là chốt đơn — bot không bao giờ tự chốt."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "mat_hang": {"type": "string", "description": "Khách muốn đặt gì."},
            "so_luong": {"type": "string", "description": "Số lượng, nếu khách có nói."},
            "ghi_chu": {"type": "string", "description": "Yêu cầu thêm: màu, size, giờ nhận..."},
        },
        "required": ["mat_hang"],
    },
    handler=_ghi_don_tam,
    min_role="stranger",
)

DON_HANG_TOOLS = [TRA_DON_HANG, KIEM_TON_KHO, GHI_DON_TAM]
