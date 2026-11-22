#!/usr/bin/env bash
# Install a watch-face .bin on the oraimo Watch 5R Pro from this laptop.
# Usage: tools/install_face.sh designs/<name>/<name>.bin
# Turn the PHONE's Bluetooth off first (the watch talks to one device at a time).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="$(realpath "$1")"
"$HERE/../venv/bin/python" -I "$HERE/verify.py" "$BIN"
if command -v adb >/dev/null && adb get-state >/dev/null 2>&1; then
  if adb shell dumpsys bluetooth_manager 2>/dev/null | grep -qE "^\s+state: ON"; then
    echo "Phone Bluetooth is ON — turn it off first, then re-run." >&2; exit 1
  fi
fi
bluetoothctl power on >/dev/null
cd "$HERE" && python3 -I send_face.py "$BIN"
