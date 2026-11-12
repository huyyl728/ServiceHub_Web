"""Shared safety boundary for explicitly opted-in, disposable local demos."""
from pathlib import Path

MARKER = 'local_demo_seed_v1'


def demo_database(root):
    return Path(root).resolve() / '.local-demo' / 'servicehub-demo.db'


def require_local_demo(environ, host, database, root):
    if environ.get('SERVICEHUB_ENV') != 'local-demo' or environ.get('SERVICEHUB_LOCAL_DEMO') != '1':
        raise RuntimeError('Local demo requires SERVICEHUB_ENV=local-demo and SERVICEHUB_LOCAL_DEMO=1.')
    if host not in ('127.0.0.1', 'localhost'):
        raise RuntimeError('Local demo may only bind to 127.0.0.1 or localhost.')
    if Path(database).resolve() != demo_database(root):
        raise RuntimeError('Local demo requires the dedicated .local-demo/servicehub-demo.db database (no symlinks).')
    hosted = ('RENDER', 'RENDER_SERVICE_ID', 'DYNO', 'FLY_APP_NAME', 'K_SERVICE',
              'VERCEL', 'AWS_EXECUTION_ENV', 'WEBSITE_INSTANCE_ID')
    modes = ('APP_ENV', 'ENV', 'ENVIRONMENT', 'FLASK_ENV', 'NODE_ENV')
    if any(environ.get(key) for key in hosted) or any(
            environ.get(key, '').lower() in ('production', 'prod', 'staging') for key in modes):
        raise RuntimeError('Local demo is forbidden in hosted, staging or production environments.')
    if environ.get('SERVICEHUB_ENABLE_BANK_QR', '0') != '0':
        raise RuntimeError('Disable bank QR for the local demo: SERVICEHUB_ENABLE_BANK_QR=0.')
    if environ.get('SERVICEHUB_ADMIN_EMAIL') or environ.get('SERVICEHUB_ADMIN_PASSWORD'):
        raise RuntimeError('Use an environment without admin credentials for this six-account local demo.')
