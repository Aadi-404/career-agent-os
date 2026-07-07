import unittest

from app.models.extension import ExtensionValidationRecord
from app.models.system import ExtensionPackageStatus, ProductionReadinessResponse, ReadinessCheck
from app.services.staging_validation_service import build_staging_validation


class StagingValidationServiceTests(unittest.TestCase):
    def test_staging_validation_reports_missing_real_site_checks(self):
        response = build_staging_validation(
            readiness=ProductionReadinessResponse(
                environment="staging",
                readyForProduction=True,
                checks=[ReadinessCheck(key="database", label="Database", status="pass", detail="ok")],
            ),
            extension_package=ExtensionPackageStatus(packaged=True, message="ok", packagedFor="https://api.example.com"),
            extension_validations=[
                ExtensionValidationRecord(
                    id="validation-1",
                    userId="user-1",
                    site="LinkedIn",
                    url="https://linkedin.com/jobs/view/1",
                    parserRating="pass",
                    autoParsed=True,
                    manualPasteUsed=False,
                    titleFound=True,
                    companyFound=True,
                    descriptionFound=True,
                    createdAt="2026-07-07T00:00:00Z",
                )
            ],
            api_base_url="https://api.example.com",
            frontend_url="https://app.example.com",
            user_id="user-1",
        )

        self.assertFalse(response.readyForStaging)
        self.assertEqual(response.extensionSites["linkedin"], "pass")
        self.assertEqual(response.extensionSites["naukri"], "missing")
        self.assertTrue(any("Naukri" in check.label for check in response.checks))
        self.assertTrue(any("smoke_check.py" in item.command for item in response.commands))


if __name__ == "__main__":
    unittest.main()
