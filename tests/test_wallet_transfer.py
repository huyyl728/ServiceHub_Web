"""Integration tests for internal demo-wallet transfers. Server must be running."""
import json, os, unittest, urllib.request, urllib.error, uuid
BASE=os.environ.get('SERVICEHUB_TEST_BASE','http://127.0.0.1:8000')
def call(path, method='GET', data=None, token=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
def login(email,password):
    status,body=call('/api/auth/login','POST',{'email':email,'password':password})
    if status!=200: raise AssertionError(body)
    return body['data']['token']
class WalletTransferTests(unittest.TestCase):
    def test_transfer_is_atomic_and_idempotent(self):
        sender=login('huy@servicehub.local','Huy@12345'); recipient=login('owner@servicehub.local','Owner@12345')
        before_s=call('/api/me',token=sender)[1]['data']['wallet']; before_r=call('/api/me',token=recipient)[1]['data']['wallet']
        payload={'recipient_email':'owner@servicehub.local','amount':1000,'request_id':'test-'+uuid.uuid4().hex}
        status,result=call('/api/wallet/transfer','POST',payload,sender); self.assertEqual(status,200,result)
        status,retry=call('/api/wallet/transfer','POST',payload,sender); self.assertEqual(status,200,retry); self.assertTrue(retry['data']['duplicate'])
        after_s=call('/api/me',token=sender)[1]['data']['wallet']; after_r=call('/api/me',token=recipient)[1]['data']['wallet']
        self.assertEqual(before_s-after_s,1000); self.assertEqual(after_r-before_r,1000)
        self.assertTrue(any(x['action']=='wallet_transfer_sent' for x in call('/api/activity/me',token=sender)[1]['data']))
        self.assertTrue(any(x['action']=='wallet_transfer_received' for x in call('/api/activity/me',token=recipient)[1]['data']))
    def test_request_id_cannot_be_reused_for_different_transfer(self):
        token=login('huy@servicehub.local','Huy@12345')
        key='reuse-'+uuid.uuid4().hex
        first={'recipient_email':'owner@servicehub.local','amount':1000,'request_id':key}
        self.assertEqual(call('/api/wallet/transfer','POST',first,token)[0],200)
        changed={'recipient_email':'owner@servicehub.local','amount':2000,'request_id':key}
        status,body=call('/api/wallet/transfer','POST',changed,token)
        self.assertEqual(status,409); self.assertEqual(body['error']['code'],'IDEMPOTENCY_KEY_REUSED')
    def test_reject_self_transfer(self):
        token=login('huy@servicehub.local','Huy@12345')
        status,body=call('/api/wallet/transfer','POST',{'recipient_email':'huy@servicehub.local','amount':1000,'request_id':'self-'+uuid.uuid4().hex},token)
        self.assertEqual(status,400); self.assertEqual(body['error']['code'],'SELF_TRANSFER')
if __name__=='__main__': unittest.main()
