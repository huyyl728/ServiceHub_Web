#!/usr/bin/env python3
"""Explicit, localhost-only ServiceHub demo (6 users + private Admin).

Run: python3 scripts/local_demo.py
     python3 scripts/local_demo.py --setup-only

No payment accounts, real database, remote hosting, or shared public credentials.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / '.local-demo'
DB = STORE / 'servicehub-demo.db'
CREDS = STORE / 'credentials.json'
MARKER = 'local_demo_booking_only_v1'

ADMIN = ('admin-demo@demo.servicehub.test', 'Admin Demo', 'admin')
CUSTOMERS = [
    (f'customer{i:02d}@demo.servicehub.test', f'Khách hàng Demo {i}', 'customer')
    for i in range(1, 4)
]
OWNERS = [
    (f'owner{i:02d}@demo.servicehub.test', f'Chủ cơ sở Demo {i}', 'owner')
    for i in range(1, 4)
]
USERS = [ADMIN, *CUSTOMERS, *OWNERS]
BUSINESSES = [
    ('Sân Thể Thao (Demo)', 'Thể thao', 'Cầu Giấy, Hà Nội', '/static/images/demo-sport.svg', [
        ('Đặt sân 60 phút', 180000, 60), ('Đặt sân 90 phút', 250000, 90)]),
    ('Mộc Hair (Demo)', 'Làm đẹp', 'Đống Đa, Hà Nội', '/static/images/demo-salon.svg', [
        ('Cắt tóc cơ bản', 80000, 40), ('Gội đầu thư giãn', 90000, 45)]),
    ('Bếp Việt (Demo)', 'Nhà hàng', 'Ba Đình, Hà Nội', '/static/images/demo-restaurant.svg', [
        ('Đặt bàn hai người', 0, 90), ('Đặt bàn gia đình', 0, 120)]),
]

def private_json_write(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    except Exception:
        path.unlink(missing_ok=True)
        raise

def checked_credential_file():
    if DB.exists() != CREDS.exists():
        raise RuntimeError('Demo SQLite and credentials mismatch: do not overwrite. Back up .local-demo and investigate.')
    first_run = not DB.exists()
    if first_run:
        credentials = {
            'notice': 'LOCAL ONLY. Never commit, share or reuse these passwords elsewhere.',
            'users': [dict(email=email, name=name, role=role, password=secrets.token_urlsafe(24))
                      for email, name, role in USERS]
        }
        private_json_write(CREDS, credentials)
    else:
        if CREDS.stat().st_mode & 0o077:
            raise RuntimeError('Demo credentials are accessible to others; restrict file permissions before continuing.')
        credentials = json.loads(CREDS.read_text(encoding='utf-8'))
        by_email = {row.get('email'): row for row in credentials.get('users', [])}
        if set(by_email) != {x[0] for x in USERS} or not all(
            isinstance(by_email[e].get('password'), str) and len(by_email[e]['password']) >= 16
            for e, _, _ in USERS
        ):
            raise RuntimeError('Demo credentials do not match the expected seven accounts.')
    return first_run, credentials

def prepare(port):
    if any(os.environ.get(x) for x in ('RENDER', 'RENDER_SERVICE_ID', 'VERCEL', 'DYNO', 'WEBSITE_SITE_NAME')):
        raise RuntimeError('Local demo refuses public/hosting environments.')
    if not 1 <= port <= 65535:
        raise RuntimeError('Invalid port')
    STORE.mkdir(mode=0o700, exist_ok=True)
    STORE.chmod(0o700)
    first_run, credentials = checked_credential_file()
    admin = credentials['users'][0]
    os.environ.update({
        'SERVICEHUB_ENV': 'local-demo',
        'SERVICEHUB_HOST': '127.0.0.1',
        'SERVICEHUB_PORT': str(port),
        'SERVICEHUB_DB_PATH': str(DB),
        'SERVICEHUB_ADMIN_EMAIL': admin['email'],
        'SERVICEHUB_ADMIN_PASSWORD': admin['password'],
    })
    sys.path.insert(0, str(ROOT))
    import server
    # The original production DB path is never used by this script.
    if server.DB_PATH != DB or server.HOST != '127.0.0.1':
        raise RuntimeError('Local demo database/host guard failed.')
    server.seed()
    if first_run:
        with server.connect() as c:
            if c.execute('SELECT COUNT(*) FROM users').fetchone()[0] != 1:
                raise RuntimeError('Refusing to seed unexpected user data.')
            ids = {}
            for item in credentials['users'][1:]:
                cur = c.execute(
                    'INSERT INTO users(name,email,password_hash,is_admin) VALUES(?,?,?,0)',
                    (item['name'], item['email'], server.hash_password(item['password']))
                )
                ids[item['email']] = cur.lastrowid
            admin_id = c.execute('SELECT id FROM users WHERE email=?', (admin['email'],)).fetchone()['id']
            for owner, (business_name, category, address, banner, services) in zip(OWNERS, BUSINESSES):
                owner_id = ids[owner[0]]
                bid = c.execute(
                    'INSERT INTO businesses(name,category,address,phone,description,owner_id,status,banner_path) '
                    'VALUES(?,?,?,?,?,?,?,?)',
                    (business_name, category, address, '0000000000',
                     'Dữ liệu demo local, không phải cơ sở thật.', owner_id, 'active', banner)
                ).lastrowid
                c.execute(
                    'INSERT INTO business_applications(user_id,business_name,category,address,phone,description,status,reviewed_by,business_id) '
                    'VALUES(?,?,?,?,?,?,?,?,?)',
                    (owner_id, business_name, category, address, '0000000000',
                     'Dữ liệu demo local.', 'approved', admin_id, bid)
                )
                for service_name, price, duration in services:
                    c.execute(
                        'INSERT INTO services(business_id,name,description,price,duration_minutes,category,image_path) '
                        'VALUES(?,?,?,?,?,?,?)',
                        (bid, service_name, 'Dịch vụ demo.', price, duration, category, banner)
                    )
            c.execute('INSERT INTO app_settings(key,value) VALUES(?,?)', (MARKER, 'local-only'))
            c.commit()
        DB.chmod(0o600)
    else:
        with server.connect() as c:
            if not c.execute('SELECT 1 FROM app_settings WHERE key=?', (MARKER,)).fetchone():
                raise RuntimeError('Database is not marked as local demo. Refusing to continue.')
            for item in credentials['users']:
                row = c.execute('SELECT password_hash,login_enabled FROM users WHERE email=?', (item['email'],)).fetchone()
                if not row or not row['login_enabled'] or not server.verify_password(item['password'], row['password_hash']):
                    raise RuntimeError('Demo account differs from credentials. Refusing to overwrite.')
    print('Local demo:', 'created' if first_run else 'reused')
    print('Accounts: 3 Customer + 3 Owner + 1 Admin; 3 businesses and 6 services')
    print('Private credentials:', CREDS)
    print('Production database untouched. Demo is localhost-only.')
    return server

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8001)
    parser.add_argument('--setup-only', action='store_true', help='Create/check data but do not start server')
    args = parser.parse_args()
    old_umask = os.umask(0o077)
    try:
        server = prepare(args.port)
        if not args.setup_only:
            print(f'Open http://127.0.0.1:{args.port} ; Ctrl+C to stop.', flush=True)
            server.ThreadingHTTPServer(('127.0.0.1', args.port), server.Handler).serve_forever()
    except (RuntimeError, OSError, ValueError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        raise SystemExit(1)
    finally:
        os.umask(old_umask)

if __name__ == '__main__':
    main()
