#!/bin/bash
# Install conscious: compile the overlay, place the files, load the daemon.
# Safe to re-run; it upgrades in place and keeps your config, log and queue.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${CONSCIOUS_HOME:-$HOME/.conscious}"
BIN="${CONSCIOUS_BIN:-$HOME/.local/bin}"
LABEL="com.conscious.daemon"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

[[ "$(uname)" == "Darwin" ]] || { echo "conscious is macOS only (it uses AppKit and launchd)."; exit 1; }
command -v swiftc >/dev/null || { echo "swiftc not found. Install Xcode command line tools: xcode-select --install"; exit 1; }
PY="$(command -v python3)" || { echo "python3 not found."; exit 1; }

mkdir -p "$HOME_DIR" "$BIN" "$HOME/Library/LaunchAgents"

echo "compiling the overlay..."
cp "$HERE/Overlay.swift" "$HERE/pause.html" "$HERE/spectral-light.ttf" "$HOME_DIR/"
swiftc -O "$HOME_DIR/Overlay.swift" -o "$HOME_DIR/overlay"

# The curated pool is the floor under generation; never overwrite a pool the
# user has since edited or extended.
[[ -f "$HOME_DIR/whispers.json" ]] || cp "$HERE/whispers.json" "$HOME_DIR/"

cp "$HERE/conscious.py" "$BIN/conscious"
chmod +x "$BIN/conscious"

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>$PY</string>
    <string>$BIN/conscious</string>
    <string>daemon</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>$BIN:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$HOME_DIR/conscious.log</string>
  <key>StandardErrorPath</key><string>$HOME_DIR/conscious.err</string>
</dict></plist>
PLIST_EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo
echo "installed."
echo "  test it now:   $BIN/conscious now"
echo "  settings:      $BIN/conscious config   (edit $HOME_DIR/config.json)"
echo "  how it's going: $BIN/conscious stats"
echo "  stop it:       launchctl unload $PLIST"
[[ ":$PATH:" == *":$BIN:"* ]] || echo "  note: $BIN is not on your PATH yet."
