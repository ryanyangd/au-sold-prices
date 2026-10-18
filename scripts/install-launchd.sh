#!/bin/sh
# Install a per-user launchd job (macOS) that refreshes NSW data.
#
# launchd runs it at login/wake and hourly while the Mac is on; `ausold
# download-nsw` only fetches when a weekly refresh is due and backs off for 6h
# after a failed attempt, so a Mac that was off or offline catches up by itself.
#
# macOS blocks background jobs from reading ~/Documents (the process hangs on a
# privacy prompt), so the job uses a venv and data directory under
# ~/.local/share/ausold, and ./data in the repo becomes a symlink to it.
set -eu

REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/.local/share/ausold"
LABEL="com.ausold.download-nsw"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PYTHON="${PYTHON:-$REPO/.venv/bin/python}"
BIN="$APP_DIR/venv/bin/ausold"

mkdir -p "$APP_DIR/data" "$APP_DIR/logs" "$HOME/Library/LaunchAgents"
"$PYTHON" -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade "$REPO"

if [ ! -e "$REPO/data" ] && [ ! -L "$REPO/data" ]; then
  ln -s "$APP_DIR/data" "$REPO/data"
fi

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$BIN</string>
    <string>download-nsw</string>
    <string>--data-dir</string>
    <string>$APP_DIR/data</string>
  </array>
  <key>WorkingDirectory</key><string>$APP_DIR</string>
  <key>RunAtLoad</key><true/>
  <key>StartInterval</key><integer>3600</integer>
  <key>StandardOutPath</key><string>$APP_DIR/logs/download.log</string>
  <key>StandardErrorPath</key><string>$APP_DIR/logs/download.err.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed $PLIST (data: $APP_DIR/data, logs: $APP_DIR/logs)"
