"""Checks that ServiceHub reads .env and starts without financial features."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

SOURCE = Path(__file__).resolve().parents[1]

class LocalEnvLoadingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='servicehub-env-test-')
        self.root = Path(self.tmp.name)
        shutil.copyfile(SOURCE / 'server.py', self.root / 'server.py')
        shutil.copyfile(SOURCE / 'schema.sql', self.root / 'schema.sql')
        shutil.copyfile(SOURCE / 'email_verification.py', self.root / 'email_verification.py')
        (self.root / '.env').write_text('SERVICEHUB_PORT=8001\nSERVICEHUB_HOST=127.0.0.1\n', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def inspect(self, overrides=None):
        env = dict(os.environ)
        for key in list(env):
            if key.startswith('SERVICEHUB_'):
                env.pop(key)
        env.update(overrides or {})
        code = ('import json, server; '
                'print(json.dumps({"port": server.PORT, "host": server.HOST}))')
        result = subprocess.check_output([sys.executable,'-c',code],cwd=self.root,env=env,text=True)
        return json.loads(result)

    def test_direct_start_loads_env_and_port(self):
        self.assertEqual(self.inspect()['port'], 8001)
        self.assertEqual(self.inspect()['host'], '127.0.0.1')

    def test_environment_override_takes_priority(self):
        self.assertEqual(self.inspect({'SERVICEHUB_PORT':'9081'})['port'], 9081)

    def test_server_starts_with_local_env(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        (self.root / '.env').write_text(f'SERVICEHUB_PORT={port}\nSERVICEHUB_HOST=127.0.0.1\n', encoding='utf-8')
        env = dict(os.environ)
        for key in list(env):
            if key.startswith('SERVICEHUB_'):
                env.pop(key)
        proc = subprocess.Popen([sys.executable,'server.py'],cwd=self.root,env=env,
                                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                if proc.poll() is not None:
                    self.fail('Server exited while loading .env')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=1) as response:
                        self.assertEqual(response.status,200)
                    break
                except (OSError,TimeoutError):
                    time.sleep(.1)
            else:
                self.fail('Server startup timed out')
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill();proc.wait(timeout=5)

if __name__ == '__main__':
    unittest.main()
