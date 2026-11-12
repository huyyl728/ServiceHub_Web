"""Local demo opt-in, idempotency, credential handling and real API permissions."""
from datetime import datetime, timedelta
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

import server
from local_demo import MARKER, demo_database, require_local_demo
from scripts import seed_local_demo as demo

SOURCE = Path(__file__).resolve().parents[1]


class LocalDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='servicehub-local-demo-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        self.root.mkdir()
        self.database = demo_database(self.root)
        self.database.parent.mkdir()
        self.credentials = Path(self.temp.name) / 'demo-credentials.json'
        self.env = {'SERVICEHUB_ENV': 'local-demo', 'SERVICEHUB_LOCAL_DEMO': '1',
                    'SERVICEHUB_HOST': '127.0.0.1', 'SERVICEHUB_ENABLE_BANK_QR': '0'}
        for context in (patch.dict(os.environ, self.env, clear=True),
                        patch.object(demo, 'ROOT', self.root),
                        patch.multiple(server, ROOT=self.root, DB_PATH=self.database,
                                       HOST='127.0.0.1', ADMIN_EMAIL='', ADMIN_PASSWORD='')):
            context.start()
            self.addCleanup(context.stop)
        self.passwords = demo.read_credentials(self.credentials)

    def snapshot(self):
        with server.connect() as connection:
            return '\n'.join(connection.iterdump())

    def test_exact_accounts_hashes_roles_relationships_and_balances(self):
        self.assertTrue(demo.seed_demo(server, self.passwords))
        server.seed()
        with server.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0], 6)
            self.assertEqual(c.execute('SELECT SUM(is_admin),SUM(login_enabled) FROM users').fetchone()[:], (0, 6))
            self.assertEqual(c.execute('SELECT COUNT(DISTINCT owner_id) FROM businesses').fetchone()[0], 3)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM services').fetchone()[0], 6)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM business_applications WHERE status='approved'").fetchone()[0], 3)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
            for username, _, role in demo.ACCOUNTS:
                row = c.execute('SELECT * FROM users WHERE email=?', (demo.email_for(username),)).fetchone()
                self.assertTrue(server.verify_password(self.passwords[username], row['password_hash']))
                self.assertNotEqual(self.passwords[username], row['password_hash'])
                count = c.execute('SELECT COUNT(*) FROM businesses WHERE owner_id=?', (row['id'],)).fetchone()[0]
                self.assertEqual(count, int(role == 'Owner'))
                balance = c.execute('SELECT balance FROM wallets WHERE user_id=?', (row['id'],)).fetchone()[0]
                self.assertEqual(balance, 1000000 if role == 'Customer' else 0)

    def test_repeat_preserves_ids_hashes_spending_and_user_edits(self):
        demo.seed_demo(server, self.passwords)
        server.seed()
        with server.connect() as c:
            c.execute('UPDATE wallets SET balance=17 WHERE user_id=1')
            c.execute("UPDATE services SET price=12345,name='Edited presentation' WHERE id=1")
        before = self.snapshot()
        self.assertFalse(demo.seed_demo(server, self.passwords))
        server.seed()
        self.assertEqual(before, self.snapshot())

    def test_normal_startup_creates_no_accounts(self):
        with patch.dict(os.environ, {}, clear=True):
            server.seed()
        with server.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0], 0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0], 0)

    def test_guard_rejects_public_production_bank_admin_and_other_database(self):
        invalid = [{}, {**self.env, 'SERVICEHUB_ENV': 'production'},
                   {**self.env, 'SERVICEHUB_LOCAL_DEMO': '0'},
                   {**self.env, 'SERVICEHUB_ENABLE_BANK_QR': '1'},
                   {**self.env, 'SERVICEHUB_ADMIN_EMAIL': 'admin@example.test'}]
        invalid += [{**self.env, key: 'production' if key == 'APP_ENV' else '1'}
                    for key in ('RENDER', 'DYNO', 'VERCEL', 'K_SERVICE', 'APP_ENV')]
        for env in invalid:
            with self.subTest(env=env), self.assertRaises(RuntimeError):
                require_local_demo(env, '127.0.0.1', self.database, self.root)
        for host in ('0.0.0.0', '::', '192.168.1.2'):
            with self.subTest(host=host), self.assertRaises(RuntimeError):
                require_local_demo(self.env, host, self.database, self.root)
        with self.assertRaises(RuntimeError):
            require_local_demo(self.env, '127.0.0.1', self.root / 'production.db', self.root)

    def test_seeded_database_cannot_start_public_or_without_opt_in(self):
        demo.seed_demo(server, self.passwords)
        before = self.snapshot()
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(RuntimeError):
            server.seed()
        with patch.object(server, 'HOST', '0.0.0.0'), self.assertRaises(RuntimeError):
            server.seed()
        copied = self.root / 'production.db'
        shutil.copyfile(self.database, copied)
        with patch.object(server, 'DB_PATH', copied), self.assertRaises(RuntimeError):
            server.seed()
        self.assertEqual(before, self.snapshot())

    def test_nonempty_unmarked_database_is_untouched(self):
        with server.connect() as c:
            c.execute('CREATE TABLE existing_data(value TEXT)')
            c.execute("INSERT INTO existing_data VALUES('keep me')")
        before = self.snapshot()
        with self.assertRaises(RuntimeError):
            demo.seed_demo(server, self.passwords)
        self.assertEqual(before, self.snapshot())

    def test_changed_credentials_or_ownership_fail_without_mutation(self):
        demo.seed_demo(server, self.passwords)
        different = dict(self.passwords, customer01=secrets.token_urlsafe(18))
        before = self.snapshot()
        with self.assertRaises(RuntimeError):
            demo.seed_demo(server, different)
        self.assertEqual(before, self.snapshot())
        with server.connect() as c:
            c.execute('UPDATE businesses SET owner_id=1 WHERE id=1')
        before = self.snapshot()
        with self.assertRaises(RuntimeError):
            demo.seed_demo(server, self.passwords)
        self.assertEqual(before, self.snapshot())

    def test_transaction_rolls_back_all_seed_rows_on_failure(self):
        with patch.object(server, 'hash_password', side_effect=[server.hash_password(secrets.token_urlsafe(18)), RuntimeError('injected')]):
            with self.assertRaises(RuntimeError):
                demo.seed_demo(server, self.passwords)
        with server.connect() as c:
            for table in ('users', 'wallets', 'businesses', 'services', 'app_settings'):
                self.assertEqual(c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 0)

    def test_credentials_private_external_distinct_and_reused(self):
        self.assertEqual(len(set(self.passwords.values())), 6)
        self.assertEqual(self.passwords, demo.read_credentials(self.credentials))
        self.assertEqual(self.credentials.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(RuntimeError):
            demo.read_credentials(self.root / 'credentials.json')
        link = Path(self.temp.name) / 'link.json'
        link.symlink_to(self.credentials)
        with self.assertRaises(RuntimeError):
            demo.read_credentials(link)
        payload = json.loads(self.credentials.read_text())
        payload['accounts'][1]['password'] = payload['accounts'][0]['password']
        self.credentials.write_text(json.dumps(payload))
        with self.assertRaises(RuntimeError):
            demo.read_credentials(self.credentials)

    def test_cli_requires_flag_rechecks_dotenv_and_is_idempotent(self):
        (self.root / 'scripts').mkdir()
        for filename in ('server.py', 'schema.sql', 'local_demo.py', 'scripts/seed_local_demo.py'):
            shutil.copyfile(SOURCE / filename, self.root / filename)
        command = [sys.executable, str(self.root / 'scripts/seed_local_demo.py'),
                   '--credentials-file', str(self.credentials)]
        result = subprocess.run(command, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.database.exists())
        (self.root / '.env').write_text('RENDER=true\n')
        result = subprocess.run(command + ['--local-demo'], env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.database.exists())
        (self.root / '.env').unlink()
        for _ in range(2):
            result = subprocess.run(command + ['--local-demo'], env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for password in self.passwords.values():
                self.assertNotIn(password, result.stdout + result.stderr)

    def test_six_real_logins_owner_isolation_and_booking_flow(self):
        demo.seed_demo(server, self.passwords)
        server.seed()
        http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        def cleanup():
            http.shutdown()
            http.server_close()
            thread.join(timeout=5)
        self.addCleanup(cleanup)
        def request(path, method='GET', body=None, token=None):
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Authorization'] = 'Bearer ' + token
            req = urllib.request.Request(f'http://127.0.0.1:{http.server_port}' + path,
                data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    return response.status, json.load(response)
            except urllib.error.HTTPError as error:
                with error:
                    return error.code, json.load(error)
        tokens = {}
        for username, _, role in demo.ACCOUNTS:
            status, response = request('/api/auth/login', 'POST',
                {'email': demo.email_for(username), 'password': self.passwords[username]})
            self.assertEqual(status, 200, response)
            token = tokens[username] = response['data']['token']
            profile = request('/api/me', token=token)[1]['data']
            self.assertEqual(len(profile['businesses']), int(role == 'Owner'))
            self.assertEqual(request('/api/admin/stats', token=token)[0], 403)
        services = request('/api/services')[1]['data']
        self.assertEqual(len(services), 6)
        with server.connect() as c:
            manifest = json.loads(c.execute('SELECT value FROM app_settings WHERE key=?', (MARKER,)).fetchone()[0])
        for owner in ('owner01', 'owner02', 'owner03'):
            bid = manifest['businesses'][owner]
            for username in tokens:
                status, _ = request(f'/api/owner/services?business_id={bid}', token=tokens[username])
                self.assertEqual(status, 200 if username == owner else 403)
        status, booking = request('/api/bookings', 'POST',
            {'service_id': manifest['services']['owner01'][0],
             'date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'), 'start_time': '10:00'}, tokens['customer01'])
        self.assertEqual(status, 201, booking)
        booking_id = booking['data']['id']
        bid = manifest['businesses']['owner01']
        self.assertEqual(request(f'/api/owner/bookings/{bid}/confirm', 'POST', {'booking_id': booking_id}, tokens['owner02'])[0], 403)
        self.assertEqual(request(f'/api/owner/bookings/{bid}/confirm', 'POST', {'booking_id': booking_id}, tokens['owner01'])[0], 200)
        self.assertEqual(request(f'/api/bookings/{booking_id}/pay-wallet', 'POST', {}, tokens['customer01'])[0], 200)
        self.assertFalse(demo.seed_demo(server, self.passwords))


if __name__ == '__main__':
    unittest.main()
