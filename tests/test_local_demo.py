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

        self.assertEqual(
            self.query(
                'SELECT COUNT(*) FROM users WHERE is_admin=0'
            )[0][0],
            0
        )

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

if __name__ == '__main__':
    unittest.main()