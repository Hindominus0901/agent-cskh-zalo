"""Luong anh chuyen khoan — cho nguy hiem nhat ve tien bac trong ca he thong.

Bon lop chan viec bot tu xac nhan da nhan tien. Moi lop mot nhom test o day.
Neu bat ky test nao do, DUNG LAI: mot lan bot noi sai la mat tien that.
"""

from __future__ import annotations

import pytest

from agent_cskh.harness.turn import _MAU_XAC_NHAN_TIEN, MSG_BIEN_LAI_AN_TOAN
from agent_cskh.llm.base import ToolCall
from agent_cskh.wiki import strip_accents
from tests.conftest import make_event, run_one

ANH = "https://cdn.zalo.me/bienlai.jpg"


def bat(text: str) -> bool:
    phang = strip_accents(text)
    return any(m.search(phang) for m in _MAU_XAC_NHAN_TIEN)


class TestLop4_ChanCauTraLoi:
    """Lop chan cuoi: soi cau tra loi truoc khi gui."""

    @pytest.mark.parametrize(
        "cau",
        [
            "Dạ em đã nhận được tiền của anh rồi ạ.",
            "Em xác nhận thanh toán thành công nhé anh.",
            "Đơn hàng đã được thanh toán ạ.",
            "Tiền đã về tài khoản bên em rồi ạ.",
            "Chuyển khoản thành công nha anh.",
            "Anh đã thanh toán rồi nên em xử lý luôn ạ.",
            "da nhan duoc tien roi a",
        ],
    )
    def test_bat_duoc_cau_xac_nhan_tien(self, cau: str) -> None:
        assert bat(cau), f"KHONG bat duoc: {cau!r}"

    @pytest.mark.parametrize(
        "cau",
        [
            MSG_BIEN_LAI_AN_TOAN,
            "Dạ em đã nhận được ảnh chuyển khoản ạ.",
            "Em đã nhận được ảnh của anh, đang chuyển kế toán đối soát ạ.",
            "Anh vui lòng chuyển khoản theo thông tin dưới đây ạ.",
            "Bên em nhận thanh toán qua chuyển khoản ngân hàng ạ.",
            "Dạ em nghe anh ạ.",
        ],
    )
    def test_khong_bat_nham_cau_an_toan(self, cau: str) -> None:
        """Quan trong ngang viec bat dung: bat nham lam bot khong noi duoc gi."""
        assert not bat(cau), f"BAT NHAM cau an toan: {cau!r}"


class TestLop1_KhongCoCongCuXacNhan:
    def test_khong_ton_tai_cong_cu_danh_dau_da_thanh_toan(self) -> None:
        from agent_cskh.tools import default_registry

        ten = {t.name for t in default_registry().allowed("owner")}
        for cam in ("xac_nhan_thanh_toan", "danh_dau_da_tra", "confirm_payment"):
            assert cam not in ten

    def test_khong_co_ham_nao_ghi_verified_by(self) -> None:
        """verified_by chi nguoi that dien — grep ca codebase de chac chan."""
        import pathlib

        goc = pathlib.Path(__file__).resolve().parent.parent / "agent_cskh"
        for f in goc.rglob("*.py"):
            noi_dung = f.read_text(encoding="utf-8")
            assert "verified_by =" not in noi_dung, f"{f.name} ghi vao verified_by"
            assert "SET verified_by" not in noi_dung, f"{f.name} ghi vao verified_by"


class TestLop2_TuMoBanGiao:
    async def test_trich_bien_lai_tu_chuyen_nguoi_that(self, rig) -> None:  # noqa: F811
        rig["provider"].script = [
            [
                ToolCall(
                    id="c1",
                    name="trich_bien_lai",
                    args={
                        "so_tien": "1.500.000",
                        "thoi_gian": "05/08/2026 14:30",
                        "noi_dung": "MINH CK GOI STANDARD",
                        "ngan_hang": "Vietcombank",
                    },
                )
            ]
        ]
        await run_one(rig, make_event(None, kind="photo", photo_url=ANH))

        assert await rig["repo"].get_state("c1") == "HUMAN_PENDING"
        h = await rig["db"].fetch_one("SELECT reason, summary FROM handoffs")
        assert h["reason"] == "thanh_toan"
        assert "ĐỐI SOÁT" in h["summary"]

    async def test_ghi_dung_so_tien_va_trang_thai_cho_doi_soat(self, rig) -> None:  # noqa: F811
        rig["provider"].script = [
            [
                ToolCall(
                    id="c1",
                    name="trich_bien_lai",
                    args={"so_tien": "1.500.000", "noi_dung": "CK GOI STANDARD"},
                )
            ]
        ]
        await run_one(rig, make_event(None, kind="photo", photo_url=ANH))

        row = await rig["db"].fetch_one(
            "SELECT amount, memo, status, verified_by FROM payment_claims"
        )
        assert row["amount"] == 1500000
        assert row["status"] == "cho_doi_soat"
        assert row["verified_by"] is None

    async def test_khong_doc_duoc_gi_thi_khong_ghi(self, rig) -> None:  # noqa: F811
        rig["provider"].script = [[ToolCall(id="c1", name="trich_bien_lai", args={})]]
        await run_one(rig, make_event(None, kind="photo", photo_url=ANH))
        assert await rig["db"].fetch_val("SELECT count(*) FROM payment_claims") == 0

    async def test_khong_co_anh_thi_tu_choi(self, rig) -> None:  # noqa: F811
        rig["provider"].script = [
            [ToolCall(id="c1", name="trich_bien_lai", args={"so_tien": "1000000"})]
        ]
        await run_one(rig, make_event("em chuyển rồi nhé"))
        assert await rig["db"].fetch_val("SELECT count(*) FROM payment_claims") == 0


class TestAnhDinhKemVaoLuot:
    async def test_url_anh_duoc_gui_len_model(self, rig) -> None:  # noqa: F811
        await run_one(rig, make_event(None, kind="photo", photo_url=ANH))
        assert rig["provider"].calls[0][-1].image_urls == [ANH]

    async def test_cong_cu_bien_lai_co_trong_danh_sach(self, rig) -> None:  # noqa: F811
        await run_one(rig, make_event(None, kind="photo", photo_url=ANH))
        assert "trich_bien_lai" in rig["provider"].tools_seen[0]
