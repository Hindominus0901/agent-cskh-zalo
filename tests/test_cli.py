"""CLI — cong vao duy nhat cua nguoi dung.

Moi lenh o day la thu HOC VIEN GO DAU TIEN. Hong o day thi khong con buoc thu hai:
ho nhan mot traceback Python lam ket qua dau tien va bo cuoc.
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent


class TestConsoleKhongDauCungChay:
    """Bug do duoc 11/08/2026 khi dua repo cho mot agent la chay thu.

    MOI chuoi nguoi dung thay deu la tieng Viet co dau. Console Windows mac dinh
    la cp1252, khong ma hoa duoc "ế"/"ữ"/"ộ" — nen `check` va `chat` chet bang
    UnicodeEncodeError TRUOC KHI in noi mot dong.

    Khong ai phat hien som hon vi console cua may dang phat trien da duoc dat
    UTF-8 tu truoc. Dung kieu loi chi hien ra o may nguoi khac — nen phai co test
    ep bang ma, khong duoc tin vao console dang chay.
    """

    def _chay(self, *lenh: str, bang_ma: str) -> subprocess.CompletedProcess:
        import os

        env = {**os.environ, "PYTHONIOENCODING": bang_ma}
        return subprocess.run(
            [sys.executable, "-m", "agent_cskh", *lenh],
            cwd=GOC,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

    def test_check_khong_chet_tren_cp1252(self) -> None:
        kq = self._chay("check", bang_ma="cp1252")
        assert "UnicodeEncodeError" not in kq.stderr, kq.stderr[-800:]
        assert "Traceback" not in kq.stderr, kq.stderr[-800:]
        # Van phai in ra bang ket qua, khong phai im lang.
        assert "[ok]" in kq.stdout or "[THIẾU]" in kq.stdout

    def test_check_khong_chet_tren_ascii(self) -> None:
        """Bang ma hep nhat co the gap. `errors="replace"` phai do duoc."""
        kq = self._chay("check", bang_ma="ascii")
        assert "UnicodeEncodeError" not in kq.stderr, kq.stderr[-800:]

    def test_lenh_khong_biet_khong_chet(self) -> None:
        kq = self._chay("linh-tinh", bang_ma="cp1252")
        assert "Traceback" not in kq.stderr


class TestBatUtf8AnToan:
    def test_khong_chet_khi_stdout_la_StringIO(self, monkeypatch) -> None:
        """Trong test, stdout thuong bi thay bang StringIO — khong co
        `reconfigure`. Ham nay phai nuot loi do chu khong duoc nem ra."""
        from agent_cskh.cli import _bat_utf8

        monkeypatch.setattr(sys, "stdout", io.StringIO())
        monkeypatch.setattr(sys, "stderr", io.StringIO())
        _bat_utf8()  # khong duoc nem exception
