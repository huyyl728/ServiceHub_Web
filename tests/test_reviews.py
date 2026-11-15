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

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]


class ReviewIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.temp = tempfile.TemporaryDirectory(
            prefix='servicehub-review-tests-'
        )

        cls.addClassCleanup(cls.temp.cleanup)

        cls.db = Path(cls.temp.name) / 'reviews.db'

        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]

        cls.base = f'http://127.0.0.1:{port}'

        env = dict(
            os.environ,
            SERVICEHUB_HOST='127.0.0.1',
            SERVICEHUB_PORT=str(port),
            SERVICEHUB_DB_PATH=str(cls.db),
            SERVICEHUB_LOCAL_DEMO='0',
            SERVICEHUB_ADMIN_EMAIL='',
            SERVICEHUB_ADMIN_PASSWORD=''
        )

        cls.process = subprocess.Popen(
            [sys.executable, 'tests/fixture_server.py'],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        cls.addClassCleanup(cls.stop_server)

        for _ in range(100):

            if cls.process.poll() is not None:
                raise RuntimeError(
                    'Review test server stopped.'
                )

            try:
                code, _ = cls.request('/api/health')

                if code == 200:
                    break

            except OSError:
                time.sleep(0.1)

        else:
            raise RuntimeError(
                'Review test server did not start.'
            )

        # Tài khoản fixture chỉ dành cho database test
        cls.customer = cls.login(
            'huy@servicehub.local',
            'Huy@12345'
        )

        cls.owner = cls.login(
            'owner@servicehub.local',
            'Owner@12345'
        )

        with closing(sqlite3.connect(cls.db)) as c:

            cls.customer_id = c.execute(
                'SELECT id FROM users WHERE email=?',
                ('huy@servicehub.local',)
            ).fetchone()[0]

            cls.owner_id = c.execute(
                'SELECT id FROM users WHERE email=?',
                ('owner@servicehub.local',)
            ).fetchone()[0]

            cls.service_id, cls.business_id = c.execute(
                'SELECT id, business_id FROM services '
                'ORDER BY id LIMIT 1'
            ).fetchone()

    @classmethod
    def stop_server(cls):

        if cls.process.poll() is None:

            cls.process.terminate()

            try:
                cls.process.wait(timeout=5)

            except subprocess.TimeoutExpired:
                cls.process.kill()
                cls.process.wait(timeout=5)

    @classmethod
    def request(cls, path, method='GET',
                body=None, token=None):

        headers = {
            'Content-Type': 'application/json'
        }

        if token:
            headers['Authorization'] = 'Bearer ' + token

        req = urllib.request.Request(
            cls.base + path,
            data=(
                json.dumps(body).encode('utf-8')
                if body is not None else None
            ),
            headers=headers,
            method=method
        )

        try:

            with urllib.request.urlopen(
                req, timeout=10
            ) as response:

                return response.status, json.load(response)

        except urllib.error.HTTPError as error:

            with error:
                return error.code, json.load(error)

    @classmethod
    def login(cls, email, password):

        code, result = cls.request(
            '/api/auth/login',
            'POST',
            {
                'email': email,
                'password': password
            }
        )

        if code != 200:
            raise AssertionError(result)

        return result['data']['token']

    def setUp(self):

        # Chỉ xóa dữ liệu trong database kiểm thử riêng
        with closing(sqlite3.connect(self.db)) as c, c:

            c.execute('PRAGMA foreign_keys=ON')
            c.execute('DELETE FROM reviews')
            c.execute('DELETE FROM bookings')

    def create_booking(self, status='completed',
                       user_id=None):

        if user_id is None:
            user_id = self.customer_id

        with closing(sqlite3.connect(self.db)) as c, c:

            c.execute('PRAGMA foreign_keys=ON')

            cursor = c.execute(
                """
                INSERT INTO bookings (
                    user_id,
                    service_id,
                    business_id,
                    booking_date,
                    start_time,
                    end_time,
                    status,
                    price
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    self.service_id,
                    self.business_id,
                    '2026-01-01',
                    '10:00',
                    '11:00',
                    status,
                    100000
                )
            )

            return cursor.lastrowid

    def create_review(self, booking_id, rating=5,
                      comment='Dich vu tot'):

        return self.request(
            '/api/reviews',
            'POST',
            {
                'booking_id': booking_id,
                'rating': rating,
                'comment': comment
            },
            self.customer
        )

    # REV-01
    def test_create_valid_review(self):

        booking = self.create_booking()

        code, result = self.create_review(booking)

        self.assertEqual(code, 201, result)
        self.assertEqual(result['data']['rating'], 5)
        self.assertEqual(
            result['data']['booking_id'], booking
        )
        self.assertEqual(
            result['data']['user_id'], self.customer_id
        )
        self.assertEqual(
            result['data']['business_id'], self.business_id
        )

    # REV-02
    def test_review_requires_authentication(self):

        booking = self.create_booking()

        code, _ = self.request(
            '/api/reviews',
            'POST',
            {
                'booking_id': booking,
                'rating': 5
            }
        )

        self.assertEqual(code, 401)

    # REV-03
    def test_uncompleted_booking_is_rejected(self):

        for status in (
            'pending', 'confirmed', 'cancelled'
        ):

            with self.subTest(status=status):

                booking = self.create_booking(status)

                code, result = self.create_review(booking)

                self.assertEqual(code, 409, result)

    # REV-04
    def test_other_users_booking_is_rejected(self):

        booking = self.create_booking(
            user_id=self.owner_id
        )

        code, result = self.create_review(booking)

        self.assertEqual(code, 404, result)

    # REV-05
    def test_duplicate_review_is_rejected(self):

        booking = self.create_booking()

        first, _ = self.create_review(booking)
        second, result = self.create_review(booking)

        self.assertEqual(first, 201)
        self.assertEqual(second, 409, result)

        with closing(sqlite3.connect(self.db)) as c:

            count = c.execute(
                'SELECT COUNT(*) FROM reviews '
                'WHERE booking_id=?',
                (booking,)
            ).fetchone()[0]

            self.assertEqual(count, 1)

    # REV-06
    def test_invalid_review_payload(self):

        booking = self.create_booking()

        for rating in (0, 6, -1, 2.5, '5', True, None):

            with self.subTest(rating=rating):

                code, result = self.create_review(
                    booking, rating
                )

                self.assertEqual(code, 400, result)

        code, result = self.create_review(
            booking, 5, 'a' * 1001
        )

        self.assertEqual(code, 400, result)

        code, result = self.create_review(
            booking, 5, 123
        )

        self.assertEqual(code, 400, result)

        code, result = self.create_review(2**63)

        self.assertEqual(code, 400, result)

    # REV-07
    def test_update_own_review(self):

        booking = self.create_booking()

        code, created = self.create_review(booking)

        self.assertEqual(code, 201, created)

        review_id = created['data']['id']

        code, updated = self.request(
            f'/api/reviews/{review_id}',
            'PUT',
            {
                'rating': 4,
                'comment': 'Da cap nhat'
            },
            self.customer
        )

        self.assertEqual(code, 200, updated)
        self.assertEqual(updated['data']['rating'], 4)
        self.assertEqual(
            updated['data']['comment'], 'Da cap nhat'
        )

    # REV-08
    def test_update_other_users_review_is_rejected(self):

        booking = self.create_booking()

        code, created = self.create_review(booking)

        self.assertEqual(code, 201, created)

        review_id = created['data']['id']

        code, result = self.request(
            f'/api/reviews/{review_id}',
            'PUT',
            {
                'rating': 1,
                'comment': 'Unauthorized update'
            },
            self.owner
        )

        self.assertEqual(code, 404, result)

    # REV-09
    def test_personal_reviews_are_private(self):

        booking = self.create_booking()

        code, _ = self.create_review(booking)

        self.assertEqual(code, 201)

        code, customer = self.request(
            '/api/reviews/me',
            token=self.customer
        )

        self.assertEqual(code, 200)
        self.assertEqual(len(customer['data']), 1)

        code, owner = self.request(
            '/api/reviews/me',
            token=self.owner
        )

        self.assertEqual(code, 200)
        self.assertEqual(owner['data'], [])

        code, _ = self.request('/api/reviews/me')

        self.assertEqual(code, 401)

    # REV-10
    def test_public_rating_excludes_hidden_reviews(self):

        first = self.create_booking()
        second = self.create_booking()
        third = self.create_booking()

        self.assertEqual(
            self.create_review(first, 5)[0], 201
        )

        self.assertEqual(
            self.create_review(second, 3)[0], 201
        )

        self.assertEqual(
            self.create_review(third, 1)[0], 201
        )

        # Mô phỏng Admin đã ẩn đánh giá thứ ba.
        with closing(sqlite3.connect(self.db)) as c, c:

            c.execute(
                'UPDATE reviews SET is_visible=0 '
                'WHERE booking_id=?',
                (third,)
            )

        for endpoint in (
            f'/api/reviews?business_id={self.business_id}',
            f'/api/reviews?service_id={self.service_id}'
        ):

            with self.subTest(endpoint=endpoint):

                code, result = self.request(endpoint)

                self.assertEqual(code, 200, result)

                data = result['data']

                self.assertEqual(data['review_count'], 2)
                self.assertEqual(data['average_rating'], 4.0)
                self.assertEqual(len(data['reviews']), 2)

                self.assertNotIn(
                    1,
                    [r['rating'] for r in data['reviews']]
                )

    # REV-11
    def test_end_to_end_booking_and_review(self):

        date = (
            datetime.now() + timedelta(days=1)
        ).strftime('%Y-%m-%d')

        code, booking = self.request(
            '/api/bookings',
            'POST',
            {
                'service_id': self.service_id,
                'date': date,
                'start_time': '10:00'
            },
            self.customer
        )

        self.assertEqual(code, 201, booking)

        booking_id = booking['data']['id']

        for action in ('confirm', 'complete'):

            code, result = self.request(
                f'/api/owner/bookings/{self.business_id}/{action}',
                'POST',
                {'booking_id': booking_id},
                self.owner
            )

            self.assertEqual(code, 200, result)

        code, review = self.create_review(
            booking_id, 5, 'Dich vu rat tot'
        )

        self.assertEqual(code, 201, review)

        code, result = self.request(
            f'/api/reviews?service_id={self.service_id}'
        )

        self.assertEqual(code, 200, result)
        self.assertEqual(
            result['data']['average_rating'], 5.0
        )
        self.assertEqual(
            result['data']['review_count'], 1
        )

        # REV-12
    def test_concurrent_duplicate_reviews(self):

        booking_id = self.create_booking()

        def submit_review():
            return self.create_review(booking_id)[0]

        with ThreadPoolExecutor(max_workers=2) as pool:

            first = pool.submit(submit_review)
            second = pool.submit(submit_review)

            results = sorted([
                first.result(),
                second.result()
            ])

        self.assertEqual(results, [201, 409])

        with closing(sqlite3.connect(self.db)) as c:

            count = c.execute(
                'SELECT COUNT(*) FROM reviews '
                'WHERE booking_id=?',
                (booking_id,)
            ).fetchone()[0]

        self.assertEqual(count, 1)

        # REV-13
    def test_reviews_are_scoped_to_correct_target(self):

        first = self.create_booking()
        second = self.create_booking()
        third = self.create_booking()

        with closing(sqlite3.connect(self.db)) as c, c:

            other_service = c.execute(
                '''
                SELECT id FROM services
                WHERE business_id=? AND id!=?
                LIMIT 1
                ''',
                (self.business_id, self.service_id)
            ).fetchone()[0]

            other_business_service = c.execute(
                '''
                SELECT id, business_id FROM services
                WHERE business_id!=?
                LIMIT 1
                ''',
                (self.business_id,)
            ).fetchone()

            c.execute(
                'UPDATE bookings SET service_id=? WHERE id=?',
                (other_service, second)
            )

            c.execute(
                '''
                UPDATE bookings
                SET service_id=?, business_id=?
                WHERE id=?
                ''',
                (
                    other_business_service[0],
                    other_business_service[1],
                    third
                )
            )

        self.assertEqual(
            self.create_review(first, 5)[0], 201
        )

        self.assertEqual(
            self.create_review(second, 3)[0], 201
        )

        self.assertEqual(
            self.create_review(third, 1)[0], 201
        )

        code, business = self.request(
            f'/api/reviews?business_id={self.business_id}'
        )

        self.assertEqual(code, 200, business)
        self.assertEqual(
            business['data']['average_rating'], 4.0
        )
        self.assertEqual(
            business['data']['review_count'], 2
        )

        code, service = self.request(
            f'/api/reviews?service_id={self.service_id}'
        )

        self.assertEqual(code, 200, service)
        self.assertEqual(
            service['data']['average_rating'], 5.0
        )
        self.assertEqual(
            service['data']['review_count'], 1
        )

        # REV-14
    def test_hidden_review_cannot_be_updated(self):

        booking_id = self.create_booking()

        code, created = self.create_review(booking_id)

        self.assertEqual(code, 201, created)

        review_id = created['data']['id']

        with closing(sqlite3.connect(self.db)) as c, c:

            c.execute(
                'UPDATE reviews SET is_visible=0 WHERE id=?',
                (review_id,)
            )

        code, result = self.request(
            f'/api/reviews/{review_id}',
            'PUT',
            {
                'rating': 1,
                'comment': 'Updated comment'
            },
            self.customer
        )

        self.assertEqual(code, 409, result)

        self.assertEqual(
            result['error']['code'],
            'REVIEW_HIDDEN'
        )

        # REV-15
    def test_existing_database_migration(self):

        booking_id = self.create_booking()

        with tempfile.TemporaryDirectory() as temp:

            old_db = Path(temp) / 'existing.db'

            with closing(sqlite3.connect(self.db)) as source:
                with closing(sqlite3.connect(old_db)) as target:
                    source.backup(target)

            with closing(sqlite3.connect(old_db)) as c, c:

                c.execute('DROP TABLE reviews')

                before = c.execute(
                    'SELECT * FROM bookings WHERE id=?',
                    (booking_id,)
                ).fetchone()

            env = dict(
                os.environ,
                SERVICEHUB_DB_PATH=str(old_db),
                SERVICEHUB_HOST='127.0.0.1',
                SERVICEHUB_LOCAL_DEMO='0',
                SERVICEHUB_ADMIN_EMAIL='',
                SERVICEHUB_ADMIN_PASSWORD=''
            )

            for _ in range(2):

                result = subprocess.run(
                    [
                        sys.executable,
                        '-c',
                        'import server; server.seed()'
                    ],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True
                )

                self.assertEqual(
                    result.returncode, 0, result.stderr
                )

            with closing(sqlite3.connect(old_db)) as c:

                after = c.execute(
                    'SELECT * FROM bookings WHERE id=?',
                    (booking_id,)
                ).fetchone()

                self.assertEqual(before, after)

                self.assertTrue(
                    c.execute(
                        'PRAGMA table_info(reviews)'
                    ).fetchall()
                )

                self.assertEqual(
                    c.execute(
                        'PRAGMA foreign_key_check'
                    ).fetchall(),
                    []
                )

if __name__ == '__main__':
    unittest.main()