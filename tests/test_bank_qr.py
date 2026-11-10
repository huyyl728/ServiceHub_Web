"""Bank QR integration tests: no bank calls or real money are involved."""
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]

class BankQRTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='servicehub-bankqr-')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
        cls.base=f'http://127.0.0.1:{port}'
        env=dict(os.environ,SERVICEHUB_HOST='127.0.0.1',SERVICEHUB_PORT=str(port),
                 SERVICEHUB_DB_PATH=str(Path(cls.tmp.name)/'data.db'),
                 SERVICEHUB_ENABLE_BANK_QR='1',SERVICEHUB_BANK_BIN='970436',
                 SERVICEHUB_BANK_ACCOUNT='0000000000',SERVICEHUB_BANK_NAME='NGUYEN VAN DEMO')
        cls.proc=subprocess.Popen([sys.executable,'tests/fixture_server.py'],cwd=ROOT,env=env,
                                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                if cls.proc.poll() is not None: raise RuntimeError('Test server exited')
                try:
                    if cls.request('/api/health')[0]==200:break
                except (OSError,urllib.error.URLError):time.sleep(.1)
            else: raise RuntimeError('Test server startup timeout')
            cls.user=cls.login('huy@servicehub.local','Huy@12345')
            cls.owner=cls.login('owner@servicehub.local','Owner@12345')
            cls.admin=cls.login('admin@servicehub.local','Admin@12345')
        except Exception:
            cls.tearDownClass();raise

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'proc'):
            cls.proc.terminate()
            try:cls.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:cls.proc.kill();cls.proc.wait()
        if hasattr(cls,'tmp'):cls.tmp.cleanup()

    @classmethod
    def request(cls,path,method='GET',data=None,token=None):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        request=urllib.request.Request(cls.base+path,
             data=json.dumps(data).encode() if data is not None else None, headers=headers,method=method)
        try:
            with urllib.request.urlopen(request,timeout=10) as response:
                return response.status,json.load(response)
        except urllib.error.HTTPError as error:
            return error.code,json.loads(error.read())

    @classmethod
    def login(cls,email,password):
        code,body=cls.request('/api/auth/login','POST',{'email':email,'password':password})
        if code!=200:raise AssertionError(body)
        return body['data']['token']

    def test_configuration_and_auth(self):
        self.assertEqual(self.request('/api/bank-qr/config')[0],401)
        code,res=self.request('/api/bank-qr/config',token=self.user)
        self.assertEqual(code,200)
        self.assertTrue(res['data']['configured'])
        self.assertEqual(res['data']['bank_bin'],'970436')
        self.assertEqual(self.request('/api/bank-qr/requests',method='POST',data={'amount':10000,'request_id':'test-auth-01'})[0],401)

    def test_invalid_amount_and_request(self):
        for amount in [0,1000,5000001,-5,1.2,True,'10.5','']:
            code,_=self.request('/api/bank-qr/requests','POST',{'amount':amount,'request_id':'test-invalid-1'},self.user)
            self.assertEqual(code,400,amount)
        code,_=self.request('/api/bank-qr/requests','POST',{'amount':50000,'request_id':'bad!'},self.user)
        self.assertEqual(code,400)

    def test_create_idempotency_and_no_wallet_credit(self):
        start=self.request('/api/me',token=self.user)[1]['data']['wallet']
        body={'amount':69000,'request_id':'test-idempotent-qr-a'}
        code,first=self.request('/api/bank-qr/requests','POST',body,self.user)
        self.assertEqual(code,201,first)
        self.assertEqual(first['data']['status'],'pending')
        self.assertTrue(first['data']['qr_url'].startswith('https://img.vietqr.io/image/970436-0000000000-compact2.png?'))
        self.assertIn(first['data']['reference'],first['data']['qr_url'])
        self.assertIn('amount=69000',first['data']['qr_url'])
        code,again=self.request('/api/bank-qr/requests','POST',body,self.user)
        self.assertEqual(code,200)
        self.assertEqual(again['data']['id'],first['data']['id'])
        code,otheramount=self.request('/api/bank-qr/requests','POST',{'amount':71000,'request_id':'test-idempotent-qr-a'},self.user)
        self.assertEqual(code,409)
        self.assertEqual(otheramount['error']['code'],'REQUEST_CONFLICT')
        self.assertEqual(self.request('/api/me',token=self.user)[1]['data']['wallet'],start)

    def test_requests_scoped_to_customer(self):
        self.request('/api/bank-qr/requests','POST',{'amount':78000,'request_id':'test-scope-customer'},self.user)
        self.request('/api/bank-qr/requests','POST',{'amount':81000,'request_id':'test-scope-owner'},self.owner)
        user_ids={x['reference'] for x in self.request('/api/bank-qr/requests/me',token=self.user)[1]['data']}
        owner_ids={x['reference'] for x in self.request('/api/bank-qr/requests/me',token=self.owner)[1]['data']}
        self.assertTrue(user_ids and owner_ids)
        self.assertTrue(user_ids.isdisjoint(owner_ids))

    def test_admin_verification_and_duplicate_bank_reference(self):
        start=self.request('/api/me',token=self.user)[1]['data']['wallet']
        admin_start=self.request('/api/me',token=self.admin)[1]['data']['wallet']
        c,first=self.request('/api/bank-qr/requests','POST',{'amount':91000,'request_id':'test-confirm-first'},self.user)
        self.assertEqual(c,201)
        c,second=self.request('/api/bank-qr/requests','POST',{'amount':92000,'request_id':'test-confirm-second'},self.user)
        self.assertEqual(c,201)
        id1=first['data']['id'];id2=second['data']['id']
        target=f'/api/admin/bank-qr/requests/{id1}/confirm'
        self.assertEqual(self.request('/api/admin/bank-qr/requests',token=self.owner)[0],403)
        self.assertEqual(self.request(target,'POST',{'verified':True,'bank_transaction_ref':'DUMMYTEST123456'},self.owner)[0],403)
        self.assertEqual(self.request(target,'POST',{'verified':False,'bank_transaction_ref':'DUMMYTEST123456'},self.admin)[0],400)
        self.assertEqual(self.request('/api/me',token=self.user)[1]['data']['wallet'],start)
        code,body=self.request(target,'POST',{'verified':True,'bank_transaction_ref':'DUMMYTEST123456'},self.admin)
        self.assertEqual(code,200,body)
        self.assertEqual(self.request(target,'POST',{'verified':True,'bank_transaction_ref':'DUMMYTEST123456'},self.admin)[0],409)
        self.assertEqual(self.request(f'/api/admin/bank-qr/requests/{id2}/confirm','POST',{'verified':True,'bank_transaction_ref':'DUMMYTEST123456'},self.admin)[0],409)
        profile=self.request('/api/me',token=self.user)[1]['data']
        self.assertEqual(profile['wallet'],start+91000)
        entries=[t for t in profile['transactions'] if t['reference']==first['data']['reference']]
        self.assertEqual(len(entries),1)
        self.assertEqual((entries[0]['kind'],entries[0]['amount']),('bank_qr_topup',91000))
        self.assertEqual(self.request('/api/me',token=self.admin)[1]['data']['wallet'],admin_start)
        mine=self.request('/api/bank-qr/requests/me',token=self.user)[1]['data']
        self.assertEqual(next(r for r in mine if r['id']==id1)['status'],'confirmed')
        self.assertEqual(next(r for r in mine if r['id']==id2)['status'],'pending')
        notifications=self.request('/api/notifications',token=self.user)[1]['data']
        credits=[n for n in notifications if first['data']['reference'] in n['message'] and n['title']=='Đã cộng tiền vào ví']
        self.assertEqual(len(credits),1)

    def test_concurrent_confirmation_only_credits_once(self):
        start=self.request('/api/me',token=self.user)[1]['data']['wallet']
        _,result=self.request('/api/bank-qr/requests','POST',{'amount':99000,'request_id':'test-concurrent-qr'},self.user)
        target=f"/api/admin/bank-qr/requests/{result['data']['id']}/confirm"
        def confirm(_):
            return self.request(target,'POST',{'verified':True,'bank_transaction_ref':'CONCURRENT123456'},self.admin)[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(confirm,range(2))),[200,409])
        self.assertEqual(self.request('/api/me',token=self.user)[1]['data']['wallet'],start+99000)

    def test_credit_failure_rolls_back_confirmation(self):
        start=self.request('/api/me',token=self.user)[1]['data']['wallet']
        _,result=self.request('/api/bank-qr/requests','POST',{'amount':98000,'request_id':'test-rollback-qr'},self.user)
        target=f"/api/admin/bank-qr/requests/{result['data']['id']}/confirm"
        db=Path(self.tmp.name)/'data.db'
        with sqlite3.connect(db) as c:
            c.execute("CREATE TRIGGER fail_qr_credit BEFORE INSERT ON wallet_transactions WHEN NEW.kind='bank_qr_topup' BEGIN SELECT RAISE(ABORT, 'test credit failure'); END")
        try:
            self.assertEqual(self.request(target,'POST',{'verified':True,'bank_transaction_ref':'ROLLBACK123456'},self.admin)[0],500)
            profile=self.request('/api/me',token=self.user)[1]['data']
            self.assertEqual(profile['wallet'],start)
            self.assertFalse(any(t['reference']==result['data']['reference'] for t in profile['transactions']))
            with sqlite3.connect(db) as c:
                self.assertEqual(c.execute('SELECT status,bank_transaction_ref,reviewed_at FROM bank_qr_requests WHERE id=?',(result['data']['id'],)).fetchone(),('pending',None,None))
                self.assertEqual(c.execute("SELECT COUNT(*) FROM notifications WHERE message LIKE ?",('%'+result['data']['reference']+'%',)).fetchone()[0],0)
        finally:
            with sqlite3.connect(db) as c:
                c.execute('DROP TRIGGER fail_qr_credit')
        self.assertEqual(self.request(target,'POST',{'verified':True,'bank_transaction_ref':'ROLLBACK123456'},self.admin)[0],200)
        self.assertEqual(self.request('/api/me',token=self.user)[1]['data']['wallet'],start+98000)

    def test_admin_reject_and_notification(self):
        start=self.request('/api/me',token=self.user)[1]['data']['wallet']
        _,result=self.request('/api/bank-qr/requests','POST',{'amount':93000,'request_id':'test-reject-one'},self.user)
        target=f"/api/admin/bank-qr/requests/{result['data']['id']}/reject"
        self.assertEqual(self.request(target,'POST',{'reason':'a'},self.admin)[0],400)
        code,_=self.request(target,'POST',{'reason':'Không có giao dịch khớp sao kê.'},self.admin)
        self.assertEqual(code,200)
        self.assertEqual(self.request(target,'POST',{'reason':'Không có giao dịch khớp sao kê.'},self.admin)[0],409)
        notifications=self.request('/api/notifications',token=self.user)[1]['data']
        self.assertTrue(any('Chuyển khoản' in n['title'] for n in notifications))
        self.assertEqual(self.request('/api/me',token=self.user)[1]['data']['wallet'],start)


