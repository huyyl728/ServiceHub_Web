"""Real startup tests: isolated demo, private credentials and fail-closed guards."""
import json
import os
from pathlib import Path
import shutil
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

SOURCE = Path(__file__).resolve().parents[1]
HOSTING = ('RENDER', 'RENDER_SERVICE_ID', 'VERCEL', 'DYNO', 'WEBSITE_SITE_NAME',
           'RAILWAY_ENVIRONMENT', 'FLY_APP_NAME', 'K_SERVICE', 'AWS_EXECUTION_ENV',
           'KUBERNETES_SERVICE_HOST', 'APP_ENV', 'NODE_ENV', 'ENVIRONMENT')


class LocalDemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='servicehub-local-demo-')
        self.root = Path(self.tmp.name)
        for name in ('server.py', 'schema.sql'):
            shutil.copyfile(SOURCE / name, self.root / name)
        shutil.copytree(SOURCE / 'static', self.root / 'static', ignore=shutil.ignore_patterns('uploads'))
        self.store = self.root / '.local-demo'
        self.db = self.store / 'servicehub-demo.db'
        self.creds = self.store / 'credentials.json'
        self.process = None
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('SERVICEHUB_') and k not in HOSTING}
        self.env['NO_PROXY'] = '127.0.0.1,localhost'
        self.log = self.root / 'startup.log'
        # Existing real DB content must survive every demo startup byte-for-byte.
        self.real_db = self.root / 'servicehub.db'
        with sqlite3.connect(self.real_db) as c:
            c.execute('CREATE TABLE keep_me(value TEXT)')
            c.execute("INSERT INTO keep_me VALUES('existing teammate data')")
        self.original_db = self.real_db.read_bytes()

    def tearDown(self):
        self.stop()
        self.assertEqual(self.real_db.read_bytes(), self.original_db)
        self.tmp.cleanup()

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None

    def start(self, args=('--local-demo',), overrides=None):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        self.base = f'http://127.0.0.1:{port}'
        with self.log.open('w') as output:
            self.process = subprocess.Popen([sys.executable, 'server.py', *args, '--port', str(port)],
                                            cwd=self.root, env=self.env | (overrides or {}),
                                            stdout=output, stderr=output)
        for _ in range(150):
            if self.process.poll() is not None:
                self.fail('Startup failed: ' + self.log.read_text())
            try:
                if self.request('/api/health')[0] == 200:
                    return
            except (OSError, TimeoutError):
                time.sleep(.05)
        self.fail('Demo startup timed out')

    def request(self, path, method='GET', data=None, token=None, headers=None):
        hdr = {'Content-Type': 'application/json'} | (headers or {})
        if token:
            hdr['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request(self.base + path, method=method, headers=hdr,
                                     data=None if data is None else json.dumps(data).encode())
        try:
            response = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw = response.read()
            return response.status, json.loads(raw) if 'application/json' in response.headers.get('Content-Type', '') else raw

    def rejected(self, overrides=None, args=('--local-demo',)):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        result = subprocess.run([sys.executable, 'server.py', *args], cwd=self.root,
                                env=self.env | {'SERVICEHUB_PORT': str(port)} | (overrides or {}),
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('ServiceHub running at', result.stderr)
        return result

    def users(self):
        return json.loads(self.creds.read_text())['users']

    def test_seven_accounts_roles_catalog_and_booking_flow(self):
        real_password = secrets.token_urlsafe(24)
        self.start(overrides={'SERVICEHUB_ADMIN_EMAIL': 'real-admin@example.com',
                              'SERVICEHUB_ADMIN_PASSWORD': real_password})
        users = self.users()
        self.assertEqual([u['role'] for u in users].count('admin'), 1)
        self.assertEqual([u['role'] for u in users].count('customer'), 3)
        self.assertEqual([u['role'] for u in users].count('owner'), 3)
        self.assertEqual(len({u['password'] for u in users}), 7)
        if os.name == 'posix':
            self.assertEqual(self.store.stat().st_mode & 0o777, 0o700)
            for path in (self.db, self.creds):
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        tokens = {}
        businesses = {}
        for u in users:
            self.assertGreaterEqual(len(u['password']), 32)
            self.assertNotIn(u['password'], self.log.read_text())
            code, body = self.request('/api/auth/login', 'POST', {'email': u['email'], 'password': u['password']})
            self.assertEqual(code, 200)
            token = body['data']['token']
            tokens[u['email']] = token
            self.assertEqual(self.request('/api/admin/stats', token=token)[0], 200 if u['role'] == 'admin' else 403)
            me = self.request('/api/me', token=token)[1]['data']
            self.assertEqual(len(me['businesses']), 1 if u['role'] == 'owner' else 0)
            if u['role'] == 'owner':
                businesses[u['email']] = me['businesses'][0]['id']
        code, catalog = self.request('/api/services')
        self.assertEqual(code, 200)
        self.assertEqual(len(catalog['data']), 6)
        customer = next(u for u in users if u['role'] == 'customer')
        owners = [u for u in users if u['role'] == 'owner']
        owner = owners[0]
        bid = businesses[owner['email']]
        service = next(s for s in catalog['data'] if s['business_id'] == bid)
        from datetime import date, timedelta
        code, booking = self.request('/api/bookings', 'POST', {'service_id': service['id'],
                                     'date': (date.today() + timedelta(days=1)).isoformat(), 'start_time': '10:00'},
                                     tokens[customer['email']])
        self.assertEqual(code, 201)
        route = f'/api/owner/bookings/{bid}/confirm'
        data = {'booking_id': booking['data']['id']}
        self.assertEqual(self.request(route, 'POST', data, tokens[owners[1]['email']])[0], 403)
        self.assertEqual(self.request(route, 'POST', data, tokens[owner['email']])[0], 200)
        self.assertEqual(self.request('/api/auth/login', 'POST', {'email': 'real-admin@example.com',
                         'password': real_password})[0], 401)

    def test_restart_preserves_credentials_sessions_and_edited_data(self):
        self.start()
        before = self.creds.read_bytes()
        u = self.users()[0]
        token = self.request('/api/auth/login', 'POST', u)[1]['data']['token']
        self.stop()
        with sqlite3.connect(self.db) as c:
            c.execute("UPDATE businesses SET name='Owner edit',status='suspended' WHERE id=1")
            hashes = c.execute('SELECT password_hash FROM users ORDER BY id').fetchall()
        # PR #43 format is preserved; list order is not significant.
        credentials = json.loads(before)
        credentials['users'].reverse()
        self.creds.write_text(json.dumps(credentials))
        before = self.creds.read_bytes()
        self.start()
        self.assertEqual(before, self.creds.read_bytes())
        self.assertEqual(self.request('/api/admin/stats', token=token)[0], 200)
        with sqlite3.connect(self.db) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0], 7)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM services').fetchone()[0], 6)
            self.assertEqual(c.execute('SELECT name,status FROM businesses WHERE id=1').fetchone(), ('Owner edit', 'suspended'))
            self.assertEqual(c.execute('SELECT password_hash FROM users ORDER BY id').fetchall(), hashes)

    def test_env_opt_in_and_explicit_normal_override(self):
        (self.root / '.env').write_text('SERVICEHUB_ENV=local-demo\nSERVICEHUB_PORT=8001\n')
        self.start(args=())
        self.assertEqual(len(self.users()), 7)
        self.stop()
        self.start(args=(), overrides={'SERVICEHUB_ENV': 'production', 'SERVICEHUB_DB_PATH': str(self.root / 'normal.db')})
        with sqlite3.connect(self.root / 'normal.db') as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0], 0)

    def test_hosting_public_binding_production_and_db_overrides_refused(self):
        cases = [{k: 'production' if k in ('APP_ENV', 'NODE_ENV', 'ENVIRONMENT') else '1'} for k in HOSTING]
        cases += [{'SERVICEHUB_ENV': mode} for mode in ('production', 'prod', 'staging')]
        cases += [{'SERVICEHUB_HOST': host} for host in ('0.0.0.0', '192.168.1.10', '::')]
        cases += [{'SERVICEHUB_DB_PATH': str(self.real_db)}, {'SERVICEHUB_PORT': '0'}, {'SERVICEHUB_PORT': '65536'}]
        for env in cases:
            with self.subTest(env=env):
                self.rejected(env)
                self.assertFalse(self.store.exists())

    def test_busy_port_does_not_seed_or_claim_started(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); sock.listen()
            port = sock.getsockname()[1]
            result = self.rejected(args=('--local-demo', '--port', str(port)))
            self.assertIn('--port', result.stderr)
        self.assertFalse(self.store.exists())

    def test_web_never_serves_credentials_and_rejects_proxy_or_foreign_origin(self):
        self.start()
        for path in ('/.local-demo/credentials.json', '/static/../.local-demo/credentials.json',
                     '/static/%2e%2e/.local-demo/credentials.json', '/.local-demo/servicehub-demo.db'):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        for headers in ({'Host': 'public.example'}, {'X-Forwarded-For': '127.0.0.1'},
                        {'Forwarded': 'for=127.0.0.1'}, {'Origin': 'https://public.example'}, {'Origin': 'null'}):
            self.assertEqual(self.request('/api/health', headers=headers)[0], 403)
        self.assertEqual(self.request('/api/health', headers={'Origin': self.base})[0], 200)
        for path in ('/', '/terms', '/static/js/app.js', '/static/js/api.js'):
            self.assertEqual(self.request(path)[0], 200)

    def test_partial_state_or_unmarked_db_refused_without_repair(self):
        self.start(); self.stop()
        before = self.creds.read_bytes()
        with sqlite3.connect(self.db) as c:
            c.execute("DELETE FROM app_settings WHERE key='local_demo_booking_only_v1'")
        db_before = self.db.read_bytes()
        self.rejected()
        self.assertEqual(self.db.read_bytes(), db_before)
        self.assertEqual(self.creds.read_bytes(), before)
        self.creds.rename(self.store / 'saved-credentials.json')
        self.rejected()
        self.assertEqual(self.db.read_bytes(), db_before)
        self.assertFalse(self.creds.exists())

    def test_disabled_or_demoted_demo_admin_never_restored(self):
        self.start(); self.stop()
        for column in ('is_admin', 'login_enabled'):
            with sqlite3.connect(self.db) as c:
                c.execute('UPDATE users SET is_admin=1,login_enabled=1 WHERE id=1')
                c.execute(f'UPDATE users SET {column}=0 WHERE id=1')
            before = self.db.read_bytes()
            self.rejected()
            self.assertEqual(self.db.read_bytes(), before)

    def test_normal_mode_refuses_demo_database_even_if_relocated(self):
        self.start(); self.stop()
        self.rejected({'SERVICEHUB_DB_PATH': str(self.db)}, args=())
        moved = self.root / 'copied-demo.db'
        shutil.copyfile(self.db, moved)
        before = moved.read_bytes()
        self.rejected({'SERVICEHUB_ENV': 'production', 'SERVICEHUB_DB_PATH': str(moved)}, args=())
        self.assertEqual(before, moved.read_bytes())

    def test_symlinked_store_refused_before_writes(self):
        outside = self.root / 'outside'
        outside.mkdir()
        self.store.symlink_to(outside, target_is_directory=True)
        self.rejected()
        self.assertEqual(list(outside.iterdir()), [])

    def test_unsafe_credential_permissions_and_file_links_refused(self):
        self.start(); self.stop()
        before = self.db.read_bytes()
        if os.name == 'posix':
            self.creds.chmod(0o644)
            self.rejected()
            self.creds.chmod(0o600)
        original = self.store / 'private-original.json'
        self.creds.rename(original)
        self.creds.symlink_to(original)
        self.rejected()
        self.assertEqual(before, self.db.read_bytes())

    def test_parallel_initialization_lock_refuses_without_writes(self):
        self.store.mkdir(mode=0o700)
        (self.store / '.startup-lock').mkdir()
        result = self.rejected()
        self.assertIn('locked', result.stderr)
        self.assertFalse(self.db.exists())
        self.assertFalse(self.creds.exists())


if __name__ == '__main__':
    unittest.main()
