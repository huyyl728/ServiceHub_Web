#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Không tìm thấy python3. Hãy cài Python 3.10+ rồi chạy lại."
  exit 1
fi
exec python3 server.py "$@"
