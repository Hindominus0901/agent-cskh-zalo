"""Che do `tra_cuu` — bot tra loi bang kho tri thuc, KHONG dung LLM.

Day la duong di mac dinh cua template. Ly do khong phai ky thuat ma la thuc te:
phan lon nguoi vua nhan repo nay chua tra tien API, va ho can thay bot chay
TRUOC khi quyet dinh co tra hay khong.

Chay duoc vi `WikiStore.search()` tim bang REGEX BO DAU chu khong phai embedding
— khong goi mang, khong ton token, khong can key nao.

  Khach hoi -> tim trong kho -> phan dinh theo diem -> mot trong ba duong:
     chac        tra loi tu trang khop nhat
     hoi_lai     dua 2-3 lua chon danh so, khach nhan so
     khong_biet  noi that, chuyen nguoi that, GHI VAO `thieu_trang`

DUONG THU BA LA DUONG QUAN TRONG NHAT. Moi lan bot khong biet, cau hoi nguyen
van duoc ghi lai; bao cao 20h gom chung lai va noi "hom nay 6 cau khong tra loi
duoc, 3 nguoi hoi ve bao hanh". Chu bot viet them mot trang, va hom sau bot tra
loi duoc. Do la ca vong lap hoc cua he thong nay, va o che do `tra_cuu` no chay
RO HON che do `ai` — vi moi cau truot deu la mot lo hong that trong kho, khong
phai mot lan model doan hut.

GIOI HAN, noi thang de khong ai ky vong nham:
  - Khong hieu ngu canh nhieu luot. "Cai do bao nhieu tien?" sau mot cau khac
    thi no khong biet "cai do" la gi.
  - Khong suy luan, khong tong hop tu hai trang.
  - Khong dung duoc cong cu hay skill.

  - QUAN TRONG NHAT: che do nay KHONG DOC `persona.md`. Nghia la moi luat
    "phai chuyen nguoi that khi..." ma chu doanh nghiep khai trong persona deu
    KHONG CO HIEU LUC o day. No chi biet mot luat duy nhat: khong tim thay
    trang thi chuyen nguoi.

    Do duoc 10/08/2026: mot quan ca phe khai trong persona "khach hoi hom nay
    con cho khong thi phai chuyen nguoi that". Che do `tra_cuu` van tra ve
    trang "Cho ngoi va khong gian" — dung ve tra cuu (quan co 40 cho), sai ve
    nghiep vu (hom nay con hay het thi no khong biet).

    Cach song chung: viet thang cau do vao than bai trang lien quan. O vi du
    tren, trang "Cho ngoi" nen co mot dong "Con cho hay khong thi anh/chi nhan
    truc tiep de ben em xem giup a." Trang la thu duy nhat che do nay doc, nen
    moi rang buoc phai nam trong trang.

Doi `CHE_DO=ai` trong `.env` de co nhung thu do. Cung mot kho tri thuc.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_cskh.logging_setup import get_logger
from agent_cskh.tra_cuu.nguong import TOI_DA_LUA_CHON, phan_dinh
from agent_cskh.wiki import WikiPage, WikiStore

log = get_logger(__name__)

# Bao nhieu ky tu than bai duoc tra ve. Zalo cat o 2000, chua phan dau va phan
# duoi, nen giu 1400 cho an toan.
MAX_THAN_BAI = 1400

MSG_KHONG_BIET = (
    "Dạ phần này em chưa nắm chắc nên chưa dám trả lời anh/chị ạ. "
    "Em chuyển sang anh/chị phụ trách để trả lời chính xác cho mình nhé."
)

# Cau chao. Bat rieng vi neu de no di qua tim kiem thi "chao em" se khop lung
# tung vao bat ky trang nao co chu "chao".
_CHAO = {
    "hi",
    "hello",
    "alo",
    "chao",
    "chao em",
    "chao shop",
    "chao ban",
    "xin chao",
    "co ai khong",
    "co ai o day khong",
    "ib",
    "ạ",
}


@dataclass(slots=True)
class TraLoi:
    """Ket qua mot luot. `can_nguoi_that` va `cau_hoi_thieu` la thu ben goi phai
    hanh dong tiep — dinh tuyen khong tu goi CSDL hay Zalo, de test duoc no ma
    khong dung gi ca."""

    text: str
    can_nguoi_that: bool = False
    # Khac None nghia la phai ghi vao bang `thieu_trang`. Nguyen van cau hoi,
    # khong tom tat — chu bot can biet khach dung TU GI de dat ten trang moi.
    cau_hoi_thieu: str | None = None
    # Cac slug dang cho khach chon, theo dung thu tu danh so.
    dang_cho_chon: list[str] | None = None


class DinhTuyenTraCuu:
    """Mot the hien cho moi cuoc tro chuyen — no giu trang thai "dang cho chon"."""

    def __init__(self, wiki: WikiStore, *, ten_don_vi: str = "bên em") -> None:
        self._wiki = wiki
        self._ten = ten_don_vi
        # chat_id -> danh sach slug dang cho khach go so
        self._cho_chon: dict[str, list[str]] = {}

    def tra_loi(self, cau_hoi: str, *, chat_id: str, scope: frozenset[str]) -> TraLoi:
        cau_hoi = (cau_hoi or "").strip()
        if not cau_hoi:
            return TraLoi(text=self._chao())

        # 1. Khach vua go mot con so de chon o luot truoc?
        chon = self._doc_lua_chon(cau_hoi, chat_id, scope)
        if chon is not None:
            return chon

        # 2. Chao hoi — tra loi thang, khong tim kiem.
        if self._la_chao(cau_hoi):
            return TraLoi(text=self._chao())

        # 3. Tim trong kho.
        ket_qua = self._wiki.search_scored(cau_hoi, scope, limit=TOI_DA_LUA_CHON)
        quyet_dinh = phan_dinh(ket_qua)

        if quyet_dinh == "chac":
            return TraLoi(text=self._dung_tra_loi(ket_qua[0][1]))

        if quyet_dinh == "phong_doan":
            trang = ket_qua[0][1]
            return TraLoi(
                text=f"Dạ có phải anh/chị đang hỏi về **{trang.title}** không ạ:\n\n"
                + self._dung_tra_loi(trang)
            )

        if quyet_dinh == "hoi_lai":
            return self._hoi_lai(ket_qua, chat_id)

        log.info("tra_cuu_khong_biet", chat_id=chat_id[:8], cau_hoi=cau_hoi[:120])
        return TraLoi(
            text=MSG_KHONG_BIET,
            can_nguoi_that=True,
            cau_hoi_thieu=cau_hoi[:500],
        )

    # ---------- ben trong ----------
    def _chao(self) -> str:
        return (
            f"Dạ em chào anh/chị ạ. Em là trợ lý của {self._ten}, "
            "anh/chị cần hỏi gì em hỗ trợ ngay ạ."
        )

    def _la_chao(self, cau: str) -> bool:
        from agent_cskh.wiki import strip_accents

        return strip_accents(cau.lower()).strip(" .!?,") in _CHAO

    def _dung_tra_loi(self, trang: WikiPage) -> str:
        than = trang.body.strip()
        if len(than) > MAX_THAN_BAI:
            than = than[:MAX_THAN_BAI].rsplit("\n", 1)[0].rstrip() + "\n\n[...]"
        return f"{than}\n\n— Nếu chưa đúng ý, anh/chị nhắn lại giúp em ạ."

    def _hoi_lai(self, ket_qua: list[tuple[int, WikiPage]], chat_id: str) -> TraLoi:
        """Zalo khong co nut bam, nen lua chon phai la so de khach go lai."""
        trang = [p for _, p in ket_qua][:TOI_DA_LUA_CHON]
        dong = ["Dạ anh/chị đang hỏi về ý nào ạ:", ""]
        dong += [f"{i}. {p.title}" for i, p in enumerate(trang, 1)]
        dong += ["", "Anh/chị nhắn số giúp em, hoặc hỏi rõ hơn ạ."]

        slugs = [p.slug for p in trang]
        self._cho_chon[chat_id] = slugs
        return TraLoi(text="\n".join(dong), dang_cho_chon=slugs)

    def _doc_lua_chon(self, cau: str, chat_id: str, scope: frozenset[str]) -> TraLoi | None:
        """Khach go "2" ngay sau mot cau hoi lai thi mo dung trang thu hai.

        Chi nhan khi tin nhan CHI CO mot con so. "2 cai gia bao nhieu" khong phai
        lua chon — do la cau hoi moi, va doan nham no thanh lua chon thi bot tra
        ve mot trang chang lien quan.
        """
        slugs = self._cho_chon.get(chat_id)
        if not slugs:
            return None
        goc = cau.strip().rstrip(".")
        if not goc.isdigit():
            # Khach hoi tiep chuyen khac — bo trang thai cho, xu ly nhu cau moi.
            self._cho_chon.pop(chat_id, None)
            return None

        so = int(goc)
        self._cho_chon.pop(chat_id, None)
        if not 1 <= so <= len(slugs):
            return TraLoi(text=f"Dạ em chỉ có {len(slugs)} mục thôi ạ, anh/chị chọn lại giúp em.")

        trang = self._wiki.read(slugs[so - 1], scope)
        if trang is None:
            return TraLoi(text=MSG_KHONG_BIET, can_nguoi_that=True)
        return TraLoi(text=self._dung_tra_loi(trang))
