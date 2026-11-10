"""Regression checks for direct Python startup and the per-project .env file.

Only fake account data is used; no bank requests or money transfers happen.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import socket
import time
import urllib.request
import urllib.error

SOURCE = Path(__file__).resolve().parents[1]


class LocalEnvLoadingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='servicehub-env-regression-')
        self.root = Path(self.tmp.name)
        shutil.copyfile(SOURCE / 'server.py', self.root / 'server.py')
        shutil.copyfile(SOURCE / 'schema.sql', self.root / 'schema.sql')
        (self.root / '.env').write_text('''# settings only for temporary test instance
SERVICEHUB_ENABLE_BANK_QR=1
SERVICEHUB_BANK_BIN=970415
SERVICEHUB_BANK_ACCOUNT=0000000000
SERVICEHUB_BANK_NAME="NGUYEN VAN DEMO"
SERVICEHUB_PORT=8001
''', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def inspect(self, overrides=None):
        env = dict(os.environ)
        for key in list(env):
            if key.startswith('SERVICEHUB_'):
                env.pop(key)
        env.update(overrides or {})
        cmd = [sys.executable, '-c', '''import json, server
print(json.dumps({"configured": server.BANK_QR_CONFIGURED,
                  "port": server.PORT,
                  "bin": server.BANK_BIN,
                  "issues": server.BANK_QR_ISSUES},ensure_ascii=False))''']
        result = subprocess.check_output(cmd, cwd=self.root, env=env, text=True)
        return json.loads(result)

    def test_direct_start_loads_env_and_port(self):
        actual = self.inspect()
        self.assertTrue(actual['configured'])
        self.assertEqual(actual['port'], 8001)
        self.assertEqual(actual['bin'], '970415')
        self.assertEqual(actual['issues'], [])

    def test_explicit_environment_override_takes_priority(self):
        actual = self.inspect({'SERVICEHUB_ENABLE_BANK_QR': '0', 'SERVICEHUB_PORT': '9081'})
        self.assertFalse(actual['configured'])
        self.assertEqual(actual['port'], 9081)
        self.assertIn('SERVICEHUB_ENABLE_BANK_QR', ' '.join(actual['issues']))

    def test_invalid_bank_bin_has_actionable_diagnostic(self):
        (self.root / '.env').write_text((self.root / '.env').read_text().replace('970415', 'MA_BIN_6_SO'))
        actual = self.inspect()
        self.assertFalse(actual['configured'])
        self.assertIn('SERVICEHUB_BANK_BIN', ' '.join(actual['issues']))

    def test_live_api_reads_env_and_creates_pending_qr(self):
        """Run the real server with .env only, with a clearly fictitious account."""
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        (self.root / '.env').write_text((self.root / '.env').read_text().replace('8001', str(port)))
        env = dict(os.environ)
        for key in list(env):
            if key.startswith('SERVICEHUB_'):
                env.pop(key)
        proc = subprocess.Popen([sys.executable, 'server.py'], cwd=self.root, env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f'http://127.0.0.1:{port}'

        def request(path, method='GET', data=None, token=None):
            headers = {'Content-Type': 'application/json'}
            if token: headers['Authorization'] = 'Bearer ' + token
            req = urllib.request.Request(base + path,
                data=json.dumps(data).encode() if data is not None else None,
                headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.load(resp)

        try:
            for _ in range(80):
                if proc.poll() is not None:
                    self.fail('Server failed to launch from .env')
                try:
                    if request('/api/health')[0] == 200:
                        break
                except (OSError, urllib.error.URLError):
                    time.sleep(.1)
            else:
                self.fail('Server startup timed out')
            _, login = request('/api/auth/register', 'POST',
                        {'name': 'QR Environment Test', 'email': 'qr-test@example.com', 'password': 'Test-Only-Password-123'})
            token = login['data']['token']
            _, config = request('/api/bank-qr/config', token=token)
            self.assertTrue(config['data']['configured'], config)
            code, qr = request('/api/bank-qr/requests', 'POST',
                        {'amount': 100000, 'request_id': 'env-e2e-test-0001'}, token)
            self.assertEqual(code, 201)
            self.assertEqual(qr['data']['status'], 'pending')
            self.assertIn('970415-0000000000', qr['data']['qr_url'])
            self.assertIn('amount=100000', qr['data']['qr_url'])
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
