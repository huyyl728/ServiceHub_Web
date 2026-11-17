import os
import sys
import shutil
import sqlite3
import secrets
import tempfile
import subprocess
import unittest

from pathlib import Path
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]


class LocalDemoTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

        shutil.copy(ROOT / 'server.py', self.root)
        shutil.copy(ROOT / 'schema.sql', self.root)

        (self.root / 'scripts').mkdir()

        shutil.copy(
            ROOT / 'scripts/local_demo.py',
            self.root / 'scripts/local_demo.py'
        )

        shutil.copy(
            ROOT / 'scripts/start_demo.py',
            self.root / 'scripts/start_demo.py'
        )

        self.env = {
            k: v for k, v in os.environ.items()
            if not k.startswith('SERVICEHUB_')
        }

        self.env.update({
            'SERVICEHUB_HOST': '127.0.0.1',
            'SERVICEHUB_ADMIN_EMAIL':
                'admin-test@servicehub.local',
            'SERVICEHUB_ADMIN_PASSWORD':
                secrets.token_urlsafe(24),
            'SERVICEHUB_LOCAL_DEMO': '1'
        })

    def run_seed(self):
        return subprocess.run(
            [
                sys.executable,
                '-c',
                'import server; '
                'server.seed(); '
                'server.seed_local_demo()'
            ],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True
        )

    def query(self, sql):
        with closing(sqlite3.connect(
            self.root / 'servicehub.db'
        )) as conn:
            return conn.execute(sql).fetchall()

    def test_create_demo_accounts(self):
        result = self.run_seed()

        self.assertEqual(
            result.returncode, 0, result.stderr
        )

        self.assertEqual(
            self.query('SELECT COUNT(*) FROM users')[0][0],
            7
        )

        self.assertEqual(
            self.query(
                'SELECT COUNT(*) FROM users WHERE is_admin=1'
            )[0][0],
            1
        )

        self.assertEqual(
            self.query('SELECT COUNT(*) FROM businesses')[0][0],
            3
        )

        self.assertEqual(
            self.query('SELECT COUNT(*) FROM services')[0][0],
            6
        )

    def test_restart_does_not_duplicate_data(self):
        first = self.run_seed()
        self.assertEqual(first.returncode, 0, first.stderr)

        before = self.query(
            'SELECT id, email, password_hash FROM users ORDER BY id'
        )

        second = self.run_seed()
        self.assertEqual(second.returncode, 0, second.stderr)

        after = self.query(
            'SELECT id, email, password_hash FROM users ORDER BY id'
        )

        self.assertEqual(before, after)

    def test_demo_disabled_in_production(self):
        self.env['SERVICEHUB_ENV'] = 'production'

        result = self.run_seed()

        self.assertNotEqual(result.returncode, 0)

        self.assertFalse(
            (self.root / 'servicehub.db').exists()
        )

    def test_existing_demo_database_requires_demo_mode(self):
        first = self.run_seed()

        self.assertEqual(first.returncode, 0, first.stderr)

        db = self.root / 'servicehub.db'
        before = db.read_bytes()

        self.env['SERVICEHUB_LOCAL_DEMO'] = '0'

        result = self.run_seed()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, db.read_bytes())

    def test_production_rejects_copied_demo_database(self):
        first = self.run_seed()

        self.assertEqual(first.returncode, 0, first.stderr)

        copied_db = self.root / 'production.db'

        shutil.copyfile(
            self.root / 'servicehub.db',
            copied_db
        )

        before = copied_db.read_bytes()

        self.env.update({
            'SERVICEHUB_ENV': 'production',
            'SERVICEHUB_LOCAL_DEMO': '0',
            'SERVICEHUB_DB_PATH': str(copied_db)
        })

        result = self.run_seed()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, copied_db.read_bytes())
    def test_legacy_demo_compatibility(self):

        # Khởi tạo demo độc lập hai lần
        for _ in range(2):
            result = subprocess.run(
                [
                    sys.executable,
                    'scripts/local_demo.py',
                    '--setup-only'
                ],
                cwd=self.root,
                env=self.env,
                capture_output=True,
                text=True
            )

            self.assertEqual(
                result.returncode, 0, result.stderr
            )

        legacy_db = (
            self.root / '.local-demo/servicehub-demo.db'
        )

        self.assertTrue(legacy_db.exists())

        with closing(sqlite3.connect(legacy_db)) as conn:
            self.assertEqual(
                conn.execute(
                    'SELECT COUNT(*) FROM users'
                ).fetchone()[0],
                7
            )

        # Production phải từ chối database demo cũ
        copied_db = self.root / 'legacy-production.db'
        shutil.copyfile(legacy_db, copied_db)

        before = copied_db.read_bytes()

        self.env.update({
            'SERVICEHUB_ENV': 'production',
            'SERVICEHUB_LOCAL_DEMO': '0',
            'SERVICEHUB_DB_PATH': str(copied_db)
        })

        result = self.run_seed()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            'Database chứa dữ liệu demo',
            result.stderr
        )
        self.assertEqual(before, copied_db.read_bytes())

    def run_launcher(self, extra_env=None):
        env = {k: v for k, v in self.env.items()
               if not k.startswith('SERVICEHUB_')}
        env.update(extra_env or {})
        return subprocess.run(
            [sys.executable, 'scripts/start_demo.py', '--setup-only'],
            cwd=self.root, env=env, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=30
        )

    def test_launcher_clean_clone_and_restart(self):
        first = self.run_launcher()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(self.query('SELECT COUNT(*) FROM users'), [(7,)])
        self.assertEqual(self.query('SELECT COUNT(*) FROM businesses'), [(3,)])
        self.assertEqual(self.query('SELECT COUNT(*) FROM services'), [(6,)])
        env_path = self.root / '.env'
        creds_path = self.root / '.local-demo/main-credentials.json'
        self.assertTrue(env_path.is_file())
        self.assertTrue(creds_path.is_file())
        before = self.query('SELECT id, email, password_hash FROM users ORDER BY id')
        config = env_path.read_bytes()
        credentials = creds_path.read_bytes()
        second = self.run_launcher()
        self.assertEqual(second.returncode, 0, second.stderr)
        # Kiểm tra không tạo lại hoặc đổi mật khẩu khi chạy lần hai.
        self.assertTrue(config == env_path.read_bytes())
        self.assertTrue(credentials == creds_path.read_bytes())
        self.assertTrue(before == self.query(
            'SELECT id, email, password_hash FROM users ORDER BY id'
        ))

    def test_launcher_rejects_hosting_without_writing(self):
        result = self.run_launcher({'SERVICEHUB_ENV': 'production'})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / '.env').exists())
        self.assertFalse((self.root / 'servicehub.db').exists())

    def test_launcher_preserves_non_demo_database(self):
        db = self.root / 'servicehub.db'
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute('CREATE TABLE existing_data (name TEXT)')
            conn.execute("INSERT INTO existing_data VALUES ('Dữ liệu cần giữ')")
        before = db.read_bytes()
        result = self.run_launcher()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, db.read_bytes())
        self.assertFalse((self.root / '.env').exists())

    def test_launcher_does_not_overwrite_existing_config(self):
        env_path = self.root / '.env'
        env_path.write_text('SERVICEHUB_LOCAL_DEMO=0\n', encoding='utf-8')
        before = env_path.read_bytes()
        result = self.run_launcher()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, env_path.read_bytes())
        self.assertFalse((self.root / 'servicehub.db').exists())

if __name__ == '__main__':
    unittest.main()