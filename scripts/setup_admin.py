#!/usr/bin/env python3
"""Create private admin configuration locally; never print the generated secret."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]


def write_private(path, text):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    os.fchmod(fd,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(text)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email',required=True)
    args=parser.parse_args()
    email=args.email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254:
        parser.error('Enter a valid email address.')
    secret_path=ROOT/'.env.admin'
    if secret_path.exists():
        parser.error('.env.admin already exists; existing admin credentials were not changed.')
    sys.path.insert(0,str(ROOT))
    import server
    with server.connect() as c:
        if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
            row=c.execute('SELECT is_admin FROM users WHERE email=?',(email,)).fetchone()
            if row and not row['is_admin'] and email!='admin@servicehub.local':
                parser.error('This email belongs to a customer. Choose a separate admin email.')
    password=secrets.token_urlsafe(24)
    settings={'SERVICEHUB_ADMIN_EMAIL':email,'SERVICEHUB_ADMIN_PASSWORD':password}
    block=''.join(f'{key}={value}\n' for key,value in settings.items())
    env_path=ROOT/'.env'
    old=env_path.read_text(encoding='utf-8') if env_path.exists() else ''
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    if server.DB_PATH.exists():
        backup=server.DB_PATH.with_name(server.DB_PATH.stem+'-before-admin-'+stamp+'.db')
        with server.connect() as source,sqlite3.connect(backup) as destination:source.backup(destination)
        backup.chmod(0o600)
    if old:write_private(ROOT/('.env.before-admin-'+stamp+'.bak'),old)
    # Validate/provision first; invalid bootstrap must not overwrite local configuration.
    server.ADMIN_EMAIL=email;server.ADMIN_PASSWORD=password
    server.seed()
    kept=[line for line in old.splitlines() if not re.match(r'^\s*(?:export\s+)?SERVICEHUB_ADMIN_(?:EMAIL|PASSWORD)\s*=',line)]
    write_private(env_path,'\n'.join(kept).rstrip()+'\n\n'+block)
    write_private(secret_path,block)
    print('Admin configured:',email)
    print('Private credentials saved in:',secret_path)
    print('Copy only the two variables in this file to Render Environment; do not commit or share the file.')


if __name__=='__main__':main()
