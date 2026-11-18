#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Không tìm thấy python3. Hãy cài Python 3.10+ rồi chạy lại."
  exit 1
fi
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    print('Cần Python 3.10 trở lên. Phiên bản hiện tại:', sys.version.split()[0])
    raise SystemExit(1)
PY
exec python3 server.py "$@"
