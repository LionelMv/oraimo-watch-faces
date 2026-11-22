#!/usr/bin/env bash
# robust_install.sh <bin> : retry connection, install, then verify via face list (reconnecting if needed)
BIN="$1"; MAC=54:88:00:00:9D:07; HERE="$(cd "$(dirname "$0")" && pwd)"
res=""
for try in 1 2 3 4 5; do
  bluetoothctl disconnect $MAC >/dev/null 2>&1; python3 -c "import time; time.sleep(8)"
  out=$(timeout 300 python3 -I "$HERE/send_face.py" "$BIN" 2>&1 | tr '\r' '\n')
  if echo "$out" | grep -q "END ok"; then
    res=$(echo "$out" | grep -oE "APPLIED|REJECTED by watch|timeout waiting for install result" | head -1); break
  fi
  echo "  (attempt $try: connection problem before/during transfer, retrying)" >&2
done
[ -z "$res" ] && { echo "RESULT: transfer never completed"; exit 3; }
python3 -c "import time; time.sleep(20)"
for try in 1 2 3 4 5; do
  bluetoothctl disconnect $MAC >/dev/null 2>&1; python3 -c "import time; time.sleep(8)"
  lst=$(timeout 90 python3 -I "$HERE/watch_cmd.py" 0200520000 2>&1 | grep "02 00 53" | tail -1)
  [ -n "$lst" ] && break
done
slot=$(echo "$lst" | grep -q "ff ff ff ff 21 00" && echo EMPTY || echo FILLED)
echo "RESULT: notice=[$res] slot=$slot"
