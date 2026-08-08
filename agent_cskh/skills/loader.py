"""Nap skill tu `skills/<ten>/SKILL.md` va giu cong duyet.

Skill la BO NHO QUY TRINH: cach bot lam mot loai viec. File la nguon su that.

Khac kho tri thuc thế nào — hai thứ này hay bị lẫn:

    knowledge/wiki/   bot BIET gi   (bảng giá, chính sách, giờ mở cửa)
    skills/           bot LAM the nao (hỏi đủ 3 thông tin lead rồi mới chốt)

Trả lời sai vì thiếu kiến thức thì thêm trang wiki. Trả lời đúng nhưng làm sai
thứ tự thì sửa skill.

## Hai điều được giữ nguyên từ bản gốc, và lý do

**1. Chỉ mục lục vào prompt, không phải thân bài.**

`render_muc_luc()` chỉ đưa dòng `- **tên** — mô tả`. Thân bài nằm trên đĩa, bot
gọi `doc_skill` khi cần. Mười skill mà nhồi hết thân bài vào prompt là vài nghìn
token mỗi lượt cho thứ dùng tới một lần trong mười.

**2. Cổng duyệt.**

Skill người viết → `da_duyet` ngay: tự tay tạo file trong `skills/` là một hành
động có ý thức. Skill bot tự sinh → `nhap`, phải người duyệt.

Lý do ghi rõ trong `tools/bo_nho.py` của bản gốc: bot gặp một rào cản, nó viết
một skill mô tả cách vượt qua rào cản đó, rồi lần sau nó đọc chính skill đó như
hướng dẫn. Không có cổng duyệt thì ba lớp guard ở `harness/turn.py` chỉ còn là
một lời đề nghị.

Template này **chưa có** đường cho bot tự sinh skill. Cổng vẫn giữ, vì thêm
đường đó sau này là chuyện dễ, còn nhớ ra rằng cần cổng thì không.

## Lỗi đã sửa so với bản gốc

Bản gốc bảo model "đọc file `skills/<tên>/SKILL.md` bằng `doc_trang`" — nhưng
`doc_trang` chỉ quét thư mục kho tri thức, còn `skills/` là thư mục anh em. Model
thấy tên skill mà không bao giờ mở được thân bài.

Ở đây có công cụ `doc_skill` riêng. Tách hai công cụ chứ không gộp `skills/` vào
kho tri thức, vì hai thứ đó có mô hình quyền khác nhau: trang wiki phân quyền
theo thư mục `public/hocvien/internal`, còn skill thì không — skill là quy trình
nội bộ, khách không bao giờ đọc.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

from agent_cskh.config import Settings
from agent_cskh.logging_setup import get_logger

log = get_logger(__name__)

FRONTMATTER_SEP = "---"
# Than bai dai hon nguong nay thi cat. Mot skill la mot quy trinh, khong phai
# mot cuon so tay — dai hon the nay thi model doc luot va bo qua phan cuoi.
MAX_THAN_BAI = 6000


def tach_frontmatter(text: str) -> tuple[dict, str]:
    """Tra ve (meta, than_bai). Frontmatter hong thi coi nhu khong co."""
    if not text.lstrip().startswith(FRONTMATTER_SEP):
        return {}, text
    phan = text.lstrip().split(FRONTMATTER_SEP, 2)
    if len(phan) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(phan[1]) or {}
    except yaml.YAMLError as e:
        log.warning("frontmatter_skill_hong", error=str(e))
        return {}, phan[2]
    return (meta if isinstance(meta, dict) else {}), phan[2]


@dataclass(frozen=True, slots=True)
class Skill:
    ten: str
    mo_ta: str
    than_bai: str
    khi_nao: str = ""
    cong_cu: list[str] = field(default_factory=list)
    nguon: str = "nguoi"  # nguoi | tu_sinh
    trang_thai: str = "da_duyet"  # nhap | da_duyet | tat

    @property
    def duoc_nap(self) -> bool:
        return self.trang_thai == "da_duyet"

    def dong_muc_luc(self) -> str:
        # `khi_nao` la thu quyet dinh model co mo skill dung luc hay khong. Mot
        # mo ta hay ma khong noi KHI NAO dung thi skill nam do khong ai goi.
        if self.khi_nao:
            return f"- **{self.ten}** — {self.mo_ta} _(dùng khi: {self.khi_nao})_"
        return f"- **{self.ten}** — {self.mo_ta}"


def doc_skill(thu_muc: Path) -> Skill | None:
    """Doc `<thu_muc>/SKILL.md`. None neu khong co hoac khong doc duoc."""
    path = thu_muc / "SKILL.md"
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("khong_doc_duoc_skill", path=str(path), error=str(e))
        return None

    meta, than = tach_frontmatter(text)
    cong_cu = meta.get("cong_cu") or meta.get("tools") or []
    if not isinstance(cong_cu, list):
        cong_cu = []

    nguon = str(meta.get("nguon") or "nguoi").strip()
    trang_thai = str(meta.get("trang_thai") or "").strip()

    return Skill(
        ten=thu_muc.name,
        mo_ta=str(meta.get("mo_ta") or meta.get("description") or "").strip()
        or f"(thiếu mô tả — sửa frontmatter trong {path.name})",
        than_bai=than.strip()[:MAX_THAN_BAI],
        khi_nao=str(meta.get("khi_nao") or meta.get("when") or "").strip(),
        cong_cu=[str(c) for c in cong_cu],
        nguon=nguon if nguon in ("nguoi", "tu_sinh") else "nguoi",
        trang_thai=trang_thai if trang_thai in ("nhap", "da_duyet", "tat") else "",
    )


class KhoSkill:
    """Quet `skills/` va cho biet cai nao duoc nap."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._skill: dict[str, Skill] = {}

    @property
    def goc(self) -> Path:
        return self._s.skills_dir

    def nap(self) -> int:
        ra: dict[str, Skill] = {}
        if self.goc.is_dir():
            for thu_muc in sorted(p for p in self.goc.iterdir() if p.is_dir()):
                s = doc_skill(thu_muc)
                if s is None:
                    continue
                # File khong khai bao trang_thai thi suy tu NGUON. Nguoi viet thi
                # duoc nap ngay; bot tu sinh thi cho duyet.
                if not s.trang_thai:
                    s = replace(s, trang_thai="da_duyet" if s.nguon == "nguoi" else "nhap")
                ra[s.ten] = s
        self._skill = ra
        log.info("da_nap_skill", tong=len(ra), duoc_nap=sum(1 for s in ra.values() if s.duoc_nap))
        return len(ra)

    @property
    def tat_ca(self) -> list[Skill]:
        return sorted(self._skill.values(), key=lambda s: s.ten)

    def doc(self, ten: str) -> Skill | None:
        """Doc mot skill theo ten.

        Chi tra ve skill DA DUYET. Mot skill `nhap` khong duoc doc ra — biet no
        ton tai la mot nua duong toi viec dung no.

        Ten duoc chon tu danh sach da quet san, khong ghep duong dan tu dau vao
        model — nen khong ton tai duong nao de thoat thu muc.
        """
        s = self._skill.get(ten.strip())
        return s if s is not None and s.duoc_nap else None

    def duoc_nap(self) -> list[Skill]:
        return [s for s in self.tat_ca if s.duoc_nap]

    def cho_duyet(self) -> list[Skill]:
        return [s for s in self.tat_ca if s.trang_thai == "nhap"]

    def render_muc_luc(self) -> str:
        """Danh muc skill de nhet vao khoi prompt ON DINH.

        Chi liet ke skill DA DUYET.
        """
        ds = self.duoc_nap()
        if not ds:
            return ""
        dong = [
            "# Kỹ năng",
            "",
            "Quy trình bạn đã có sẵn cho một số loại việc. Gặp đúng tình huống thì "
            "gọi `doc_skill` để đọc các bước, rồi làm theo — đừng tự nghĩ lại quy trình.",
            "",
        ]
        dong += [s.dong_muc_luc() for s in ds]
        return "\n".join(dong)


__all__ = ["KhoSkill", "Skill", "doc_skill", "tach_frontmatter"]
