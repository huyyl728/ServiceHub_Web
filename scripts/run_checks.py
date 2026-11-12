#!/usr/bin/env python3
"""Reproducible ServiceHub checks, using temporary SQLite data only.
Usage: python3 scripts/run_checks.py
"""
from pathlib import Path
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def run(args, *, env=None):
    print('>>>', ' '.join(args), flush=True)
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def main():
    run([sys.executable, '-m', 'py_compile', 'server.py', 'payment_providers.py',
         'local_demo.py', 'scripts/seed_local_demo.py'])
    with tempfile.TemporaryDirectory(prefix='servicehub-all-tests-') as temp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = dict(os.environ, SERVICEHUB_HOST='127.0.0.1', SERVICEHUB_PORT=str(port),
                   SERVICEHUB_DB_PATH=str(Path(temp) / 'tests.db'),
                   SERVICEHUB_TEST_BASE=f'http://127.0.0.1:{port}')
        print('>>> Khởi động API thử nghiệm với cơ sở dữ liệu tạm', flush=True)
        process = subprocess.Popen([sys.executable, 'tests/fixture_server.py'], cwd=ROOT,
                                   env=env, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('Máy chủ kiểm thử dừng đột ngột.')
                try:
                    with urllib.request.urlopen(env['SERVICEHUB_TEST_BASE'] + '/api/health', timeout=1) as response:
                        if response.status == 200:
                            break
                except (OSError, TimeoutError):
                    time.sleep(0.1)
            else:
                raise RuntimeError('Không thể khởi động máy chủ kiểm thử.')
            run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], env=env)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    # Node is only needed for development/test, not to run the website.
    import shutil
    if shutil.which('node'):
        run(['node', '--check', 'static/js/app.js'])
        run(['node', '--check', 'static/js/advisor.js'])
        run(['node', 'tests/test_advisor.js'])
    else:
        print('>>> Node.js không có; bỏ qua kiểm tra logic advisor JS.', flush=True)
    print('>>> PASS: các bước kiểm tra đã thực thi thành công.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (subprocess.CalledProcessError, RuntimeError) as error:
        print('>>> FAIL:', error, file=sys.stderr)
        sys.exit(1)
