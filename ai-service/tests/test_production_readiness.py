import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.main import _build_production_readiness_checks, _extension_package_required_entries, _release_next_actions, _verify_extension_package_zip, release_summary, settings
from app.models.system import ExtensionPackageStatus


class ProductionReadinessTests(unittest.TestCase):
    def setUp(self):
        self.original_values = {
            "environment": settings.environment,
            "require_user_auth": settings.require_user_auth,
            "admin_user_ids": settings.admin_user_ids,
            "cors_allow_origins": settings.cors_allow_origins,
            "llm_mode": settings.llm_mode,
            "llm_provider": settings.llm_provider,
            "llm_api_key": settings.llm_api_key,
            "groq_api_key": settings.groq_api_key,
            "embedding_provider": settings.embedding_provider,
            "embedding_fallback_local": settings.embedding_fallback_local,
            "jd_parser_mode": settings.jd_parser_mode,
            "billing_webhook_secret": settings.billing_webhook_secret,
            "billing_checkout_provider": settings.billing_checkout_provider,
            "billing_checkout_url": settings.billing_checkout_url,
            "billing_checkout_success_url": settings.billing_checkout_success_url,
            "billing_checkout_cancel_url": settings.billing_checkout_cancel_url,
            "log_level": settings.log_level,
        }

    def tearDown(self):
        for key, value in self.original_values.items():
            setattr(settings, key, value)

    def test_production_flags_missing_auth_and_local_cors(self):
        settings.environment = "production"
        settings.require_user_auth = False
        settings.admin_user_ids = ""
        settings.cors_allow_origins = "http://localhost:5173"

        checks = {check.key: check for check in _build_production_readiness_checks(database_ok=True)}

        self.assertEqual(checks["auth"].status, "fail")
        self.assertEqual(checks["adminBootstrap"].status, "fail")
        self.assertEqual(checks["billingWebhook"].status, "fail")
        self.assertEqual(checks["billingCheckout"].status, "fail")
        self.assertEqual(checks["cors"].status, "fail")

    def test_billing_webhook_secret_passes_when_configured(self):
        settings.billing_webhook_secret = "configured-secret"

        checks = {check.key: check for check in _build_production_readiness_checks(database_ok=True)}

        self.assertEqual(checks["billingWebhook"].status, "pass")

    def test_billing_checkout_passes_when_configured(self):
        settings.billing_checkout_provider = "stripe"
        settings.billing_checkout_url = "https://checkout.example.test/session"

        checks = {check.key: check for check in _build_production_readiness_checks(database_ok=True)}

        self.assertEqual(checks["billingCheckout"].status, "pass")

    def test_billing_checkout_fails_in_production_when_provider_is_manual(self):
        settings.environment = "production"
        settings.billing_checkout_provider = "manual"
        settings.billing_checkout_url = "https://checkout.example.test/session"

        checks = {check.key: check for check in _build_production_readiness_checks(database_ok=True)}

        self.assertEqual(checks["billingCheckout"].status, "fail")

    def test_billing_return_urls_pass_when_configured(self):
        settings.billing_checkout_success_url = "https://app.example.test/billing/success"
        settings.billing_checkout_cancel_url = "https://app.example.test/billing/cancel"

        checks = {check.key: check for check in _build_production_readiness_checks(database_ok=True)}

        self.assertEqual(checks["billingReturnUrls"].status, "pass")

    def test_live_llm_without_key_is_a_blocker(self):
        settings.llm_mode = "live"
        settings.llm_provider = "groq"
        settings.llm_api_key = ""
        settings.groq_api_key = ""

        checks = {check.key: check for check in _build_production_readiness_checks(database_ok=True)}

        self.assertEqual(checks["llm"].status, "fail")

    def test_production_warns_for_debug_logging(self):
        settings.environment = "production"
        settings.log_level = "DEBUG"

        checks = {check.key: check for check in _build_production_readiness_checks(database_ok=True)}

        self.assertEqual(checks["logging"].status, "warn")

    def test_release_next_actions_include_extension_and_demo_cleanup(self):
        actions = _release_next_actions(
            blockers=0,
            warnings=1,
            extension_package=ExtensionPackageStatus(packaged=False, message="missing"),
            demo_user_present=True,
        )

        self.assertTrue(any("warning" in action for action in actions))
        self.assertTrue(any("Package the browser extension" in action for action in actions))
        self.assertTrue(any("Clean demo workspace" in action for action in actions))

    def test_extension_package_zip_verifier_requires_release_files(self):
        with TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "extension.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("manifest.json", "{}")
                archive.writestr("config.js", "")

            valid, missing, message = _verify_extension_package_zip(zip_path, _extension_package_required_entries())

        self.assertFalse(valid)
        self.assertIn("popup.html", missing)
        self.assertIn("missing", message)

    def test_release_summary_returns_server_backed_status(self):
        package = ExtensionPackageStatus(packaged=True, version="0.1.0", message="ready")
        original_environment = settings.environment
        original_auth = settings.require_user_auth
        original_admins = settings.admin_user_ids
        original_billing_secret = settings.billing_webhook_secret
        original_billing_provider = settings.billing_checkout_provider
        original_billing_checkout = settings.billing_checkout_url
        original_success = settings.billing_checkout_success_url
        original_cancel = settings.billing_checkout_cancel_url
        original_cors = settings.cors_allow_origins
        try:
            settings.environment = "production"
            settings.require_user_auth = True
            settings.admin_user_ids = "admin-1"
            settings.billing_webhook_secret = "secret"
            settings.billing_checkout_provider = "stripe"
            settings.billing_checkout_url = "https://checkout.example.test"
            settings.billing_checkout_success_url = "https://app.example.test/success"
            settings.billing_checkout_cancel_url = "https://app.example.test/cancel"
            settings.cors_allow_origins = "https://app.example.test"
            with (
                patch("app.main.initialize_database"),
                patch("app.main._latest_extension_package_status", return_value=package),
                patch("app.main.list_users", return_value=[]),
            ):
                summary = release_summary()
        finally:
            settings.environment = original_environment
            settings.require_user_auth = original_auth
            settings.admin_user_ids = original_admins
            settings.billing_webhook_secret = original_billing_secret
            settings.billing_checkout_provider = original_billing_provider
            settings.billing_checkout_url = original_billing_checkout
            settings.billing_checkout_success_url = original_success
            settings.billing_checkout_cancel_url = original_cancel
            settings.cors_allow_origins = original_cors

        self.assertEqual(summary.launchDecision, "ready")
        self.assertTrue(summary.extensionPackage.packaged)


if __name__ == "__main__":
    unittest.main()
