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
        env = dict(os.environ, SERVICEHUB_HOST="127.0.0.1",
                   SERVICEHUB_PORT=str(port),
                   SERVICEHUB_DB_PATH=str(Path(cls.temp.name) / "s4r08.db"))
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

    def test_booking_review_and_duplicate_review_gap_is_explicit(self):
        # The supplied schema and API currently expose no customer booking-review
        # table/endpoint. Keep this as an explicit regression sentinel rather than
        # pretending the requested review behavior has passed.
        code, body = self.request("/api/reviews", "POST", {
            "booking_id": 1, "rating": 5, "comment": "S4R-08 test"},
            self.customer)
        self.assertEqual(code, 404, body)
        self.assertEqual(body["error"]["code"], "ENDPOINT_NOT_FOUND")
        # The duplicate-review rule cannot be exercised until review creation exists.
        second_code, _ = self.request("/api/reviews", "POST", {
            "booking_id": 1, "rating": 5, "comment": "Duplicate attempt"},
            self.customer)
        self.assertEqual(second_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
