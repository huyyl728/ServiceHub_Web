"""Additive S4R-08 regression tests. Existing application files are not modified."""
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
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class S4R08BookingRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="servicehub-s4r08-")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        cls.base = f"http://127.0.0.1:{port}"
                # Cô lập môi trường kiểm thử khỏi cấu hình Local Demo
        env = dict(
            os.environ,
            SERVICEHUB_HOST="127.0.0.1",
            SERVICEHUB_PORT=str(port),
            SERVICEHUB_DB_PATH=str(
                Path(cls.temp.name) / "s4r08.db"
            ),
            SERVICEHUB_LOCAL_DEMO="0",
            SERVICEHUB_ADMIN_EMAIL="",
            SERVICEHUB_ADMIN_PASSWORD=""
        )
        cls.process = subprocess.Popen(
            [sys.executable, "tests/fixture_server.py"], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(100):
            if cls.process.poll() is not None:
                raise RuntimeError(cls.process.stderr.read().decode(errors="replace"))
            try:
                if cls.request("/api/health")[0] == 200:
                    break
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        else:
            raise RuntimeError("S4R-08 test server did not start")
        cls.customer = cls.login("huy@servicehub.local", "Huy@12345")
        cls.owner = cls.login("owner@servicehub.local", "Owner@12345")
        cls.admin = cls.login("admin@servicehub.local", "Admin@12345")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "process"):
            cls.process.terminate()
            try:
                cls.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.process.kill()
                cls.process.wait(timeout=5)
            if cls.process.stderr:
                cls.process.stderr.close()
        if hasattr(cls, "temp"):
            cls.temp.cleanup()

    @classmethod
    def request(cls, path, method="GET", body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(
            cls.base + path,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            # Đóng phản hồi HTTP sau khi đọc dữ liệu lỗi
            with closing(error):
                return error.code, json.loads(error.read())

    @classmethod
    def login(cls, email, password):
        code, result = cls.request(
            "/api/auth/login", "POST", {"email": email, "password": password})
        if code != 200:
            raise AssertionError(f"Login failed for {email}: {result}")
        return result["data"]["token"]

    def test_customer_owner_complete_booking_and_admin_count_without_payment(self):
        before = self.request("/api/admin/stats", token=self.admin)
        self.assertEqual(before[0], 200, before[1])
        before_count = before[1]["data"]["bookings"]

        services = self.request("/api/services")[1]["data"]
        service = next(s for s in services
                       if s["business_name"] == "Huy Football"
                       and s["name"] == "Sân bóng 5 người")
        date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        slots_code, slots_body = self.request(
            f'/api/services/{service["id"]}/availability?date={date}',
            token=self.customer)
        self.assertEqual(slots_code, 200, slots_body)
        self.assertTrue(slots_body["data"])

        code, created = self.request("/api/bookings", "POST", {
            "service_id": service["id"], "date": date,
            "start_time": slots_body["data"][0]["start_time"]},
            self.customer)
        self.assertEqual(code, 201, created)
        booking_id = created["data"]["id"]
        self.assertEqual(created["data"]["status"], "pending")
        self.assertNotIn("payment", created["data"])
        self.assertNotIn("payment_url", created["data"])

        my_bookings = self.request("/api/bookings/me", token=self.customer)
        self.assertEqual(my_bookings[0], 200, my_bookings[1])
        booking = next(b for b in my_bookings[1]["data"] if b["id"] == booking_id)
        self.assertEqual(booking["status"], "pending")

        managed = self.request("/api/businesses/managed", token=self.owner)
        self.assertEqual(managed[0], 200, managed[1])
        business_id = next(b["id"] for b in managed[1]["data"]
                           if b["name"] == "Huy Football")
        owner_bookings = self.request(
            f"/api/owner/bookings?business_id={business_id}", token=self.owner)
        self.assertEqual(owner_bookings[0], 200, owner_bookings[1])
        self.assertTrue(any(b["id"] == booking_id for b in owner_bookings[1]["data"]))

        code, confirmed = self.request(
            f"/api/owner/bookings/{business_id}/confirm", "POST",
            {"booking_id": booking_id}, self.owner)
        self.assertEqual(code, 200, confirmed)
        code, completed = self.request(
            f"/api/owner/bookings/{business_id}/complete", "POST",
            {"booking_id": booking_id}, self.owner)
        self.assertEqual(code, 200, completed)

        final_bookings = self.request("/api/bookings/me", token=self.customer)
        self.assertEqual(final_bookings[0], 200, final_bookings[1])
        final_booking = next(b for b in final_bookings[1]["data"]
                             if b["id"] == booking_id)
        self.assertEqual(final_booking["status"], "completed")

        after = self.request("/api/admin/stats", token=self.admin)
        self.assertEqual(after[0], 200, after[1])
        self.assertEqual(after[1]["data"]["bookings"], before_count + 1)
                # Khách hàng đánh giá lịch đặt đã hoàn thành
        review_payload = {
            "booking_id": booking_id,
            "rating": 5,
            "comment": "Kiểm thử tích hợp Sprint 4"
        }

        code, review = self.request(
            "/api/reviews",
            "POST",
            review_payload,
            self.customer
        )

        self.assertEqual(code, 201, review)

        review_id = review["data"]["id"]

        # Không cho phép đánh giá trùng lịch đặt
        code, duplicate = self.request(
            "/api/reviews",
            "POST",
            review_payload,
            self.customer
        )

        self.assertEqual(code, 409, duplicate)

        self.assertEqual(
            duplicate["error"]["code"],
            "REVIEW_ALREADY_EXISTS"
        )

        # Kiểm tra thống kê chi tiết cơ sở
        detail_url = (
            f"/api/admin/businesses/{business_id}/detail"
        )

        code, result = self.request(
            detail_url,
            token=self.admin
        )

        self.assertEqual(code, 200, result)

        detail = result["data"]
        stats = detail["business"]

        self.assertEqual(stats["id"], business_id)

        self.assertTrue(
            any(
                item["id"] == booking_id
                for item in detail["bookings"]
            )
        )

        self.assertTrue(
            any(
                item["id"] == review_id
                for item in detail["recent_reviews"]
            )
        )

        # Đối chiếu số liệu với SQLite kiểm thử
        db_path = Path(self.temp.name) / "s4r08.db"

        with closing(sqlite3.connect(db_path)) as c:
            booking_count = c.execute(
                """
                SELECT COUNT(*)
                FROM bookings
                WHERE business_id = ?
                """,
                (business_id,)
            ).fetchone()[0]

            service_count = c.execute(
                """
                SELECT COUNT(*)
                FROM services
                WHERE business_id = ?
                """,
                (business_id,)
            ).fetchone()[0]

            review_count, average_rating = c.execute(
                """
                SELECT COUNT(*), ROUND(AVG(rating), 2)
                FROM reviews
                WHERE business_id = ?
                  AND is_visible = 1
                """,
                (business_id,)
            ).fetchone()

            statuses = dict(c.execute(
                """
                SELECT status, COUNT(*)
                FROM bookings
                WHERE business_id = ?
                GROUP BY status
                """,
                (business_id,)
            ).fetchall())

        self.assertEqual(
            stats["booking_count"], booking_count
        )

        self.assertEqual(
            stats["service_count"], service_count
        )

        self.assertEqual(
            stats["review_count"], review_count
        )

        self.assertEqual(
            stats["average_rating"], average_rating
        )

        for status in (
            "pending", "confirmed",
            "completed", "cancelled"
        ):
            self.assertEqual(
                stats[f"{status}_count"],
                statuses.get(status, 0)
            )

        # Kiểm tra bộ lọc ngày sử dụng dịch vụ
        code, filtered = self.request(
            f"{detail_url}?start_date={date}&end_date={date}",
            token=self.admin
        )

        self.assertEqual(code, 200, filtered)

        self.assertEqual(
            filtered["data"]["business"]["booking_count"],
            1
        )

        self.assertEqual(
            filtered["data"]["bookings"][0]["id"],
            booking_id
        )

        # Kiểm tra đồng bộ khi ẩn và khôi phục đánh giá
        for target in ("hidden", "visible"):

            code, moderation = self.request(
                f"/api/admin/reviews/{review_id}/moderate",
                "POST",
                {
                    "target_status": target,
                    "reason": "Kiểm thử tích hợp Sprint 4"
                },
                self.admin
            )

            self.assertEqual(code, 200, moderation)

            code, updated = self.request(
                detail_url,
                token=self.admin
            )

            self.assertEqual(code, 200, updated)

            current = updated["data"]["business"]

            expected_count = (
                review_count - 1
                if target == "hidden"
                else review_count
            )

            self.assertEqual(
                current["review_count"],
                expected_count
            )

            # Đối chiếu thống kê Admin với đánh giá công khai
            code, public = self.request(
                f"/api/reviews?business_id={business_id}"
            )

            self.assertEqual(code, 200, public)

            self.assertEqual(
                current["review_count"],
                public["data"]["review_count"]
            )

            self.assertEqual(
                current["average_rating"],
                public["data"]["average_rating"]
            )

    def test_role_boundaries_customer_owner_admin(self):
        managed = self.request("/api/businesses/managed", token=self.owner)
        self.assertEqual(managed[0], 200, managed[1])
        business_id = next(b["id"] for b in managed[1]["data"]
                           if b["name"] == "Huy Football")
        self.assertEqual(
            self.request(f"/api/owner/bookings?business_id={business_id}",
                         token=self.customer)[0], 403)
        self.assertEqual(self.request("/api/admin/stats", token=self.owner)[0], 403)
        self.assertEqual(self.request("/api/admin/stats", token=self.customer)[0], 403)
        self.assertEqual(self.request("/api/admin/stats", token=self.admin)[0], 200)

    def test_booking_rejects_unauthenticated_and_invalid_input(self):
        self.assertEqual(self.request("/api/bookings", "POST", {
            "service_id": 1, "date": "2099-01-01", "start_time": "10:00"})[0], 401)
        code, body = self.request("/api/bookings", "POST", {
            "service_id": 1, "date": "not-a-date", "start_time": "10:00"},
            self.customer)
        self.assertEqual(code, 400, body)

    def test_admin_business_statistics_permissions(self):

        # Admin lấy danh sách cơ sở
        code, result = self.request(
            "/api/admin/businesses",
            token=self.admin
        )

        self.assertEqual(code, 200, result)
        self.assertTrue(result["data"])

        business_id = result["data"][0]["id"]

        endpoints = [
            "/api/admin/businesses",
            f"/api/admin/businesses/{business_id}/detail"
        ]
        # Kiểm tra xác thực và phân quyền Admin
        for endpoint in endpoints:
            for role, token, expected_status, expected_error in (
                ("Customer", self.customer, 403, "ADMIN_REQUIRED"),
                ("Owner", self.owner, 403, "ADMIN_REQUIRED"),
                ("Guest", None, 401, "AUTH_REQUIRED")
            ):
                with self.subTest(
                    endpoint=endpoint,
                    role=role
                ):
                    code, body = self.request(
                        endpoint,
                        token=token
                    )

                    self.assertEqual(
                        code, expected_status, body
                    )

                    self.assertEqual(
                        body["error"]["code"],
                        expected_error
                    )

        # Kiểm tra dữ liệu đầu vào không hợp lệ
        invalid_urls = [
            "/api/admin/businesses?page=0",
            "/api/admin/businesses?status=unknown",
            "/api/admin/businesses?start_date=invalid",
            "/api/admin/businesses?start_date=2026-12-31&end_date=2026-01-01"
        ]

        for endpoint in invalid_urls:
            code, body = self.request(
                endpoint,
                token=self.admin
            )

            self.assertEqual(code, 400, body)

        # Kiểm tra mã cơ sở không tồn tại
        code, body = self.request(
            "/api/admin/businesses/9223372036854775807/detail",
            token=self.admin
        )

        self.assertEqual(code, 404, body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
