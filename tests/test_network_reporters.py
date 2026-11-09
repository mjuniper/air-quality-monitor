import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


class NetworkReporterTests(unittest.TestCase):
    def setUp(self):
        self.radio = Mock(connected=True, ipv4_address="192.0.2.1")
        modules = {
            "wifi": Mock(radio=self.radio),
            "socketpool": Mock(),
            "adafruit_requests": Mock(),
        }
        with patch.dict(sys.modules, modules):
            self.db_module = self.load("db")
            self.notifier_module = self.load("notifier")
        self.db = self.db_module.InfluxDbReporter({
            "db": dict(host="example.invalid", port=8086, database="air",
                       table="readings", username="test", password="test")
        })
        self.notifier = self.notifier_module.NotificationReporter({
            "threshold": 10, "pushovertoken": "test", "pushoveruser": "test"
        })
        self.db.session = Mock()
        self.notifier.session = Mock()
        self.clock = patch.object(self.notifier_module.time, "time", return_value=100000)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.output = io.StringIO()
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def load(self, name):
        spec = importlib.util.spec_from_file_location(
            "test_reporter_" + name, ROOT / "reporters" / (name + ".py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_offline_or_missing_ip_skips_both_reporters(self):
        for connected, address in ((False, None), (False, "192.0.2.1"), (True, None)):
            with self.subTest(connected=connected, address=address):
                self.radio.connected = connected
                self.radio.ipv4_address = address
                self.db.report({"co2": 500})
                self.notifier.report({"delta": 0})
                self.db.session.post.assert_not_called()
                self.notifier.session.post.assert_not_called()
                self.assertEqual(self.notifier.lastNotification, 0)
        self.assertIn("InfluxDbReporter: skipping", self.output.getvalue())
        self.assertIn("NotificationReporter: skipping", self.output.getvalue())

    def test_database_request_preserves_payload_and_closes_response(self):
        response = self.db.session.post.return_value
        response.status_code = 204
        self.db.report({"co2": 500})
        self.db.session.post.assert_called_once_with(
            "http://example.invalid:8086/write?db=air", data="readings co2=500",
            headers={"Authorization": "Token test:test"}, timeout=10
        )
        response.close.assert_called_once()

    def test_database_http_failure_is_logged_and_response_closed(self):
        response = self.db.session.post.return_value
        response.status_code = 500
        self.db.report({"co2": 500})
        self.assertIn("InfluxDbReporter error: HTTP 500", self.output.getvalue())
        response.close.assert_called_once()

    def test_request_exceptions_do_not_escape_or_start_cooldown(self):
        for reporter in (self.db, self.notifier):
            with self.subTest(reporter=type(reporter).__name__):
                reporter.session.post.side_effect = OSError("connection lost")
                reporter.report({"co2": 500, "delta": 0})
        self.assertEqual(self.notifier.lastNotification, 0)
        self.assertEqual(self.output.getvalue().count("connection lost"), 2)

    def test_notification_failures_leave_cooldown_unchanged(self):
        response = self.notifier.session.post.return_value
        for status_code, body in ((500, {}), (200, {"status": 0})):
            with self.subTest(status_code=status_code, body=body):
                response.reset_mock()
                response.status_code = status_code
                response.json.return_value = body
                self.notifier.report({"delta": 0})
                self.assertEqual(self.notifier.lastNotification, 0)
                response.close.assert_called_once()
        self.assertIn("HTTP 500", self.output.getvalue())
        self.assertIn("did not accept", self.output.getvalue())

    def test_notification_success_starts_cooldown_and_suppresses_repeat(self):
        response = self.notifier.session.post.return_value
        response.status_code = 200
        response.json.return_value = {"status": 1}
        self.assertTrue(self.notifier.shouldSendNotification())
        self.assertEqual(self.notifier.lastNotification, 0)
        self.notifier.report({"delta": 0})
        self.assertEqual(self.notifier.lastNotification, 100000)
        response.close.assert_called_once()
        self.assertEqual(self.notifier.session.post.call_args.kwargs["timeout"], 10)
        self.notifier.report({"delta": 0})
        self.notifier.session.post.assert_called_once()

    def test_offline_attempt_can_send_after_reconnection(self):
        self.radio.connected = False
        self.notifier.report({"delta": 0})
        self.radio.connected = True
        response = self.notifier.session.post.return_value
        response.status_code = 200
        response.json.return_value = {"status": 1}
        self.notifier.report({"delta": 0})
        self.notifier.session.post.assert_called_once()
        self.assertEqual(self.notifier.lastNotification, 100000)

    def test_below_threshold_does_not_send(self):
        self.notifier.report({"delta": -11})
        self.notifier.session.post.assert_not_called()
