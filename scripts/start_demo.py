#!/usr/bin/env python3
"""Khởi chạy bản demo tổng hợp trên localhost, không ghi đè dữ liệu."""
import argparse
from contextlib import closing
import os
from pathlib import Path
import secrets
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.env'
DB = ROOT / 'servicehub.db'
CREDS = ROOT / '.local-demo' / 'main-credentials.json'
MARKER = 'main_local_demo_v1'
HOSTING = (
    'RENDER', 'RENDER_SERVICE_ID', 'VERCEL', 'DYNO',
    'WEBSITE_SITE_NAME', 'RAILWAY_ENVIRONMENT', 'FLY_APP_NAME',
    'K_SERVICE', 'AWS_EXECUTION_ENV', 'KUBERNETES_SERVICE_HOST',
)
CONFIG_KEYS = (
    'SERVICEHUB_HOST', 'SERVICEHUB_PORT', 'SERVICEHUB_HOST_PORT',
    'SERVICEHUB_DB_PATH', 'SERVICEHUB_LOCAL_DEMO',
    'SERVICEHUB_ADMIN_EMAIL', 'SERVICEHUB_ADMIN_PASSWORD',
)


def create_config():
    # Chỉ tạo cấu hình khi chưa có dữ liệu hay thông tin đăng nhập.
    if ENV.exists():
        return
    if DB.exists() or CREDS.exists() or (ROOT / '.env.admin').exists():
        raise RuntimeError('Đã có dữ liệu/cấu hình Admin nhưng thiếu .env. Hãy khôi phục .env từ bản sao lưu.')
    if any(DB.with_name(DB.name + suffix).exists()
           for suffix in ('-wal', '-shm', '-journal')):
        raise RuntimeError('Phát hiện file phụ SQLite. Cần kiểm tra bản dữ liệu cũ trước.')
    password = secrets.token_urlsafe(24)
    content = (
        'SERVICEHUB_HOST=127.0.0.1\n'
        'SERVICEHUB_PORT=8001\n'
        'SERVICEHUB_LOCAL_DEMO=1\n'
        'SERVICEHUB_ADMIN_EMAIL=admin@servicehub.local\n'
        f'SERVICEHUB_ADMIN_PASSWORD={password}\n'
    )
    # O_EXCL ngăn ghi đè .env nếu tiến trình khác vừa tạo file.
    fd = os.open(ENV, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(content)


def prepare():
    if any(os.environ.get(key) for key in HOSTING) or os.environ.get(
        'SERVICEHUB_ENV', '').strip().lower() not in ('', 'local', 'development', 'local-demo'):
        raise RuntimeError('Không chạy demo trong môi trường hosting hoặc production.')
    if any(key in os.environ for key in CONFIG_KEYS):
        raise RuntimeError('Có biến SERVICEHUB_* ghi đè cấu hình. Mở terminal local sạch hoặc bỏ các biến ghi đè trước.')
    create_config()
    sys.path.insert(0, str(ROOT))
    import server

    if (server.HOST != '127.0.0.1' or server.DB_PATH != DB.resolve()
            or os.environ.get('SERVICEHUB_LOCAL_DEMO') != '1'):
        raise RuntimeError('Demo cần HOST=127.0.0.1, DB=servicehub.db và LOCAL_DEMO=1. Không tự sửa .env hiện có; nếu cần hãy dùng bản clone sạch.')
    server.validate_demo_environment()
    if not server.ADMIN_EMAIL or len(server.ADMIN_PASSWORD) < 16:
        raise RuntimeError('Cấu hình Admin demo chưa hợp lệ. Không tự đổi mật khẩu đã có.')
    if DB.exists():
        # Chỉ dùng lại database đã được đánh dấu demo tích hợp.
        with closing(sqlite3.connect(DB.as_uri() + '?mode=ro', uri=True)) as conn:
            has_settings = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_settings'"
            ).fetchone()
            if not has_settings or not conn.execute(
                'SELECT 1 FROM app_settings WHERE key=?', (MARKER,)
            ).fetchone():
                raise RuntimeError('Database hiện có không phải demo tích hợp. Giữ nguyên dữ liệu; hãy dùng một bản clone sạch.')
            admin = conn.execute(
                'SELECT password_hash, is_admin, login_enabled FROM users WHERE email=?',
                (server.ADMIN_EMAIL,)
            ).fetchone()
            if not admin or not admin[1] or not admin[2] or not server.verify_password(
                server.ADMIN_PASSWORD, admin[0]
            ):
                raise RuntimeError('Cấu hình Admin không khớp database. Hãy khôi phục cấu hình đúng; không tự đổi mật khẩu.')
        if not CREDS.is_file():
            raise RuntimeError('Thiếu file tài khoản demo. Hãy khôi phục từ bản sao lưu; database được giữ nguyên.')
    elif CREDS.exists():
        raise RuntimeError('Có file tài khoản demo nhưng thiếu database. Hãy khôi phục bản sao lưu.')
    return server


def initialize(server):
    # Tái sử dụng schema, migration và dữ liệu demo của ứng dụng thật.
    server.seed()
    server.seed_local_demo()
    if os.name != 'nt':
        for path in (ENV, DB, CREDS):
            path.chmod(0o600)
    print('ServiceHub demo đã sẵn sàng.', flush=True)
    print('Admin: mở .env trên máy của bạn.', flush=True)
    print('Customer/Owner: mở .local-demo/main-credentials.json.', flush=True)
    print('Không gửi các file chứa mật khẩu lên GitHub hoặc chat.', flush=True)


def main():
    if sys.version_info < (3, 10):
        print('Cần Python 3.10 trở lên.', file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, help='Chọn cổng khác nếu cổng mặc định bận.')
    parser.add_argument('--setup-only', action='store_true', help='Chỉ kiểm tra/khởi tạo, không mở server.')
    args = parser.parse_args()
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error('Cổng phải từ 1 đến 65535.')
    old_umask = os.umask(0o077)
    try:
        server = prepare()
        port = args.port if args.port is not None else server.PORT
        if not 1 <= port <= 65535:
            raise RuntimeError('Cổng trong .env không hợp lệ.')
        if args.setup_only:
            initialize(server)
        else:
            # Dùng chính Handler của server.py; không tạo API giả.
            with server.ThreadingHTTPServer(('127.0.0.1', port), server.Handler) as httpd:
                initialize(server)
                print(f'Mở http://127.0.0.1:{port} (Ctrl+C để dừng).', flush=True)
                httpd.serve_forever()
        return 0
    except KeyboardInterrupt:
        print('\nĐã dừng ServiceHub.')
        return 0
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        print(f'Lỗi khởi chạy demo: {exc}', file=sys.stderr)
        print('Nếu cổng đang bận, dừng server cũ hoặc dùng --port 8002.', file=sys.stderr)
        return 1
    finally:
        os.umask(old_umask)


if __name__ == '__main__':
    raise SystemExit(main())
