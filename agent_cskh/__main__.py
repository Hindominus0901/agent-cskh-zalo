"""Diem vao cho `python -m agent_cskh`.

Chi la mot lop mong tro ve `cli.py`. Docker dung duong nay (`CMD ["python",
"-m", "agent_cskh"]`) vi trong container thi entrypoint `agent-cskh` co the
khong nam tren PATH; con nguoi thi dung `agent-cskh` cho ngan.

KHONG viet logic o day. Ban goc tung co mot ham `_check()` rieng tai file nay,
song song voi `agent-cskh check` — hai duong kiem tra khac nhau cho cung mot
viec, va chung se lech nhau ngay lan sua dau tien.

    python -m agent_cskh            chay bot (mac dinh, dung cho Docker)
    python -m agent_cskh check      giong `agent-cskh check`
    python -m agent_cskh chat       giong `agent-cskh chat`
"""

from __future__ import annotations

import sys

from agent_cskh.cli import main

if __name__ == "__main__":
    # Khong co lenh nao thi CHAY BOT — khac voi `agent-cskh` tran (in tro giup).
    # Docker goi duong nay va no phai chay duoc ngay, khong in tro giup roi thoat.
    if len(sys.argv) == 1:
        sys.argv.append("chay")
    sys.exit(main())
