"""Ba nguong tin cay cua che do `tra_cuu`.

Che do nay khong co model nao de tu phan dinh "minh co chac khong". Thay vao do
no dung DIEM tim kiem tu `WikiStore.search_scored()`, va ba nguong duoi day la
toan bo phan phan dinh do.

Vi sao tach ra mot file rieng cho ba con so: chung la thu ban se chinh nhieu
nhat sau khi chay that vai ngay, va chinh chung thi khong duoc phep dong vao
logic dinh tuyen. De chung nam lan trong `dinh_tuyen.py` la dam bao sau nay
khong ai dam sua.

CHINH THE NAO:
  Bot tra loi sai nhieu     -> tang NGUONG_CHAC
  Bot chuyen nguoi qua nhieu -> ha NGUONG_HOI_LAI
  Bot hoi lai lung tung      -> tang NGUONG_HOI_LAI, hoac them `tu_khoa` cho trang

Cach do dung: chay `uv run agent-cskh chat`, go 10 cau khach hay hoi that, dem
xem may cau roi vao dung o.
"""

from __future__ import annotations

from typing import Literal

from agent_cskh.wiki import WikiPage

# Diem tu day tro len thi tra loi thang.
#
# 25 khong phai con so thieng. No la "khop nguyen cum o phan dau (+20) cong mot
# lan khop tu don o phan dau (+5)" — tuc la khach go gan dung ten trang. Do la
# muc do chac chan toi thieu de dam mo mieng thay mot doanh nghiep that.
NGUONG_CHAC = 25

# Duoi NGUONG_CHAC nhung tu day tro len thi HOI LAI co chon lua, khong doan.
#
# 8 = khop hai tu don o phan dau, hoac mot tu dau cong vai lan trong than bai.
# Du de biet "co lien quan", khong du de biet "dung trang".
NGUONG_HOI_LAI = 8

# Chenh lech toi thieu giua trang nhat va trang nhi de coi la "ro rang hon han".
#
# Hai trang diem 30 va 29 thi con so cao khong con nghia gi — chon bua mot trong
# hai la 50% sai. Luc do phai hoi lai du diem da vuot NGUONG_CHAC.
CHENH_LECH_RO_RANG = 10

# Toi da bao nhieu lua chon khi hoi lai. Zalo khong co nut bam nen khach phai go
# so — qua ba lua chon la khong ai doc het.
TOI_DA_LUA_CHON = 3

KetQua = Literal["chac", "phong_doan", "hoi_lai", "khong_biet"]


def phan_dinh(ket_qua: list[tuple[int, WikiPage]]) -> KetQua:
    """Nhin diem, quyet dinh lam gi. Ham THUAN — test duoc khong can gi ca.

      chac        tra loi thang
      phong_doan  tra loi NHUNG noi ro la dang doan ("em nghĩ anh/chị hỏi về X")
      hoi_lai     dua lua chon danh so
      khong_biet  chuyen nguoi that, ghi vao `thieu_trang`
    """
    if not ket_qua:
        return "khong_biet"

    diem_nhat = ket_qua[0][0]
    if diem_nhat < NGUONG_HOI_LAI:
        return "khong_biet"

    if diem_nhat < NGUONG_CHAC:
        # CHI CO MOT UNG VIEN thi hoi lai la vo nghia — khong ai muon doc mot
        # menu chi co mot dong roi phai go "1".
        #
        # Truong hop nay xay ra nhieu hon tuong: khach go "cai nay mac khong",
        # trung dung mot dong `tu_khoa` cua trang bang gia va khong trung gi
        # khac. Diem thap (khong khop tieu de) nhung ung vien thi ro rang.
        #
        # Tra loi kem mot cau ra dau la dung: khach doc mot dong dau la biet ngay
        # co dung y minh khong, va sua lai duoc trong mot luot.
        return "phong_doan" if len(ket_qua) == 1 else "hoi_lai"

    # Da vuot nguong chac, nhung con phai hon han trang thu hai.
    if len(ket_qua) > 1 and diem_nhat - ket_qua[1][0] < CHENH_LECH_RO_RANG:
        return "hoi_lai"
    return "chac"
