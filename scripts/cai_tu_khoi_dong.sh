#!/usr/bin/env bash
# Cai bot tu chay moi khi dang nhap macOS (launchd).
# Ban song doi cua scripts/cai_tu_khoi_dong.ps1 (Task Scheduler tren Windows).
#
#   ./scripts/cai_tu_khoi_dong.sh          cai
#   ./scripts/cai_tu_khoi_dong.sh --go     go ra
#
# LUU Y VE ZALO: khong co `offset` trong getUpdates, nen tin nhan gui luc bot
# tat la MAT HAN. Tu khoi dong giup do phan nao, nhung may ngu (sleep) thi bot
# van dung. Chay that lau dai thi can VPS — xem docs/05-chuyen-len-vps.md.

set -euo pipefail

GOC="$(cd "$(dirname "$0")/.." && pwd)"
NHAN="com.agentcskh.bot"
PLIST="$HOME/Library/LaunchAgents/$NHAN.plist"

if [ "${1:-}" = "--go" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Da go. Bot khong con tu chay khi dang nhap."
    exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents" "$GOC/data/logs"

cat > "$PLIST" <<PLIST_END
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$NHAN</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$GOC/run.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$GOC</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$GOC/data/logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$GOC/data/logs/launchd.err.log</string>
</dict>
</plist>
PLIST_END

chmod +x "$GOC/run.sh"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "Da cai. Bot se tu chay moi khi dang nhap."
echo "  Nhat ky:  $GOC/data/logs/launchd.log"
echo "  Go ra:    ./scripts/cai_tu_khoi_dong.sh --go"
