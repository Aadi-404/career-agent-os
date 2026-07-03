import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.main import _authorize_admin, _authorize_billing_webhook, _authorize_user, get_billing_checkout, get_current_usage_quota, settings
from app.models.history import UsageQuotaStatus, UserRecord


class AuthGuardTests(unittest.TestCase):
    def setUp(self):
        self.original_required = settings.require_user_auth
        self.original_billing_secret = settings.billing_webhook_secret
        self.original_checkout_provider = settings.billing_checkout_provider
        self.original_checkout_url = settings.billing_checkout_url
        self.original_checkout_success_url = settings.billing_checkout_success_url
        self.original_checkout_cancel_url = settings.billing_checkout_cancel_url
        settings.require_user_auth = True

    def tearDown(self):
        settings.require_user_auth = self.original_required
        settings.billing_webhook_secret = self.original_billing_secret
        settings.billing_checkout_provider = self.original_checkout_provider
        settings.billing_checkout_url = self.original_checkout_url
        settings.billing_checkout_success_url = self.original_checkout_success_url
        settings.billing_checkout_cancel_url = self.original_checkout_cancel_url

    def test_requires_session_token_when_enabled(self):
        with self.assertRaises(HTTPException) as context:
            _authorize_user("user-1", None)

        self.assertEqual(context.exception.status_code, 401)

    def test_rejects_token_for_different_user(self):
        with patch("app.main.resolve_user_session", return_value=UserRecord(id="user-2", displayName="User 2", createdAt="2026-06-30T00:00:00Z")):
            with self.assertRaises(HTTPException) as context:
                _authorize_user("user-1", "token")

        self.assertEqual(context.exception.status_code, 403)

    def test_allows_matching_session_token(self):
        with patch("app.main.resolve_user_session", return_value=UserRecord(id="user-1", displayName="User 1", createdAt="2026-06-30T00:00:00Z")):
            _authorize_user("user-1", "token")

    def test_admin_guard_rejects_member(self):
        with patch("app.main.resolve_user_session", return_value=UserRecord(id="user-1", displayName="User 1", role="member", createdAt="2026-06-30T00:00:00Z")):
            with self.assertRaises(HTTPException) as context:
                _authorize_admin("token")

        self.assertEqual(context.exception.status_code, 403)

    def test_admin_guard_allows_admin(self):
        with patch("app.main.resolve_user_session", return_value=UserRecord(id="admin-1", displayName="Admin 1", role="admin", createdAt="2026-06-30T00:00:00Z")):
            _authorize_admin("token")

    def test_billing_webhook_requires_configured_secret(self):
        settings.billing_webhook_secret = ""

        with self.assertRaises(HTTPException) as context:
            _authorize_billing_webhook("secret")

        self.assertEqual(context.exception.status_code, 503)

    def test_billing_webhook_rejects_wrong_secret(self):
        settings.billing_webhook_secret = "expected-secret"

        with self.assertRaises(HTTPException) as context:
            _authorize_billing_webhook("wrong-secret")

        self.assertEqual(context.exception.status_code, 401)

    def test_billing_webhook_allows_matching_secret(self):
        settings.billing_webhook_secret = "expected-secret"

        _authorize_billing_webhook("expected-secret")

    def test_user_quota_endpoint_uses_user_guard(self):
        quota = UsageQuotaStatus(userId="user-1", tier="free", windowStartAt="2026-07-01T00:00:00+00:00", resetAt="2026-08-01T00:00:00+00:00", usedUnits=4, limitUnits=50, remainingUnits=46)

        with (
            patch("app.main.resolve_user_session", return_value=UserRecord(id="user-1", displayName="User 1", createdAt="2026-06-30T00:00:00Z")),
            patch("app.main.get_usage_quota_status", return_value=quota) as quota_mock,
        ):
            response = get_current_usage_quota("user-1", "token")

        quota_mock.assert_called_once_with(user_id="user-1")
        self.assertEqual(response.remainingUnits, 46)

    def test_billing_checkout_returns_configured_handoff(self):
        settings.billing_checkout_provider = "stripe"
        settings.billing_checkout_url = "https://checkout.example.test/session"
        settings.billing_checkout_success_url = "https://app.example.test/success"
        settings.billing_checkout_cancel_url = "https://app.example.test/cancel"

        with patch("app.main.resolve_user_session", return_value=UserRecord(id="user-1", displayName="User 1", createdAt="2026-06-30T00:00:00Z")):
            response = get_billing_checkout("user-1", "token")

        self.assertTrue(response.configured)
        self.assertEqual(response.provider, "stripe")
        self.assertEqual(response.checkoutUrl, "https://checkout.example.test/session")

    def test_billing_checkout_returns_manual_placeholder_when_unconfigured(self):
        settings.billing_checkout_provider = "manual"
        settings.billing_checkout_url = ""

        with patch("app.main.resolve_user_session", return_value=UserRecord(id="user-1", displayName="User 1", createdAt="2026-06-30T00:00:00Z")):
            response = get_billing_checkout("user-1", "token")

        self.assertFalse(response.configured)
        self.assertIn("not configured", response.message)


if __name__ == "__main__":
    unittest.main()
