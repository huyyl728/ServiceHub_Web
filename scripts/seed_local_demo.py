#!/usr/bin/env python3
"""Opt-in local presentation data. Passwords are generated/stored outside the repo."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_demo import MARKER, demo_database, require_local_demo

ACCOUNTS = (
    ('customer01', 'Khách demo An', 'Customer'),
    ('customer02', 'Khách demo Bình', 'Customer'),
    ('customer03', 'Khách demo Chi', 'Customer'),
    ('owner01', 'Chủ demo Sân Thể Thao', 'Owner'),
    ('owner02', 'Chủ demo Mộc Hair', 'Owner'),
    ('owner03', 'Chủ demo Bếp Việt', 'Owner'),
)
BUSINESSES = (
    ('owner01', 'Sân Thể Thao (Demo Local)', 'Thể thao', 'Khu A, địa chỉ minh họa',
     'demo-sport.svg', (('Thuê sân 60 phút', 180000, 60), ('Thuê sân 90 phút', 250000, 90))),
    ('owner02', 'Mộc Hair (Demo Local)', 'Làm đẹp', 'Khu B, địa chỉ minh họa',
     'demo-salon.svg', (('Cắt tóc và tạo kiểu', 120000, 45), ('Gội đầu thư giãn', 80000, 30))),
    ('owner03', 'Bếp Việt (Demo Local)', 'Nhà hàng', 'Khu C, địa chỉ minh họa',
     'demo-restaurant.svg', (('Đặt bàn 2 người', 0, 90), ('Bữa tối minh họa', 220000, 90))),
)
DESCRIPTION = 'Dữ liệu hư cấu chỉ dùng thuyết trình local; không phải cơ sở hoặc giao dịch thật.'


def email_for(username):
    return f'{username}@demo.servicehub.test'


def read_credentials(path):
    if path.is_symlink() or path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Credentials must be a regular file outside this repository, never a symlink.')
    if not path.exists():
        payload = {'version': 1, 'accounts': [
            {'username': username, 'email': email_for(username), 'role': role,
             'password': secrets.token_urlsafe(18)} for username, _, role in ACCOUNTS]}
        # Exclusive creation prevents overwriting another credential file.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    if not path.is_file() or (os.name == 'posix' and path.stat().st_mode & 0o077):
        raise RuntimeError('Credentials must be private: chmod 600 the credentials file.')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        rows = payload['accounts']
        if payload['version'] != 1 or len(rows) != len(ACCOUNTS):
            raise ValueError
        passwords = {}
        for username, _, role in ACCOUNTS:
            matches = [row for row in rows if row['username'] == username]
            if len(matches) != 1:
                raise ValueError
            row = matches[0]
            password = row['password']
            if (row['email'] != email_for(username) or row['role'] != role
                    or not isinstance(password, str) or len(password) < 16):
                raise ValueError
            passwords[username] = password
        if len(set(passwords.values())) != len(ACCOUNTS):
            raise ValueError
        return passwords
    except (KeyError, TypeError, ValueError):
        raise RuntimeError('Invalid credentials: require exactly six matching accounts with distinct passwords of at least 16 characters.') from None


def verify_existing(connection, manifest, passwords, server):
    """Fail closed on collisions/drift; never reset passwords, balances or ownership."""
    try:
        for username, _, role in ACCOUNTS:
            row = connection.execute('SELECT * FROM users WHERE id=?', (manifest['users'][username],)).fetchone()
            if (not row or row['email'] != email_for(username) or row['is_admin']
                    or not row['login_enabled'] or not server.verify_password(passwords[username], row['password_hash'])):
                raise ValueError
            if role == 'Customer' and connection.execute(
                    'SELECT 1 FROM businesses WHERE owner_id=?', (row['id'],)).fetchone():
                raise ValueError
        for username, *_ in BUSINESSES:
            bid = manifest['businesses'][username]
            row = connection.execute('SELECT owner_id FROM businesses WHERE id=?', (bid,)).fetchone()
            if not row or row['owner_id'] != manifest['users'][username]:
                raise ValueError
            application = connection.execute(
                "SELECT 1 FROM business_applications WHERE id=? AND user_id=? AND business_id=? AND status='approved'",
                (manifest['applications'][username], row['owner_id'], bid)).fetchone()
            if not application:
                raise ValueError
            for sid in manifest['services'][username]:
                if not connection.execute('SELECT 1 FROM services WHERE id=? AND business_id=?', (sid, bid)).fetchone():
                    raise ValueError
    except (KeyError, TypeError, ValueError):
        raise RuntimeError('Demo data or credentials differ from the original seed. No changes made; restore the matching private credentials/database.') from None


def seed_demo(server, passwords):
    require_local_demo(os.environ, server.HOST, server.DB_PATH, ROOT)
    # This is a dedicated demo database: initialize the current schema, not old test fixtures.
    with closing(server.connect()) as connection, connection:
        tables = [r[0] for r in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        marked = 'app_settings' in tables and connection.execute(
            'SELECT 1 FROM app_settings WHERE key=?', (MARKER,)).fetchone()
        if not marked and any(connection.execute(
                'SELECT 1 FROM "' + table.replace('"', '""') + '" LIMIT 1').fetchone() for table in tables):
            raise RuntimeError('Refusing to seed an unmarked, nonempty database. Use a fresh dedicated local demo database.')
        connection.executescript(server.SCHEMA)
        connection.execute('BEGIN IMMEDIATE')
        row = connection.execute('SELECT value FROM app_settings WHERE key=?', (MARKER,)).fetchone()
        if row:
            verify_existing(connection, json.loads(row['value']), passwords, server)
            return False
        # Never adopt an existing database, even when someone renamed it to the demo path.
        tables = [r[0] for r in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        if any(connection.execute('SELECT 1 FROM "' + table.replace('"', '""') + '" LIMIT 1').fetchone()
               for table in tables):
            raise RuntimeError('Refusing to seed an unmarked, nonempty database. Use a fresh dedicated local demo database.')
        manifest = {'users': {}, 'businesses': {}, 'applications': {}, 'services': {}}
        for username, name, role in ACCOUNTS:
            uid = connection.execute(
                'INSERT INTO users(name,email,password_hash,is_admin,login_enabled) VALUES(?,?,?,0,1)',
                (name, email_for(username), server.hash_password(passwords[username]))).lastrowid
            manifest['users'][username] = uid
            balance = 1000000 if role == 'Customer' else 0
            connection.execute('INSERT INTO wallets(user_id,balance) VALUES(?,?)', (uid, balance))
            if balance:
                connection.execute(
                    'INSERT INTO wallet_transactions(user_id,amount,kind,description,reference) VALUES(?,?,?,?,?)',
                    (uid, balance, 'demo_credit', 'Số dư hư cấu cho thuyết trình local', 'local-demo:' + username))
        for username, name, category, address, image, services in BUSINESSES:
            uid = manifest['users'][username]
            image_path = '/static/images/' + image
            bid = connection.execute(
                "INSERT INTO businesses(name,category,address,phone,description,owner_id,status,banner_path) VALUES(?,?,?,?,?,?,'active',?)",
                (name, category, address, '0000000000', DESCRIPTION, uid, image_path)).lastrowid
            manifest['businesses'][username] = bid
            manifest['applications'][username] = connection.execute(
                "INSERT INTO business_applications(user_id,business_name,category,address,phone,description,status,review_note,business_id) VALUES(?,?,?,?,?,?,'approved',?,?)",
                (uid, name, category, address, '0000000000', DESCRIPTION, 'Hồ sơ demo local được seed sẵn.', bid)).lastrowid
            manifest['services'][username] = []
            for service_name, price, duration in services:
                sid = connection.execute(
                    'INSERT INTO services(business_id,name,description,price,duration_minutes,category,image_path) VALUES(?,?,?,?,?,?,?)',
                    (bid, service_name + ' (Demo)', DESCRIPTION, price, duration, category, image_path)).lastrowid
                manifest['services'][username].append(sid)
            connection.execute('INSERT INTO membership_programs(business_id,name,description,benefits) VALUES(?,?,?,?)',
                               (bid, name + ' Member', DESCRIPTION, 'Quyền lợi minh họa cho thành viên.'))
        connection.execute('INSERT INTO app_settings(key,value) VALUES(?,?)', (MARKER, json.dumps(manifest)))
        verify_existing(connection, manifest, passwords, server)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-demo', action='store_true', help='Explicitly authorize a disposable local demo')
    parser.add_argument('--credentials-file', type=Path, required=True, help='Private JSON file OUTSIDE the repository; generated if missing')
    parser.add_argument('--serve', action='store_true', help='Start the demo at the loopback address after seeding')
    args = parser.parse_args()
    if not args.local_demo:
        parser.error('--local-demo is required; normal server startup never creates demo accounts')
    os.environ['SERVICEHUB_LOCAL_DEMO'] = '1'
    database = demo_database(ROOT)
    # Reject a production DB override instead of silently redirecting or modifying it.
    selected = Path(os.environ.get('SERVICEHUB_DB_PATH', str(database))).expanduser()
    require_local_demo(os.environ, os.environ.get('SERVICEHUB_HOST', '127.0.0.1'), selected, ROOT)
    os.environ['SERVICEHUB_DB_PATH'] = str(database)
    import server
    # server loads .env; validate again so hosted/public/bank/admin settings cannot slip through.
    require_local_demo(os.environ, server.HOST, server.DB_PATH, ROOT)
    passwords = read_credentials(args.credentials_file.expanduser().absolute())
    created = seed_demo(server, passwords)
    server.seed()  # Apply the same startup checks/migrations and legacy-login retirement.
    print(('Created' if created else 'Verified existing') + ': 3 Customer, 3 Owner, 3 businesses, 6 services.')
    print('Passwords remain in the private credentials file; nothing secret is printed.')
    if args.serve:
        print(f'Local demo: http://{server.HOST}:{server.PORT}', flush=True)
        with server.ThreadingHTTPServer((server.HOST, server.PORT), server.Handler) as http:
            try:
                http.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, sqlite3.Error, ValueError) as error:
        print(f'Local demo refused: {error}', file=sys.stderr)
        sys.exit(1)
