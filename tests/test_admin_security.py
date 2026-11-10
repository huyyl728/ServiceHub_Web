"""Public demo retirement, private admin bootstrap and static-file boundaries."""
import hashlib
import json
from pathlib import Path
import secrets
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
import server


class AdminSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='servicehub-admin-security-')
        self.root=Path(self.tmp.name)
        (self.root/'static').mkdir()
        (self.root/'static'/'index.html').write_text('public test page')
        (self.root/'private-test.txt').write_text('private test file')
        (self.root/'static'/'outside.txt').symlink_to(self.root/'private-test.txt')
        self.patch=patch.multiple(server,DB_PATH=self.root/'test.db',ROOT=self.root,
                                  ADMIN_EMAIL='',ADMIN_PASSWORD='')
        self.patch.start()
        server.seed()
        self.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True)
        self.thread.start()
        self.base=f'http://127.0.0.1:{self.http.server_port}'

    def tearDown(self):
        self.http.shutdown();self.http.server_close();self.thread.join(timeout=5)
        self.patch.stop();self.tmp.cleanup()

    def request(self,path,method='GET',data=None,token=None):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,
                                   method=method,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=5) as response:
                body=response.read()
                return response.status,json.loads(body) if 'application/json' in response.headers.get('Content-Type','') else body
        except urllib.error.HTTPError as error:
            with error:return error.code,json.load(error)

    def provision(self,email='private-admin@example.com',password='Private-Test-Password-123!'):
        with patch.multiple(server,ADMIN_EMAIL=email,ADMIN_PASSWORD=password):server.seed()
        return email,password

    def login(self,email,password):
        return self.request('/api/auth/login','POST',{'email':email,'password':password})

    def test_fresh_start_has_no_demo_accounts_and_register_cannot_grant_admin(self):
        with server.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0],0)
        for email in server.LEGACY_DEMO_EMAILS:
            self.assertEqual(self.login(email,'Admin@12345')[0],401)
            self.assertEqual(self.request('/api/auth/register','POST',{'name':'Fake Admin','email':email,'password':'Password-123'})[0],400)
        code,body=self.request('/api/auth/register','POST',{'name':'Normal User','email':'customer@example.com','password':'Password-123','is_admin':1})
        self.assertEqual(code,200);self.assertEqual(body['data']['user']['is_admin'],0)
        self.assertEqual(self.request('/api/admin/stats',token=body['data']['token'])[0],403)

    def test_bootstrap_admin_login_idempotency_and_password_rotation(self):
        email,password=self.provision()
        code,body=self.login(email,password);self.assertEqual(code,200)
        token=body['data']['token']
        self.assertEqual(self.request('/api/admin/stats',token=token)[0],200)
        self.provision()
        self.assertEqual(self.request('/api/admin/stats',token=token)[0],200)
        with server.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM users WHERE is_admin=1').fetchone()[0],1)
        self.provision(password='Rotated-Test-Password-456!')
        self.assertEqual(self.login(email,password)[0],401)
        self.assertEqual(self.request('/api/me',token=token)[0],401)
        self.assertEqual(self.login(email,'Rotated-Test-Password-456!')[0],200)

    def test_migration_disables_old_logins_and_sessions_preserves_money(self):
        legacy_passwords=['Admin@12345','Huy@12345','Owner@12345']
        tokens=[]
        with server.connect() as c:
            c.execute("DELETE FROM app_settings WHERE key='demo_logins_retired_v1'")
            for email,password in zip(server.LEGACY_DEMO_EMAILS,legacy_passwords):
                uid=c.execute('INSERT INTO users(name,email,password_hash,is_admin) VALUES(?,?,?,?)',
                              ('Legacy',email,server.hash_password(password),int(email.startswith('admin@')))).lastrowid
                c.execute('INSERT INTO wallets(user_id,balance) VALUES(?,123456)',(uid,))
                token=secrets.token_urlsafe(20);tokens.append(token)
                c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),uid,'2099-01-01T00:00:00+00:00'))
        self.provision()
        for email,password,token in zip(server.LEGACY_DEMO_EMAILS,legacy_passwords,tokens):
            self.assertEqual(self.login(email,password)[0],401)
            self.assertEqual(self.request('/api/me',token=token)[0],401)
        with server.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users WHERE login_enabled=0').fetchone()[0],3)
            self.assertEqual(c.execute('SELECT SUM(balance) FROM wallets').fetchone()[0],3*123456)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users WHERE is_admin=1').fetchone()[0],1)

    def test_disabled_account_stays_blocked_even_with_a_new_session(self):
        _,body=self.request('/api/auth/register','POST',{'name':'Disabled User','email':'disabled@example.com','password':'Password-123'})
        with server.connect() as c:c.execute('UPDATE users SET login_enabled=0 WHERE id=?',(body['data']['user']['id'],))
        self.assertEqual(self.request('/api/me',token=body['data']['token'])[0],401)
        self.assertEqual(self.login('disabled@example.com','Password-123')[0],401)

    def test_admin_email_collision_never_promotes_customer(self):
        self.request('/api/auth/register','POST',{'name':'Customer','email':'customer@example.com','password':'Password-123'})
        with self.assertRaises(RuntimeError):self.provision(email='customer@example.com')
        with server.connect() as c:self.assertEqual(c.execute('SELECT is_admin FROM users WHERE email=?',('customer@example.com',)).fetchone()[0],0)

    def test_invalid_admin_configuration_fails_without_partial_admin(self):
        for email,password in [('admin@example.com',''),('','Password-123456789'),('invalid','Password-123456789'),('admin@example.com','short')]:
            with self.subTest(email=email),self.assertRaises(RuntimeError):self.provision(email,password)
        with server.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0],0)

    def test_reuse_legacy_admin_email_only_with_new_secret(self):
        with server.connect() as c:
            c.execute("DELETE FROM app_settings WHERE key='demo_logins_retired_v1'")
            uid=c.execute('INSERT INTO users(name,email,password_hash,is_admin) VALUES(?,?,?,1)',
                          ('Old Admin','admin@servicehub.local',server.hash_password('Admin@12345'))).lastrowid
            c.execute('INSERT INTO wallets(user_id,balance) VALUES(?,100)',(uid,))
        self.provision('admin@servicehub.local')
        self.assertEqual(self.login('admin@servicehub.local','Admin@12345')[0],401)
        self.assertEqual(self.login('admin@servicehub.local','Private-Test-Password-123!')[0],200)

    def test_static_paths_cannot_escape_public_directory(self):
        self.assertEqual(self.request('/')[0],200)
        self.assertEqual(self.request('/static/index.html')[0],200)
        for path in ['/static/../private-test.txt','/static/../test.db','/static/../../private-test.txt','/static/outside.txt','/static/%2e%2e/private-test.txt']:
            with self.subTest(path=path):self.assertEqual(self.request(path)[0],404)

    def test_frontend_has_no_demo_login_buttons_or_credentials(self):
        project=Path(__file__).resolve().parents[1]
        html=(project/'static/index.html').read_text();js=(project/'static/js/app.js').read_text()
        for fragment in ['data-demo-login','Admin@12345','Huy@12345','Owner@12345','demoLogin']:
            self.assertNotIn(fragment,html+js)


if __name__=='__main__':unittest.main()
