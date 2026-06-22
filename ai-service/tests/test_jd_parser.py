import unittest

from app.models.jd_parse import JdParseRequest
from app.services.jd_parser import parse_jd
from tests.parser_fixtures import JdParserExpectation, JdParserFixture


JD_PARSER_FIXTURES = [
    JdParserFixture(
        id="linkedin_dotnet_cloud_role",
        description="LinkedIn-style JD with strong wording, location, work mode, and certification basics.",
        raw_text="""
Role: Senior .NET Full Stack Developer
Location: Pune / Mumbai, hybrid
Experience: 3 to 5 years
Must have strong hands-on experience with ASP.NET Core, Web API, SQL Server, Entity Framework, React, and Azure cloud basics.
Responsibilities include building scalable APIs, maintaining React screens, optimizing SQL queries, and collaborating with QA and DevOps teams.
Good to have AZ-900, AWS Cloud Practitioner, or similar cloud fundamentals certification.
""",
        expected=JdParserExpectation(
            role_title_contains=".NET Full Stack Developer",
            min_years=3.0,
            required_skills=["ASP.NET Core", "Web API", "SQL Server", "Entity Framework", "React"],
            preferred_skills=["AZ-900"],
            required_certifications_contains=["cloud fundamentals"],
            emphasized_contains=["ASP.NET Core"],
            responsibilities_min_count=3,
            locations=["Pune", "Mumbai"],
            work_modes=["hybrid"],
        ),
    ),
    JdParserFixture(
        id="naukri_data_ai_role",
        description="Naukri-style paragraph JD with repeated AI/data requirements and remote mode.",
        raw_text="""
Hiring Data Engineer / AI Developer with minimum 2 years of experience. Remote role based in India.
Required skills: Python, SQL, Power BI, Azure Data Factory, ADLS, LLM Integration.
Key responsibility is to design ETL pipelines, build dashboards, develop AI agents, and automate manual reporting workflows.
Strong Python and SQL are mandatory. Preferred exposure to Control-M and Snowflake.
""",
        expected=JdParserExpectation(
            role_title_contains="Data Engineer / AI Developer",
            min_years=2.0,
            required_skills=["Python", "SQL", "Power BI", "Azure Data Factory"],
            preferred_skills=["Control-M", "Snowflake"],
            emphasized_contains=["Python", "SQL"],
            responsibilities_min_count=3,
            locations=["India"],
            work_modes=["remote"],
        ),
    ),
]


class JdParserRegressionTests(unittest.TestCase):
    def test_jd_parser_fixture_pack(self):
        for fixture in JD_PARSER_FIXTURES:
            with self.subTest(fixture=fixture.id):
                parsed = parse_jd(JdParseRequest(rawJobDescriptionText=fixture.raw_text)).parsedJobDescription
                expected = fixture.expected

                if expected.role_title_contains:
                    self.assertIsNotNone(parsed.roleTitle)
                    self.assertIn(expected.role_title_contains, parsed.roleTitle)
                if expected.min_years is not None:
                    self.assertEqual(parsed.experienceRange.minYears, expected.min_years)
                for skill in expected.required_skills:
                    self.assertIn(skill, parsed.requiredSkills)
                for skill in expected.preferred_skills:
                    self.assertIn(skill, parsed.preferredSkills)
                for fragment in expected.required_certifications_contains:
                    self.assertTrue(
                        any(fragment.lower() in item.lower() for item in parsed.requiredCertifications),
                        f"{fragment} was not found in required certifications: {parsed.requiredCertifications}",
                    )
                for fragment in expected.emphasized_contains:
                    self.assertTrue(
                        any(fragment.lower() in item.lower() for item in parsed.emphasizedRequirements),
                        f"{fragment} was not found in emphasized requirements: {parsed.emphasizedRequirements}",
                    )
                if expected.responsibilities_min_count is not None:
                    self.assertGreaterEqual(len(parsed.responsibilities), expected.responsibilities_min_count)
                for location in expected.locations:
                    self.assertIn(location, parsed.locations)
                for mode in expected.work_modes:
                    self.assertIn(mode, parsed.workModes)


if __name__ == "__main__":
    unittest.main()
