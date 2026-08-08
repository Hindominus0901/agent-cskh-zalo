"""Bao cao hang ngay cho chu bot.

Ham THUAN: chi doc CSDL roi tra ve chuoi. Khong goi mang, khong ton mot token
LLM nao. Nho vay job hang ngay va lenh /baocao dung chung duoc mot duong, va test
duoc ma khong can Zalo hay Claude.

Thu tu trinh bay co chu dich: phan CAN AI DO LAM GI len truoc, so lieu xuong sau.
Bao cao ma phai doc het moi biet co viec can lam thi vai hom la khong ai doc nua.

DAY LA MOT NUA CUA VONG LAP HOC. Nua kia la `ChatRepo.ghi_thieu_trang()`: moi
lan bot tu choi vi kho tri thuc thieu, cau hoi NGUYEN VAN duoc ghi lai. Bao cao
nay gom chung lai va dat len dau. Khong co buoc nay thi bot tu choi rat ngoan
ma chu bot khong bao gio biet phai viet them trang gi — va do la nut that lon
nhat cua ca he thong.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agent_cskh.security import QuotaGuard
from agent_cskh.store.repo import ChatRepo

MAX_KY_TU = 2000
# Toi da bao nhieu dong cho moi muc "can lam". Dai hon thi khong ai doc het.
MAX_DONG_MOI_MUC = 5


def _cat(dong: list[str], gioi_han: int = MAX_KY_TU) -> str:
    """Ghep va cat cho vua mot tin Zalo, giu nguyen phan dau (phan quan trong)."""
    text = "\n".join(dong)
    if len(text) <= gioi_han:
        return text
    return text[: gioi_han - 20].rstrip() + "\n… (còn nữa)"


def _gon_cau(cau: str, toi_da: int = 70) -> str:
    cau = " ".join((cau or "").split())
    return cau if len(cau) <= toi_da else cau[: toi_da - 1] + "…"


def _gom_theo_chu_de(rows: list[dict], toi_da: int = MAX_DONG_MOI_MUC) -> list[dict]:
    """Gom cac cau HOI CUNG MOT Y, va noi ro co bao nhieu nguoi hoi.

    Gom de DOC, khong phai de xoa bot: mot cau ba nguoi cung hoi la mot trang
    can viet gap hon mot cau chi mot nguoi hoi. Con so do la thu quyet dinh thu
    tu, nen no phai hien ra.
    """
    theo: dict[str, list[dict]] = {}
    for r in rows:
        khoa = (r.get("chu_de") or _gon_cau(r["cau_hoi"], 40)).lower()
        theo.setdefault(khoa, []).append(r)

    ra: list[dict] = []
    for nhom in sorted(theo.values(), key=len, reverse=True)[:toi_da]:
        dau = dict(nhom[0])
        if len(nhom) > 1:
            dau["cau_hoi"] = f"{_gon_cau(dau['cau_hoi'], 55)} ({len(nhom)} người hỏi)"
        ra.append(dau)
    return ra


async def dung_bao_cao(
    *,
    repo: ChatRepo,
    quota: QuotaGuard,
    health_tom_tat: str = "",
    health_model_tom_tat: str = "",
) -> str:
    can_lam: list[str] = []

    # DAT LEN DAU DANH SACH.
    #
    # Bot huu ich dung bang do phu cua kho tri thuc, va day la thu duy nhat cho
    # biet kho con thieu cho nao. Cac muc khac la viec cua hom nay; muc nay la
    # thu quyet dinh ngay mai bot co gioi hon khong.
    thieu = await repo.thieu_trang_gan_day(ngay=1)
    if thieu:
        can_lam.append(f"📚 {len(thieu)} câu bot KHÔNG trả lời được — kho tri thức thiếu:")
        can_lam += [f'   • "{_gon_cau(r["cau_hoi"])}"' for r in _gom_theo_chu_de(thieu)]
        can_lam.append("   Bổ sung bằng /themtrang public <tên-trang>")

    cho_nguoi = await repo.pending_handoffs(limit=50)
    if cho_nguoi:
        can_lam.append(f"🔔 {len(cho_nguoi)} khách đang chờ người tiếp quản")

    bien_lai = await repo.pending_payment_claims()
    if bien_lai:
        can_lam.append(f"🧾 {len(bien_lai)} biên lai chờ đối soát")

    # ---------- so lieu ----------
    hom_qua = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    lead_moi = await repo.count_leads(since_iso=hom_qua)
    st = await quota.status()
    chi_phi = await repo.chi_phi_hom_nay()

    dong = ["📋 BÁO CÁO HÔM NAY", ""]

    if can_lam:
        dong.append("── CẦN LÀM ──")
        dong += can_lam
        dong.append("")
    else:
        # Khong co viec gi thi noi thang mot cau. Bao cao rong ma van dai dong
        # se day nguoi ta toi cho bo qua ca nhung ban co viec that.
        dong.append("Không có việc gì cần xử lý.")
        dong.append("")

    dong.append("── SỐ LIỆU ──")
    dong.append(f"Khách mới để lại thông tin (24h): {lead_moi}")
    dong.append(f"Hạn mức Zalo: {st.used}/{st.limit} ({st.pct:.0f}%)")
    if chi_phi:
        dong.append(f"Chi phí AI hôm nay: ${chi_phi:.4f}")

    if health_tom_tat or health_model_tom_tat:
        dong.append("")
        dong.append("── HỆ THỐNG ──")
        if health_tom_tat:
            dong.append(health_tom_tat)
        if health_model_tom_tat:
            dong.append(health_model_tom_tat)

    return _cat(dong)
