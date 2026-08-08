"""Buffer hoi thoai — dung dinh dang tin nhan cho LLM."""

from __future__ import annotations

from agent_cskh.memory.buffer import to_messages
from agent_cskh.store.repo import StoredMessage


def m(direction: str, text: str | None, kind: str = "text") -> StoredMessage:
    return StoredMessage(direction=direction, kind=kind, text=text, created_at="")  # type: ignore[arg-type]


class TestToMessages:
    def test_anh_xa_vai_tro(self) -> None:
        out = to_messages([m("in", "chào em"), m("out", "dạ em nghe")])
        assert [x.role for x in out] == ["user", "assistant"]
        assert out[0].text == "chào em"

    def test_gop_tin_lien_tiep_cung_vai(self) -> None:
        out = to_messages([m("in", "chào"), m("in", "em ơi"), m("out", "dạ")])
        assert len(out) == 3 - 1
        assert out[0].text == "chào\nem ơi"

    def test_mo_ta_anh_khi_khong_co_chu(self) -> None:
        out = to_messages([m("in", None, kind="photo")])
        assert "anh" in out[0].text.lower()

    def test_bo_qua_tin_khong_co_noi_dung(self) -> None:
        assert to_messages([m("in", None, kind="unsupported")]) == []

    def test_lich_su_rong(self) -> None:
        assert to_messages([]) == []
