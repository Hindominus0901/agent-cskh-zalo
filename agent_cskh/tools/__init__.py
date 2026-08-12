from agent_cskh.config import Settings, get_settings
from agent_cskh.logging_setup import get_logger
from agent_cskh.tools.base import Tool, ToolRegistry
from agent_cskh.tools.bo_nho import BO_NHO_TOOLS
from agent_cskh.tools.don_hang import DON_HANG_TOOLS, co_du_lieu
from agent_cskh.tools.handoff import HANDOFF_TOOLS
from agent_cskh.tools.lead import LEAD_TOOLS
from agent_cskh.tools.skill import SKILL_TOOLS
from agent_cskh.tools.vision import VISION_TOOLS
from agent_cskh.tools.wiki import WIKI_TOOLS

__all__ = [
    "BO_NHO_TOOLS",
    "DON_HANG_TOOLS",
    "HANDOFF_TOOLS",
    "LEAD_TOOLS",
    "SKILL_TOOLS",
    "VISION_TOOLS",
    "WIKI_TOOLS",
    "Tool",
    "ToolRegistry",
]

log = get_logger(__name__)


def default_registry(settings: Settings | None = None) -> ToolRegistry:
    """Bo cong cu mac dinh cua mot bot CSKH.

    Sau cong cu, chia lam ba nhom:

      TRA KHO      doc_trang, tim_trang       — nen tang cua moi cau tra loi
      QUY TRINH    doc_skill                  — lam theo cach da dinh, khong tu nghi
      GHI NHAN     luu_lead, trich_bien_lai   — bien cuoc chat thanh du lieu
      NGUOI THAT   chuyen_nguoi_that          — biet luc phai dung lai
      BO NHO       ghi_nho, tim_hoi_thoai     — nho nguoi quen giua cac lan chat

    Chua co: Notion, Google Sheets, Gmail, Calendar, Drive, tim kiem web —
    tat ca deu can OAuth hoac API key ma chu bot phai tu cap.

    THEM CONG CU CUA RIENG BAN o day. Doc `tools/lead.py` truoc — no la vi du
    ngan nhat cua mot cong cu GHI ma van an toan cho nguoi la.
    """
    ds = [
        *WIKI_TOOLS,
        *SKILL_TOOLS,
        *HANDOFF_TOOLS,
        *LEAD_TOOLS,
        *VISION_TOOLS,
        *BO_NHO_TOOLS,
    ]

    # NHOM DON HANG chi duoc dang ky khi CO du lieu that (`data/don_hang.csv`).
    #
    # Khong co file thi model KHONG NHIN THAY ba cong cu nay, nen no khong bao
    # gio hua mot nang luc he thong khong co.
    #
    # Cach nguoc lai — dang ky roi tra "chua cau hinh" — te hon nhieu: model se
    # noi voi khach "de em tra don giup anh/chi" roi moi phat hien khong tra
    # duoc, va luc do khach da tin roi.
    s = settings or get_settings()
    if co_du_lieu(s):
        ds += DON_HANG_TOOLS
        log.info("bat_cong_cu_don_hang", so=len(DON_HANG_TOOLS))
    else:
        log.info("tat_cong_cu_don_hang", ly_do="chua co data/don_hang.csv")

    return ToolRegistry(ds)
