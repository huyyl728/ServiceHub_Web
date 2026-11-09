"""Bank QR integration tests: no bank calls or real money are involved."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
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
        cls.proc=subprocess.Popen([sys.executable,'server.py'],cwd=ROOT,env=env,
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
        c,first=self.request('/api/bank-qr/requests','POST',{'amount':91000,'request_id':'test-confirm-first'},self.user)
        self.assertEqual(c,201)
        c,second=self.request('/api/bank-qr/requests','POST',{'amount':92000,'request_id':'test-confirm-second'},self.user)
        self.assertEqual(c,201)
        id1=first['data']['id'];id2=second['data']['id']
        target=f'/api/admin/bank-qr/requests/{id1}/confirm'
        self.assertEqual(self.request('/api/admin/bank-qr/requests',token=self.owner)[0],403)
        self.assertEqual(self.request(target,'POST',{'verified':True,'bank_transaction_ref':'DUMMYTEST123456'},self.owner)[0],403)
        self.assertEqual(self.request(target,'POST',{'verified':False,'bank_transaction_ref':'DUMMYTEST123456'},self.admin)[0],400)
        start=self.request('/api/me',token=self.user)[1]['data']['wallet']
        code,body=self.request(target,'POST',{'verified':True,'bank_transaction_ref':'DUMMYTEST123456'},self.admin)
        self.assertEqual(code,200,body)
        self.assertEqual(self.request(target,'POST',{'verified':True,'bank_transaction_ref':'DUMMYTEST123456'},self.admin)[0],409)
        self.assertEqual(self.request(f'/api/admin/bank-qr/requests/{id2}/confirm','POST',{'verified':True,'bank_transaction_ref':'DUMMYTEST123456'},self.admin)[0],409)
        self.assertEqual(self.request('/api/me',token=self.user)[1]['data']['wallet'],start)
        mine=self.request('/api/bank-qr/requests/me',token=self.user)[1]['data']
        self.assertEqual(next(r for r in mine if r['id']==id1)['status'],'confirmed')

    def test_admin_reject_and_notification(self):
        _,result=self.request('/api/bank-qr/requests','POST',{'amount':93000,'request_id':'test-reject-one'},self.user)
        target=f"/api/admin/bank-qr/requests/{result['data']['id']}/reject"
        self.assertEqual(self.request(target,'POST',{'reason':'a'},self.admin)[0],400)
        code,_=self.request(target,'POST',{'reason':'Không có giao dịch khớp sao kê.'},self.admin)
        self.assertEqual(code,200)
        self.assertEqual(self.request(target,'POST',{'reason':'Không có giao dịch khớp sao kê.'},self.admin)[0],409)
        notifications=self.request('/api/notifications',token=self.user)[1]['data']
        self.assertTrue(any('Chuyển khoản' in n['title'] for n in notifications))

if __name__=='__main__':unittest.main()
