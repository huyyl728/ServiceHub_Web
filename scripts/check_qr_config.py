#!/usr/bin/env python3
"""Check VietQR settings locally without printing the receiving account number."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server  # reads .env next to server.py without starting an HTTP server

print('ServiceHub | VietQR configuration check')
print('Project folder:', ROOT)
print('.env found:', 'yes' if (ROOT / '.env').is_file() else 'no')
print('Python listening port:', server.PORT)
print('VietQR status:', 'READY' if server.BANK_QR_CONFIGURED else 'NOT READY')
print('BIN valid:', 'yes' if server.BANK_BIN.isascii() and server.BANK_BIN.isdigit() and len(server.BANK_BIN)==6 else 'no')
print('Account present:', 'yes' if server.BANK_ACCOUNT else 'no')
print('Account holder name present:', 'yes' if server.BANK_NAME else 'no')
if server.BANK_QR_ISSUES:
    for issue in server.BANK_QR_ISSUES:
        print('Fix:', issue)
print('Note: QR creation never verifies money received.')
