import unittest

from app.main import _build_production_readiness_checks, settings


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
        self.assertEqual(checks["cors"].status, "fail")

    def test_billing_webhook_secret_passes_when_configured(self):
        settings.billing_webhook_secret = "configured-secret"

        checks = {check.key: check for check in _build_production_readiness_checks(database_ok=True)}

        self.assertEqual(checks["billingWebhook"].status, "pass")

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


if __name__ == "__main__":
    unittest.main()