class BankQRCreditMigrationTests(unittest.TestCase):
    def test_startup_repairs_legacy_confirmations_once(self):
        import server
        from fixture_server import seed_demo_data
        with tempfile.TemporaryDirectory(prefix='servicehub-credit-migration-') as tmp:
            with patch.multiple(server,DB_PATH=Path(tmp)/'legacy.db',ADMIN_EMAIL='',ADMIN_PASSWORD=''):
                server.seed()
                seed_demo_data()
                with server.connect() as c:
                    users=[r['id'] for r in c.execute('SELECT id FROM users ORDER BY id LIMIT 2')]
                    before={r['user_id']:r['balance'] for r in c.execute('SELECT * FROM wallets')}
                    for i,(uid,status,amount) in enumerate([(users[0],'confirmed',10000),(users[0],'confirmed',20000),(users[1],'confirmed',30000),(users[1],'pending',40000),(users[1],'rejected',50000)]):
                        c.execute('INSERT INTO bank_qr_requests(user_id,amount,reference,request_id,status,bank_transaction_ref,reviewed_by,reviewed_at) VALUES(?,?,?,?,?,?,?,?)',
                                  (uid,amount,'LEGACY'+str(i),'legacy-key-'+str(i),status,'BANKLEGACY'+str(i) if status=='confirmed' else None,users[0],server.now_iso()))
                server.seed()
                server.seed()
                with server.connect() as c:
                    for uid in users:
                        self.assertEqual(c.execute('SELECT balance FROM wallets WHERE user_id=?',(uid,)).fetchone()[0],before[uid]+30000)
                    self.assertEqual(c.execute("SELECT COUNT(*),SUM(amount) FROM wallet_transactions WHERE kind='bank_qr_topup'").fetchone()[:],(3,60000))
                    self.assertEqual(c.execute("SELECT COUNT(*) FROM notifications WHERE title='Đã cộng tiền vào ví'").fetchone()[0],3)
                    self.assertEqual(c.execute("SELECT COUNT(*) FROM audit_logs WHERE action='wallet_bank_qr_topup'").fetchone()[0],3)

if __name__=='__main__':unittest.main()
