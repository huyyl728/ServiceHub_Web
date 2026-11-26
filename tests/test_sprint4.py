"""Isolated Sprint 4 API integration tests with a disposable SQLite database.
These tests start their own server and do not touch servicehub.db.
"""
import json
import hashlib
import sqlite3
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Sprint4IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='servicehub-sprint4-test-')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.base = f'http://127.0.0.1:{port}'
        env = dict(os.environ, SERVICEHUB_HOST='127.0.0.1', SERVICEHUB_PORT=str(port),
                   SERVICEHUB_DB_PATH=str(Path(cls.temp.name) / 'isolated.db'))
        cls.process = subprocess.Popen([sys.executable, 'tests/fixture_server.py'], cwd=ROOT, env=env,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(100):
            if cls.process.poll() is not None:
                output = cls.process.stderr.read().decode(errors='replace')
                raise RuntimeError('Test server failed to start: ' + output)
            try:
                code, _ = cls.request('/api/health')
                if code == 200:
                    break
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        else:
            cls.process.terminate()
            cls.process.wait(timeout=5)
            raise RuntimeError('Test server did not start')
        cls.customer = cls.login('huy@servicehub.local', 'Huy@12345')
        cls.owner = cls.login('owner@servicehub.local', 'Owner@12345')
        cls.admin = cls.login('admin@servicehub.local', 'Admin@12345')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'process'):
            cls.process.terminate()
            try:
                cls.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.process.kill()
                cls.process.wait(timeout=5)
            if cls.process.stderr:
                cls.process.stderr.close()
        if hasattr(cls, 'temp'):
            cls.temp.cleanup()

    @classmethod
    def request(cls, path, method='GET', body=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        request = urllib.request.Request(cls.base + path,
            data=json.dumps(body).encode('utf-8') if body is not None else None,
            headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    @classmethod
    def login(cls, email, password):
        code, result = cls.request('/api/auth/login', 'POST', {'email': email, 'password': password})
        if code != 200:
            raise AssertionError(result)
        return result['data']['token']

    def test_admin_reports_and_audit_are_protected(self):
        for endpoint in ('/api/admin/reports', '/api/admin/audit', '/api/admin/businesses'):
            self.assertEqual(self.request(endpoint, token=self.owner)[0], 403)
            code, body = self.request(endpoint, token=self.admin)
            self.assertEqual(code, 200, body)
            self.assertTrue(body['success'])
        report = self.request('/api/admin/reports', token=self.admin)[1]['data']
        self.assertGreaterEqual(report['active_services'], 1)
        self.assertIsInstance(report['booking_statuses'], dict)

    def test_business_moderation_and_catalog_visibility(self):
        businesses = self.request('/api/admin/businesses', token=self.admin)[1]['data']
        selected = next(b for b in businesses if b['name'].startswith('Bếp Nhà Mình'))
        bid = selected['id']
        before = self.request('/api/services')[1]['data']
        self.assertTrue(any(s['business_id'] == bid for s in before))
        try:
            code, response = self.request(f'/api/admin/businesses/{bid}/status', 'POST',
                                          {'status': 'suspended'}, self.admin)
            self.assertEqual(code, 200, response)
            after = self.request('/api/services')[1]['data']
            self.assertFalse(any(s['business_id'] == bid for s in after))
            self.assertEqual(self.request('/api/businesses/' + str(bid))[0], 404)
            self.assertEqual(self.request(f'/api/admin/businesses/{bid}/status', 'POST',
                                           {'status': 'active'}, self.customer)[0], 403)
        finally:
            self.assertEqual(self.request(f'/api/admin/businesses/{bid}/status', 'POST',
                                         {'status': 'active'}, self.admin)[0], 200)
        restored = self.request('/api/services')[1]['data']
        self.assertTrue(any(s['business_id'] == bid for s in restored))

    def test_notifications_read_and_ownership(self):
        services = self.request('/api/services')[1]['data']
        service = next(x for x in services if x['business_name'] == 'Huy Football')
        date = (datetime.now() + timedelta(days=21)).strftime('%Y-%m-%d')
        slots = self.request(f'/api/services/{service["id"]}/availability?date={date}', token=self.customer)[1]['data']
        self.assertTrue(slots)
        code, booking = self.request('/api/bookings', 'POST', {
            'service_id': service['id'], 'date': date, 'start_time': slots[-1]['start_time']}, self.customer)
        self.assertEqual(code, 201, booking)
        notifications = self.request('/api/notifications', token=self.customer)[1]['data']
        self.assertTrue(notifications)
        nid = notifications[0]['id']
        self.assertEqual(self.request(f'/api/notifications/{nid}/read', 'POST', {}, self.owner)[0], 404)
        self.assertEqual(self.request(f'/api/notifications/{nid}/read', 'POST', {}, self.customer)[0], 200)
        self.assertEqual(self.request('/api/notifications/read-all', 'POST', {}, self.customer)[0], 200)
        self.assertEqual(self.request('/api/notifications/unread-count', token=self.customer)[1]['data']['unread'], 0)


    def test_owner_memberships_are_scoped(self):
        owner_businesses = self.request('/api/businesses/managed', token=self.owner)[1]['data']
        memberships = self.request('/api/memberships/me', token=self.customer)[1]['data']
        bid = next(b['id'] for b in owner_businesses if any(m['business_id'] == b['id'] for m in memberships))
        program = next(m for m in memberships if m['business_id'] == bid)
        code, data = self.request(f'/api/memberships/{program["id"]}/join', 'POST', {}, self.customer)
        self.assertEqual(code, 200, data)
        code, members = self.request(f'/api/owner/members?business_id={bid}', token=self.owner)
        self.assertEqual(code, 200, members)
        self.assertTrue(any(m['member_name'] == 'Nguyễn Thành Huy' for m in members['data']))
        self.assertEqual(self.request(f'/api/owner/members?business_id={bid}', token=self.customer)[0], 403)

    def test_booking_creates_notifications_for_both_sides(self):
        services = self.request('/api/services')[1]['data']
        service = next(s for s in services if s['business_name'] == 'Huy Football')
        date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        availability = self.request(f'/api/services/{service["id"]}/availability?date={date}',
                                    token=self.customer)[1]['data']
        self.assertTrue(availability)
        code, data = self.request('/api/bookings', 'POST', {
            'service_id': service['id'], 'date': date,
            'start_time': availability[0]['start_time']}, self.customer)
        self.assertEqual(code, 201, data)
        booking_id = data['data']['id']
        for token in (self.customer, self.owner):
            messages = self.request('/api/notifications', token=token)[1]['data']
            self.assertTrue(any(f'#{booking_id}' in n['message'] for n in messages))

    def test_welcome_voucher_member_counts_points_and_owner_reply(self):
        # Tạo khách kiểm thử riêng, không đụng tài khoản hoặc dữ liệu thật.
        email='member-'+uuid.uuid4().hex+'@example.test'
        customer_token=uuid.uuid4().hex
        expiry=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat(timespec='seconds')
        with sqlite3.connect(Path(self.temp.name)/'isolated.db') as c:
            uid=c.execute('''INSERT INTO users(name,email,password_hash)
                             VALUES(?,?,?)''',
                          ('Khách hội viên mới',email,'fixture-hash-unused')).lastrowid
            c.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                      (hashlib.sha256(customer_token.encode()).hexdigest(),uid,expiry))
            c.commit()

        programs=self.request('/api/memberships/me',token=customer_token)[1]['data']
        program=next(p for p in programs if p['business_name']=='Huy Football')
        business_id=program['business_id']
        program_id=program['id']
        code,updated=self.request('/api/owner/membership','PUT',{
            'business_id':business_id,'name':'Huy Football Member',
            'description':'Ưu đãi dành cho khách đã đăng ký',
            'benefits':'Quyền lợi được quản lý bởi cơ sở',
            'points_per_currency':2,'auto_approve_bookings':False,
            'welcome_discount_percent':20,'voucher_valid_days':30,'active':True
        },self.owner)
        self.assertEqual(code,200,updated)
        self.assertEqual(self.request('/api/owner/membership','PUT',{
            'business_id':business_id,'name':'Huy Football Member',
            'welcome_discount_percent':51
        },self.owner)[0],400)
        before=self.request(f'/api/owner/membership?business_id={business_id}',
                            token=self.owner)[1]['data']['member_count']

        code,joined=self.request(f'/api/memberships/{program_id}/join','POST',{},customer_token)
        self.assertEqual(code,200,joined)
        self.assertTrue(joined['data']['joined'])
        self.assertTrue(joined['data']['voucher_code'])
        code,second=self.request(f'/api/memberships/{program_id}/join','POST',{},customer_token)
        self.assertEqual(code,200,second)
        self.assertFalse(second['data']['joined'])
        membership=self.request(f'/api/owner/membership?business_id={business_id}',
                                token=self.owner)[1]['data']
        self.assertEqual(membership['member_count'],before+1)
        self.assertEqual(self.request(f'/api/owner/membership?business_id={business_id}',
                                      token=customer_token)[0],403)

        vouchers=self.request('/api/vouchers/me',token=customer_token)[1]['data']
        self.assertEqual(len(vouchers),1)
        voucher=vouchers[0]
        self.assertEqual(voucher['discount_percent'],20)
        self.assertIsNone(voucher['used_booking_id'])
        other_vouchers=self.request('/api/vouchers/me',token=self.owner)[1]['data']
        self.assertFalse(any(x['code']==voucher['code'] for x in other_vouchers))
        services=self.request('/api/services')[1]['data']
        service=next(s for s in services if s['business_id']==business_id and
                     s['name']=='Sân bóng 5 người')
        date=(datetime.now()+timedelta(days=75)).strftime('%Y-%m-%d')
        wrong_service=next(s for s in services if s['business_id']!=business_id
                          and s['price']>0)
        self.assertEqual(self.request('/api/bookings','POST',{
            'service_id':wrong_service['id'],'date':date,
            'start_time':'13:00','voucher_id':voucher['id']
        },customer_token)[0],409)
        # Mã hết hạn không được dùng; khôi phục hạn dùng trên DB thử nghiệm.
        with sqlite3.connect(Path(self.temp.name)/'isolated.db') as c:
            c.execute('UPDATE membership_vouchers SET expires_at=0 WHERE id=?',(voucher['id'],))
            c.commit()
        self.assertEqual(self.request('/api/bookings','POST',{
            'service_id':service['id'],'date':date,
            'start_time':'13:00','voucher_id':voucher['id']
        },customer_token)[0],409)
        with sqlite3.connect(Path(self.temp.name)/'isolated.db') as c:
            c.execute('UPDATE membership_vouchers SET expires_at=? WHERE id=?',
                      (voucher['expires_at'],voucher['id']))
            c.commit()
        def book(hour,voucher_id):
            return self.request('/api/bookings','POST',{
                'service_id':service['id'],'date':date,'start_time':hour,
                'voucher_id':voucher_id
            },customer_token)
        code,first=book('15:00',voucher['id'])
        self.assertEqual(code,201,first)
        self.assertEqual(first['data']['discount_amount'],50000)
        self.assertEqual(first['data']['price'],200000)
        self.assertEqual(book('17:00',voucher['id'])[0],409)
        first_id=first['data']['id']
        self.assertEqual(self.request(f'/api/bookings/{first_id}/cancel','POST',
                                      {},customer_token)[0],200)
        self.assertIsNone(self.request('/api/vouchers/me',token=customer_token)
                          [1]['data'][0]['used_booking_id'])
        code,final=book('16:00',voucher['id'])
        self.assertEqual(code,201,final)
        final_id=final['data']['id']
        self.assertEqual(self.request(f'/api/owner/bookings/{business_id}/confirm',
                                      'POST',{'booking_id':final_id},self.owner)[0],200)
        self.assertEqual(self.request(f'/api/owner/bookings/{business_id}/complete',
                                      'POST',{'booking_id':final_id},self.owner)[0],200)
        self.assertEqual(self.request(f'/api/owner/bookings/{business_id}/complete',
                                      'POST',{'booking_id':final_id},self.owner)[0],409)
        program_after=next(p for p in self.request('/api/memberships/me',
                            token=customer_token)[1]['data'] if p['id']==program_id)
        self.assertEqual(program_after['points'],400)

        code,review=self.request('/api/reviews','POST',
            {'booking_id':final_id,'rating':5,'comment':'Dịch vụ rất tốt'},customer_token)
        self.assertEqual(code,201,review)
        review_id=review['data']['id']
        reply_route=f'/api/owner/reviews/{review_id}/reply'
        self.assertEqual(self.request(reply_route,'POST',
                                      {'reply':'Cảm ơn bạn đã ghé!'},customer_token)[0],403)
        second_owner_token=uuid.uuid4().hex
        with sqlite3.connect(Path(self.temp.name)/'isolated.db') as c:
            second_owner_id=c.execute('INSERT INTO users(name,email,password_hash) VALUES(?,?,?)',
                        ('Chủ cơ sở khác','other-owner-'+uuid.uuid4().hex+'@example.test',
                         'fixture-hash-unused')).lastrowid
            c.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                      (hashlib.sha256(second_owner_token.encode()).hexdigest(),
                       second_owner_id,expiry))
            c.commit()
        self.assertEqual(self.request(reply_route,'POST',
                                      {'reply':'Không phải cơ sở của tôi'},second_owner_token)[0],403)
        self.assertEqual(self.request(reply_route,'POST',
                                      {'reply':'Cảm ơn bạn đã ghé!'},self.owner)[0],200)
        owner_reviews=self.request(f'/api/owner/reviews?business_id={business_id}',
                                   token=self.owner)[1]['data']
        self.assertTrue(any(x['id']==review_id and
                            x['owner_reply']=='Cảm ơn bạn đã ghé!' for x in owner_reviews))
        public=self.request(f'/api/reviews?business_id={business_id}')[1]['data']['reviews']
        self.assertTrue(any(x['id']==review_id and
                            x['owner_reply']=='Cảm ơn bạn đã ghé!' for x in public))
        admin=self.request('/api/admin/stats',token=self.admin)[1]['data']
        self.assertGreaterEqual(admin['unique_members'],1)
        listing=self.request('/api/admin/businesses',token=self.admin)[1]['data']
        self.assertTrue(any(x['id']==business_id and
                            x['member_count']>=1 for x in listing))
        details=self.request(f'/api/admin/businesses/{business_id}/detail',
                             token=self.admin)[1]['data']
        self.assertGreaterEqual(details['business']['member_count'],1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
