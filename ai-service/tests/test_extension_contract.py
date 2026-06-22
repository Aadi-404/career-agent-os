import unittest

from app.main import parse_extension_job_page
from app.models.extension import ExtensionPageParseRequest


class ExtensionContractTests(unittest.TestCase):
    def test_parse_page_prefers_site_extracted_fields(self):
        request = ExtensionPageParseRequest(
            pageTitle="Noisy browser title | Jobs",
            pageUrl="https://www.linkedin.com/jobs/view/123",
            selectedText=None,
            pageText="Company: Wrong Corp. Location: Wrong City. This page has lots of unrelated text.",
            extractedTitle="Senior Full Stack Engineer",
            extractedCompany="Example Corp",
            extractedLocation="Pune, Maharashtra, India",
            extractedDescription="Build ASP.NET Core APIs, React screens, SQL Server queries, and Azure cloud integrations for enterprise products.",
            source="linkedin",
        )

        draft = parse_extension_job_page(request)

        self.assertEqual(draft.title, "Senior Full Stack Engineer")
        self.assertEqual(draft.company, "Example Corp")
        self.assertEqual(draft.location, "Pune, Maharashtra, India")
        self.assertEqual(draft.description, request.extractedDescription)


if __name__ == "__main__":
    unittest.main()
