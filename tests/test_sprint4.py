"""Isolated Sprint 4 API integration tests with a disposable SQLite database.
These tests start their own server and do not touch servicehub.db.
"""
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
import uuid
from datetime import datetime, timedelta
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
