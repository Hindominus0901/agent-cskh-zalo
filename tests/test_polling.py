"""Vong lap polling — kiem tra no khong quay nong khi mat ket noi.

Bai hoc 07/08/2026: `get_updates()` nuot loi mang roi tra None NGAY LAP TUC. Truoc
khi sua, nhanh `body is None` khong ngu ma `continue` thang, nen long-poll 30 giay
— thu duy nhat giu nhip vong lap — bien mat. Ket qua: 5 giay mat DNS ngay
05/08/2026 sinh hang nghin dong `polling_loi_mang` trong log.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from agent_cskh.config import Settings
from agent_cskh.health import Health
from agent_cskh.transport import polling as polling_mod
from agent_cskh.transport.polling import BACKOFF_MIN, PollingTransport


class ClientGia:
    """Gia lap ZaloClient: tra ve lan luot cac gia tri da dinh san."""

    def __init__(self, ket_qua: list[Any]) -> None:
        self._ket_qua = list(ket_qua)
        self.so_lan_goi = 0

    async def delete_webhook(self) -> None:
        return None

    async def get_updates(self, timeout: int = 30) -> Any:
        self.so_lan_goi += 1
        if not self._ket_qua:
            raise asyncio.CancelledError
        return self._ket_qua.pop(0)


@pytest.fixture
def khong_ngu_that(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Ghi lai moi lan sleep thay vi ngu that — test chay trong mili giay."""
    da_ngu: list[float] = []

    async def sleep_gia(giay: float) -> None:
        da_ngu.append(giay)

    monkeypatch.setattr(polling_mod.asyncio, "sleep", sleep_gia)
    return da_ngu


async def _chay_het(transport: PollingTransport) -> None:
    await transport.start()
    with pytest.raises(asyncio.CancelledError):
        async for _ in transport.stream():
            pass


class TestKhongQuayNong:
    @pytest.mark.asyncio
    async def test_none_phai_ngu_truoc_khi_thu_lai(self, khong_ngu_that: list[float]) -> None:
        """Moi lan None phai keo theo dung mot lan ngu — khong duoc quay tron."""
        client = ClientGia([None, None, None])
        t = PollingTransport(Settings(), client, Health())  # type: ignore[arg-type]
        await _chay_het(t)

        assert len(khong_ngu_that) == 3
        assert all(g > 0 for g in khong_ngu_that)

    @pytest.mark.asyncio
    async def test_backoff_tang_dan(self, khong_ngu_that: list[float]) -> None:
        """Mat ket noi lau thi gian cho phai gian ra, khong dam Zalo deu dan."""
        client = ClientGia([None] * 4)
        t = PollingTransport(Settings(), client, Health())  # type: ignore[arg-type]
        await _chay_het(t)

        assert khong_ngu_that == sorted(khong_ngu_that)
        assert khong_ngu_that[-1] > khong_ngu_that[0]

    @pytest.mark.asyncio
    async def test_long_poll_rong_khong_ngu(self, khong_ngu_that: list[float]) -> None:
        """dict rong = 408 het gio cho. Chinh long-poll da giu nhip, ngu them la thua."""
        client = ClientGia([{}, {}, {}])
        t = PollingTransport(Settings(), client, Health())  # type: ignore[arg-type]
        await _chay_het(t)

        assert khong_ngu_that == []

    @pytest.mark.asyncio
    async def test_noi_lai_duoc_thi_reset_backoff(self, khong_ngu_that: list[float]) -> None:
        """Zalo song lai -> lan mat ket noi sau phai bat dau tu dau, khong keo dai."""
        client = ClientGia([None, None, {}, None])
        t = PollingTransport(Settings(), client, Health())  # type: ignore[arg-type]
        await _chay_het(t)

        assert khong_ngu_that[-1] == BACKOFF_MIN


class TestNhipTimVanDung:
    @pytest.mark.asyncio
    async def test_none_van_bi_dem_la_loi(self, khong_ngu_that: list[float]) -> None:
        """Sua chuyen ngu khong duoc lam mat kha nang phat hien mat ket noi."""
        health = Health()
        client = ClientGia([None, None, None])
        await _chay_het(PollingTransport(Settings(), client, health))  # type: ignore[arg-type]

        assert health.so_loi_lien_tiep == 3

    @pytest.mark.asyncio
    async def test_rong_van_duoc_coi_la_khoe(self, khong_ngu_that: list[float]) -> None:
        health = Health()
        client = ClientGia([None, {}, {}])
        await _chay_het(PollingTransport(Settings(), client, health))  # type: ignore[arg-type]

        assert health.so_loi_lien_tiep == 0
