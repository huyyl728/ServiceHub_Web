"""Small smoke tests. Start server in another terminal, then run: python3 -m unittest discover -s tests"""
import json, unittest, urllib.request, urllib.error
BASE=__import__('os').environ.get('SERVICEHUB_TEST_BASE','http://127.0.0.1:8000')

def call(path, method='GET', data=None, token=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request(BASE+path, data=json.dumps(data).encode() if data is not None else None, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req,timeout=3) as r: return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code,json.loads(e.read())

class ServiceHubSmokeTests(unittest.TestCase):
    def test_health(self):
        status,body=call('/api/health'); self.assertEqual(status,200); self.assertTrue(body['success'])
    def test_public_services(self):
        status,body=call('/api/services'); self.assertEqual(status,200); self.assertGreaterEqual(len(body['data']),1)
    def test_login(self):
        status,body=call('/api/auth/login','POST',{'email':'huy@servicehub.local','password':'Huy@12345'}); self.assertEqual(status,200); self.assertIn('token',body['data'])
    def test_bad_login(self):
        status,body=call('/api/auth/login','POST',{'email':'huy@servicehub.local','password':'wrong'}); self.assertEqual(status,401); self.assertFalse(body['success'])

if __name__=='__main__': unittest.main()
