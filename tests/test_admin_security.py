"""Admin security and email verification tests using disposable data only."""
import gc
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from unittest.mock import patch
import server


class AdminSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='servicehub-admin-security-')
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(gc.collect)
        self.root = Path(self.tmp.name)
        (self.root / 'static').mkdir()
        (self.root / 'static' / 'index.html').write_text('public test page', encoding='utf-8')
        (self.root / 'private-test.txt').write_text('private test file', encoding='utf-8')
        self.has_symlink = True
        try:
            (self.root / 'static' / 'outside.txt').symlink_to(self.root / 'private-test.txt')
        except (OSError, NotImplementedError):
            # Windows may require Developer Mode or permission to create symlinks.
            self.has_symlink = False

        self.env_patch = patch.dict(os.environ, {
            'SERVICEHUB_LOCAL_DEMO': '0',
            'SERVICEHUB_ENV': 'test',
            'SERVICEHUB_OTP_SECRET': secrets.token_hex(32),
            'SERVICEHUB_SMTP_EMAIL': '',
            'SERVICEHUB_SMTP_PASSWORD': '',
        })
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.outbox = {}
        self.patch = patch.multiple(
            server, DB_PATH=self.root / 'test.db', ROOT=self.root,
            ADMIN_EMAIL='', ADMIN_PASSWORD=''
        )
        self.patch.start()
        self.addCleanup(self.patch.stop)
        # Patch the function used by server.py, not the actual Gmail account.
        self.mail_patch = patch.object(server, 'send_otp_email', side_effect=self.capture_otp)
        self.mail_mock = self.mail_patch.start()
        self.addCleanup(self.mail_patch.stop)
        server.seed()
        self.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_http)
        self.base = f'http://127.0.0.1:{self.http.server_port}'

    def stop_http(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=5)

    def capture_otp(self, email, code):
        self.outbox[email] = code

    def request(self, path, method='GET', data=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(data).encode() if data is not None else None,
            method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                body = response.read()
                return response.status, json.loads(body) if 'application/json' in response.headers.get('Content-Type', '') else body
        except urllib.error.HTTPError as error:
            with error:
                return error.code, json.load(error)

    def provision(self, email='private-admin@example.com', password='Private-Test-Password-123!'):
        with patch.multiple(server, ADMIN_EMAIL=email, ADMIN_PASSWORD=password):
            server.seed()
        return email, password

    def login(self, email, password):
        return self.request('/api/auth/login', 'POST', {'email': email, 'password': password})

    def register_pending(self, email, password='Password-123', name='Normal User', **extra):
        status, body = self.request('/api/auth/register', 'POST', {
            'name': name, 'email': email, 'password': password, **extra
        })
        self.assertEqual(status, 201, body)
        self.assertTrue(body['data']['requires_verification'])
        self.assertNotIn('token', body['data'])
        self.assertIn(email, self.outbox)
        self.assertRegex(self.outbox[email], r'^[0-9]{6}$')
        return self.outbox[email]

    def verify(self, email, password, code):
        return self.request('/api/auth/verify-email', 'POST', {
            'email': email, 'password': password, 'code': code
        })

    def register_and_login(self, email, password='Password-123', name='Normal User', **extra):
        code = self.register_pending(email, password, name, **extra)
        status, body = self.verify(email, password, code)
        self.assertEqual(status, 200, body)
        status, body = self.login(email, password)
        self.assertEqual(status, 200, body)
        return body

    def test_fresh_start_has_no_demo_accounts_and_register_cannot_grant_admin(self):
        with closing(server.connect()) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0], 0)
        for email in server.LEGACY_DEMO_EMAILS:
            self.assertEqual(self.login(email, 'Admin@12345')[0], 401)
            self.assertEqual(self.request('/api/auth/register', 'POST', {
                'name': 'Fake Admin', 'email': email, 'password': 'Password-123'
            })[0], 400)
        self.mail_mock.assert_not_called()
        body = self.register_and_login('customer@example.com', is_admin=1)
        self.assertEqual(body['data']['user']['is_admin'], 0)
        self.assertEqual(self.request('/api/admin/stats', token=body['data']['token'])[0], 403)

    def test_bootstrap_admin_login_idempotency_and_password_rotation(self):
        email, password = self.provision()
        code, body = self.login(email, password)
        self.assertEqual(code, 200)
        token = body['data']['token']
        self.assertEqual(self.request('/api/admin/stats', token=token)[0], 200)
        self.provision()
        self.assertEqual(self.request('/api/admin/stats', token=token)[0], 200)
        with closing(server.connect()) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users WHERE is_admin=1').fetchone()[0], 1)
        self.provision(password='Rotated-Test-Password-456!')
        self.assertEqual(self.login(email, password)[0], 401)
        self.assertEqual(self.request('/api/me', token=token)[0], 401)
        self.assertEqual(self.login(email, 'Rotated-Test-Password-456!')[0], 200)

    def test_migration_disables_old_logins_and_sessions_preserves_money(self):
        legacy_passwords = ['Admin@12345', 'Huy@12345', 'Owner@12345']
        tokens = []
        with closing(server.connect()) as c, c:
            c.execute("DELETE FROM app_settings WHERE key='demo_logins_retired_v1'")
            for email, password in zip(server.LEGACY_DEMO_EMAILS, legacy_passwords):
                uid = c.execute('INSERT INTO users(name,email,password_hash,is_admin) VALUES(?,?,?,?)',
                                ('Legacy', email, server.hash_password(password), int(email.startswith('admin@')))).lastrowid
                token = secrets.token_urlsafe(20)
                tokens.append(token)
                c.execute('INSERT INTO sessions VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), uid, '2099-01-01T00:00:00+00:00'))
        self.provision()
        for email, password, token in zip(server.LEGACY_DEMO_EMAILS, legacy_passwords, tokens):
            self.assertEqual(self.login(email, password)[0], 401)
            self.assertEqual(self.request('/api/me', token=token)[0], 401)
        with closing(server.connect()) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users WHERE login_enabled=0').fetchone()[0], 3)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users WHERE is_admin=1').fetchone()[0], 1)

    def test_disabled_account_stays_blocked_even_with_a_new_session(self):
        body = self.register_and_login('disabled@example.com', name='Disabled User')
        with closing(server.connect()) as c, c:
            c.execute('UPDATE users SET login_enabled=0 WHERE id=?', (body['data']['user']['id'],))
        self.assertEqual(self.request('/api/me', token=body['data']['token'])[0], 401)
        self.assertEqual(self.login('disabled@example.com', 'Password-123')[0], 401)

    def test_admin_email_collision_never_promotes_customer(self):
        self.register_pending('customer@example.com', name='Customer')
        with self.assertRaises(RuntimeError):
            self.provision(email='customer@example.com')
        with closing(server.connect()) as c:
            self.assertEqual(c.execute('SELECT is_admin FROM users WHERE email=?', ('customer@example.com',)).fetchone()[0], 0)

    def test_invalid_admin_configuration_fails_without_partial_admin(self):
        for email, password in [('admin@example.com', ''), ('', 'Password-123456789'), ('invalid', 'Password-123456789'), ('admin@example.com', 'short')]:
            with self.subTest(email=email), self.assertRaises(RuntimeError):
                self.provision(email, password)
        with closing(server.connect()) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0], 0)

    def test_reuse_legacy_admin_email_only_with_new_secret(self):
        with closing(server.connect()) as c, c:
            c.execute("DELETE FROM app_settings WHERE key='demo_logins_retired_v1'")
            c.execute('INSERT INTO users(name,email,password_hash,is_admin) VALUES(?,?,?,1)',
                      ('Old Admin', 'admin@servicehub.local', server.hash_password('Admin@12345')))
        self.provision('admin@servicehub.local')
        self.assertEqual(self.login('admin@servicehub.local', 'Admin@12345')[0], 401)
        self.assertEqual(self.login('admin@servicehub.local', 'Private-Test-Password-123!')[0], 200)

    def test_static_paths_cannot_escape_public_directory(self):
        self.assertEqual(self.request('/')[0], 200)
        self.assertEqual(self.request('/static/index.html')[0], 200)
        for path in ['/static/../private-test.txt', '/static/../test.db', '/static/../../private-test.txt', '/static/%2e%2e/private-test.txt']:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_static_symlink_cannot_escape_public_directory(self):
        if not self.has_symlink:
            self.skipTest('This environment does not permit symlink creation.')
        self.assertEqual(self.request('/static/outside.txt')[0], 404)

    def test_frontend_has_no_demo_login_buttons_or_credentials(self):
        project = Path(__file__).resolve().parents[1]
        html = (project / 'static/index.html').read_text(encoding='utf-8')
        js = (project / 'static/js/app.js').read_text(encoding='utf-8')
        for fragment in ['data-demo-login', 'Admin@12345', 'Huy@12345', 'Owner@12345', 'demoLogin']:
            self.assertNotIn(fragment, html + js)

    def test_otp_required_before_login_and_cannot_be_reused(self):
        email, password = 'otp@example.com', 'Password-123'
        code = self.register_pending(email, password)
        status, body = self.login(email, password)
        self.assertEqual(status, 403)
        self.assertEqual(body['error']['code'], 'EMAIL_NOT_VERIFIED')
        self.assertEqual(self.verify(email, 'Wrong-Password', code)[0], 401)
        self.assertEqual(self.verify(email, password, code)[0], 200)
        self.assertEqual(self.login(email, password)[0], 200)
        self.assertEqual(self.verify(email, password, code)[0], 409)
        with closing(server.connect()) as c:
            self.assertEqual(c.execute('SELECT email_verified FROM users WHERE email=?', (email,)).fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM email_verifications').fetchone()[0], 0)

    def test_otp_attempt_limit_expiry_and_resend(self):
        email, password = 'retry@example.com', 'Password-123'
        # Fixed OTPs ONLY in this test, to avoid randomly generating the same value twice.
        with patch.object(server, 'generate_otp', side_effect=['123456', '654321']):
            code = self.register_pending(email, password)
            credentials = {'email': email, 'password': password}
            status, body = self.request('/api/auth/resend-code', 'POST', credentials)
            self.assertEqual(status, 429)
            self.assertEqual(body['error']['code'], 'RESEND_TOO_SOON')
            for _ in range(server.MAX_ATTEMPTS):
                self.assertEqual(self.verify(email, password, '000000')[0], 400)
            status, body = self.verify(email, password, code)
            self.assertEqual(status, 429)
            self.assertEqual(body['error']['code'], 'OTP_ATTEMPTS_EXCEEDED')
            with closing(server.connect()) as c, c:
                c.execute('UPDATE email_verifications SET expires_at=0, sent_at=0')
            status, body = self.verify(email, password, code)
            self.assertEqual(status, 400)
            self.assertEqual(body['error']['code'], 'OTP_EXPIRED')
            self.assertEqual(self.request('/api/auth/resend-code', 'POST', credentials)[0], 200)
            new_code = self.outbox[email]
            self.assertNotEqual(new_code, code)
            self.assertEqual(self.verify(email, password, code)[0], 400)
            self.assertEqual(self.verify(email, password, new_code)[0], 200)
            self.assertEqual(self.login(email, password)[0], 200)


if __name__ == '__main__':
    unittest.main()
