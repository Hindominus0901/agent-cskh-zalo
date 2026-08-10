"""Kho tri thuc dang LLM Wiki (phuong phap Karpathy).

Khong vector database, khong embedding. Chi Markdown lien ket, nguoi doc duoc,
nguoi sua duoc. Chinh Claude lam viec khop ngu nghia khi doc index — o quy mo
vai tram trang thi model tu lam duoc, mien phi va khong do tre.

Gist goc: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

Ba muc hien thi, do THU MUC quyet dinh:
  wiki/public/   — ai cung doc duoc
  wiki/hocvien/  — hoc vien + nhan vien + chu
  wiki/internal/ — chi nhan vien va chu

AN TOAN — hai quy tac khong duoc pha:
  1. Quyen doc do THU MUC quyet dinh, khong do noi dung file khai bao. Nguoi la
     khong bao gio thay trang internal, ke ca ten trang trong index.
  2. Bot khong bao gio ghep duong dan tu dau vao nguoi dung. No chi chon `slug`
     trong danh sach da quet san — nen khong ton tai duong nao de thoat thu muc.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

from agent_cskh.config import Settings
from agent_cskh.logging_setup import get_logger

log = get_logger(__name__)

Visibility = Literal["public", "hocvien", "internal"]

# Thu tu quet quyet dinh ben nao thang khi trung slug: cang ve sau cang kin.
# Trung slug thi giu ban QUET TRUOC (cong khai hon) — de mot trang noi bo dat
# nham ten khong the am tham thay the trang cong khai dang phuc vu khach.
MUC_HIEN_THI: tuple[Visibility, ...] = ("public", "hocvien", "internal")

FRONTMATTER_SEP = "---"
MAX_PAGE_CHARS = 12_000
SNIPPET_CHARS = 400

# HU TU — bo khoi truy van truoc khi cham diem.
#
# Vi sao can: diem cham theo so lan khop, va moi lan khop o tieu de/tom tat/
# tu_khoa an 5 diem. Nhung tu nhu "khong", "co", "cho" nam rai trong tu_khoa va
# tieu de cua GAN NHU MOI trang, nen chung mot minh du de lat nguoc thu tu.
#
# Do duoc ngay 10/08/2026 tren mot kho 5 trang: cau "chỗ mình có ship không"
# tra ve trang "Chỗ ngồi" thay vi "Giao hàng" — vi "cho" + "khong" an 15 diem
# cho trang cho-ngoi, con "ship" chi an 5 cho trang dung. Cau "quán có bán bánh
# ngọt không" (khong co trong kho) le ra phai chuyen nguoi that thi lai dua ra
# ba lua chon vo quan, cung vi ba hu tu do.
#
# Luu y ve dau: danh sach nay o dang DA BO DAU, nen mot muc bat nhieu tu that.
# "cho" bat ca "cho" (gioi tu) lan "chỗ" (danh tu) — chap nhan duoc, vi bo mot
# tu mo ho khoi truy van chi lam ket qua HEP lai, ma hep thi roi ve phia
# "khong biet" -> chuyen nguoi that. Do la huong sai an toan.
#
# Truy van chi toan hu tu se con rong -> `search_scored` tra [] -> bot noi that
# la chua nam duoc. Dung nhu mong muon.
HU_TU = frozenset(
    """
    a o oi u um da vang da_vang
    co khong con chua duoc dang se da van cung deu
    la cua va voi cho den tu ve tai boi bang theo
    nay do kia ay cai chiec con_nay
    minh ban em anh chi ho toi tao may
    the thi ma nhe nha nhi day roi luon a_ha
    rat qua hoi kha lam nhieu it
    xin cam_on giup gium ho
    """.split()
)


def strip_accents(text: str) -> str:
    """Bo dau tieng Viet de khop duoc khi khach go khong dau ("bao gia")."""
    nfkd = unicodedata.normalize("NFD", text.lower())
    out = "".join(c for c in nfkd if not unicodedata.combining(c))
    return out.replace("đ", "d")


@dataclass(frozen=True, slots=True)
class WikiPage:
    slug: str
    visibility: Visibility
    title: str
    summary: str
    body: str
    tags: list[str] = field(default_factory=list)
    updated: str = ""
    sources: list[str] = field(default_factory=list)
    # CACH KHACH HAY HOI, nguyen van. Khac han `tags` (phan loai cho nguoi doc).
    #
    # Day la truong quan trong nhat cua che do `tra_cuu`. Tim kiem o day la regex
    # bo dau, khong phai embedding — nen no khop "gia" nhung truot "mac khong",
    # "bao nhieu xu", "co dat khong". Ba dong `tu_khoa` bu duoc dung cho ho hong
    # do, va no cung giup che do `ai` chon dung trang nhanh hon.
    #
    #   tu_khoa: ["bao nhieu tien", "gia", "chi phi", "mac khong", "co dat khong"]
    tu_khoa: list[str] = field(default_factory=list)

    @property
    def haystack(self) -> str:
        """Chuoi da bo dau de tim kiem."""
        return strip_accents(
            f"{self.slug} {self.title} {self.summary} "
            f"{' '.join(self.tags)} {' '.join(self.tu_khoa)} {self.body}"
        )

    def index_line(self) -> str:
        # Nhan chi de model biet nen nhac trang nay voi ai. Viec CHAN thi da lam
        # o `visible()` — trang ngoai quyen khong bao gio den duoc day.
        mark = {"public": "", "hocvien": " [học viên]", "internal": " [nội bộ]"}[self.visibility]
        return f"- [[{self.slug}]]{mark} — {self.summary}"

    def render(self) -> str:
        head = f"# {self.title}"
        if self.updated:
            head += f"\n*Cập nhật: {self.updated}*"
        body = self.body[:MAX_PAGE_CHARS]
        if len(self.body) > MAX_PAGE_CHARS:
            body += "\n\n[...trang quá dài, đã cắt bớt]"
        return f"{head}\n\n{body}"

    def snippet(self, query_norm: str) -> str:
        """Doan quanh vi tri khop dau tien — de bot uoc luong trang co dung khong."""
        pos = self.haystack.find(query_norm) if query_norm else -1
        if pos < 0:
            return self.summary
        start = max(0, pos - SNIPPET_CHARS // 2)
        return self.body[start : start + SNIPPET_CHARS].strip().replace("\n", " ")


def _parse(path: Path, visibility: Visibility) -> WikiPage | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("khong_doc_duoc_trang_wiki", path=str(path), error=str(e))
        return None

    meta: dict = {}
    body = text
    if text.lstrip().startswith(FRONTMATTER_SEP):
        parts = text.lstrip().split(FRONTMATTER_SEP, 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError as e:
                log.warning("frontmatter_hong", path=path.name, error=str(e))
            body = parts[2]

    if not isinstance(meta, dict):
        meta = {}

    slug = path.stem
    summary = str(meta.get("summary") or "").strip()
    if not summary:
        # Khong co summary thi trang nay gan nhu vo hinh voi bot — canh bao to.
        log.warning("trang_thieu_summary", slug=slug, path=str(path))
        summary = str(meta.get("title") or slug)

    tags = meta.get("tags") or []
    sources = meta.get("sources") or []
    tu_khoa = meta.get("tu_khoa") or meta.get("keywords") or []
    return WikiPage(
        slug=slug,
        visibility=visibility,
        title=str(meta.get("title") or slug),
        summary=summary,
        body=body.strip(),
        tags=[str(t) for t in tags] if isinstance(tags, list) else [],
        updated=str(meta.get("updated") or ""),
        sources=[str(s) for s in sources] if isinstance(sources, list) else [],
        tu_khoa=[str(k) for k in tu_khoa] if isinstance(tu_khoa, list) else [],
    )


class WikiStore:
    """Quet thu muc wiki/ va phuc vu truy van, co loc quyen."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._pages: dict[str, WikiPage] = {}

    @property
    def root(self) -> Path:
        return self._s.knowledge_dir / "wiki"

    def reload(self) -> int:
        """Quet lai toan bo. Goi luc khoi dong va khi co lenh /nap."""
        pages: dict[str, WikiPage] = {}
        for vis in MUC_HIEN_THI:
            folder = self.root / vis
            if not folder.is_dir():
                continue
            for path in sorted(folder.rglob("*.md")):
                page = _parse(path, vis)  # type: ignore[arg-type]
                if page is None:
                    continue
                if page.slug in pages:
                    log.warning(
                        "trung_slug",
                        slug=page.slug,
                        giu=pages[page.slug].visibility,
                        bo=vis,
                    )
                    continue
                pages[page.slug] = page
        self._pages = pages
        log.info(
            "da_nap_wiki",
            tong=len(pages),
            **{v: sum(1 for p in pages.values() if p.visibility == v) for v in MUC_HIEN_THI},
        )
        return len(pages)

    # ---------- truy van ----------
    def visible(self, scope: frozenset[str]) -> list[WikiPage]:
        return [p for p in self._pages.values() if p.visibility in scope]

    def render_index(self, scope: frozenset[str]) -> str:
        """Ban do tong, nhet vao phan dau system prompt duoc cache.

        Nguoi la chi thay trang public — ke ca TEN trang internal cung khong lo.
        """
        pages = sorted(self.visible(scope), key=lambda p: (p.visibility, p.slug))
        if not pages:
            return ""
        lines = [
            "# Kho tri thức",
            "",
            "Danh mục các trang bạn tra cứu được. Dùng công cụ `doc_trang` để đọc "
            "toàn văn một trang trước khi trả lời — không trả lời chỉ dựa vào dòng "
            "tóm tắt ở đây.",
            "",
        ]
        lines += [p.index_line() for p in pages]
        return "\n".join(lines)

    def read(self, slug: str, scope: frozenset[str]) -> WikiPage | None:
        """Doc mot trang. Tra None neu khong ton tai HOAC ngoai quyen.

        Khong phan biet hai truong hop — nguoi la khong duoc biet trang internal
        co ton tai hay khong.
        """
        page = self._pages.get(slug.strip().removesuffix(".md"))
        if page is None or page.visibility not in scope:
            return None
        return page

    def search(self, query: str, scope: frozenset[str], limit: int = 5) -> list[WikiPage]:
        """Tim theo tu khoa, khong dau. Uu tien tieu de va tom tat hon than bai."""
        return [p for _, p in self.search_scored(query, scope, limit)]

    def search_scored(
        self, query: str, scope: frozenset[str], limit: int = 5
    ) -> list[tuple[int, WikiPage]]:
        """Nhu `search()` nhung TRA VE CA DIEM, sap giam dan.

        Che do `ai` khong can diem: model tu doc snippet roi tu quyet dinh trang
        nao dung. Che do `tra_cuu` thi khong co ai quyet dinh ho ca — no phai tu
        biet luc nao minh chac, luc nao nen hoi lai, va luc nao phai chuyen nguoi
        that. Con so nay la thu duy nhat de phan biet ba truong hop do.

        Thang diem: moi lan khop o TIEU DE / TOM TAT / TAG / TU_KHOA an 5 diem,
        khop trong than bai an 1. Khop nguyen cum o phan dau cong them 20 — day
        la tin hieu manh nhat, vi khach go dung ca cum thi gan nhu chac chan ho
        dang hoi dung trang do.
        """
        q = strip_accents(query).strip()
        if not q:
            return []
        terms = [t for t in q.split() if len(t) > 1 and t not in HU_TU]
        if not terms:
            # Ca cau chi toan hu tu ("co khong a", "the a"). Khong doan bua —
            # tra rong de ben goi noi that la chua nam duoc.
            return []

        # Khop theo RANH GIOI TU, khong phai chuoi con. Tieng Viet viet roi am tiet
        # nen chuoi con sai rat nhieu: "gia" se khop vao giua "thoi gian".
        patterns = [re.compile(rf"\b{re.escape(t)}\b") for t in terms]

        scored: list[tuple[int, WikiPage]] = []
        for page in self.visible(scope):
            head = strip_accents(
                f"{page.slug} {page.title} {page.summary} "
                f"{' '.join(page.tags)} {' '.join(page.tu_khoa)}"
            )
            body = strip_accents(page.body)
            score = 0
            for pat in patterns:
                score += len(pat.findall(head)) * 5
                score += len(pat.findall(body))
            if q in head:
                score += 20

            # CUM `tu_khoa` KHOP NGUYEN VAN — tin hieu manh nhat trong ca ham.
            #
            # Chu doanh nghiep khai "mac khong" nghia la ho da noi thang: khach
            # hoi kieu do la hoi trang nay. Cham tung tu le thi cum do tan ra —
            # "mac" an 5 diem, con "khong" bi loc mat vi la hu tu — va tong lai
            # khong du nguong, nen bot chuyen nguoi that cho mot cau ma chinh
            # chu da day no tra loi.
            #
            # Do duoc 10/08/2026: "cái này mắc không" roi xuong "khong biet" du
            # trang bang gia khai dung cum "mac khong".
            #
            # Doi chieu voi `q` CHUA LOC hu tu, vi cum khai bao thuong chua chung
            # ("mac khong", "co dat khong", "hong thi sao").
            for cum in page.tu_khoa:
                c = strip_accents(cum).strip()
                if len(c) > 2 and c in q:
                    score += 25
                    break

            if score:
                scored.append((score, page))

        scored.sort(key=lambda x: (-x[0], x[1].slug))
        return scored[:limit]

    def stats(self, scope: frozenset[str]) -> dict[str, int]:
        pages = self.visible(scope)
        return {
            "trang": len(pages),
            "ky_tu": sum(len(p.body) for p in pages),
        }
