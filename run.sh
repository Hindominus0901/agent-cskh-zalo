#!/usr/bin/env bash
# Khoi dong bot tren macOS / Linux. Ban song doi cua run.ps1.
#
#   ./run.sh              chay binh thuong, tu khoi dong lai neu bot chet
#   ./run.sh --once       chay mot lan, khong tu khoi dong lai (de xem loi)
#   ./run.sh --check      chi kiem tra cau hinh roi thoat
#
# Lan dau chay can cap quyen: chmod +x run.sh

set -euo pipefail
cd "$(dirname "$0")"

tim_uv() {
    if command -v uv >/dev/null 2>&1; then
        command -v uv
        return
    fi
    for p in "$HOME/.local/bin/uv" "/opt/homebrew/bin/uv" "/usr/local/bin/uv"; do
        if [ -x "$p" ]; then
            echo "$p"
            return
        fi
    done
    echo "Khong tim thay uv. Cai bang: brew install uv" >&2
    exit 1
}

UV="$(tim_uv)"

case "${1:-}" in
    --check)
        exec "$UV" run agent-cskh check
        ;;
    --once)
        exec "$UV" run agent-cskh chay
        ;;
esac

# Vong tu khoi dong lai. Bot da tu chiu duoc loi mang va loi Zalo ben trong;
# vong nay chi de cuu nhung truong hop tien trinh chet han (het bo nho, may ngu
# day, Python crash).
lan=0
while true; do
    lan=$((lan + 1))
    echo "[$(date +%H:%M:%S)] Khoi dong bot (lan $lan)..."
    set +e
    "$UV" run agent-cskh chay
    code=$?
    set -e

    if [ "$code" -eq 0 ]; then
        echo "[$(date +%H:%M:%S)] Bot dung binh thuong."
        break
    fi

    # Cho lau dan de khong quay vong dot CPU khi loi lap lai (5s -> toi da 5 phut).
    mu=$((lan - 1))
    [ "$mu" -gt 6 ] && mu=6
    cho=$((5 * (2 ** mu)))
    [ "$cho" -gt 300 ] && cho=300
    echo "[$(date +%H:%M:%S)] Bot thoat voi ma $code. Chay lai sau $cho giay."
    sleep "$cho"
done
