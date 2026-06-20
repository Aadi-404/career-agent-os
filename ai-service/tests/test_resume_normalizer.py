import unittest

from app.models.resume_normalize import ResumeNormalizeRequest
from app.services.resume_normalizer import normalize_resume


ADITYA_RESUME = """
Aditya Rana
Location: /envelopeadityarana81027@gmail.com phone7870851840 marker-altNavi Mumbai, India
Contact: peadityarana81027@gmail.com | 7870851840 | linkedin.com/in/aditya-rana-1017771b2/githubgithub.com/Aadi-404 | github.com/Aadi-404

Projects
Flight Reservation System
Built booking workflow and CRUD features for both user and admin modules.
Developed using ASP.NET Core, Entity Framework, Angular, and SQL Server.
Designed smooth end-to-end flow for searching, booking, and managing flights.
PCAP Data Analysis (Desktop App)
Created tool to analyze packet captures (.pcap) and extract domains and IPs.
Built using Python (scapy), Electron.js, and JavaScript.
Helps understand traffic patterns through simple visual output.
Cross-Share Web App
Web app for easy file sharing with multi-file drag-and-drop support.
Developed using React.js, Django, SQLite, and Django REST API.
Enables users to upload and share files smoothly over the internet
"""


HARSH_RESUME = """
Harsh Garud
Contact: harsh412g@gmail.com | +91-7898480696 | linkedin.com/in/harshgarud

Summary
Results-driven Senior Analyst with 2+ years of experience at Capgemini in full-stack development, data engineering, and AI-driven solutions. Proficient in building scalable web applications using Django, Python, and React, and delivering actionable business insights through Power BI and SQL

Experience
Capgemini Jun 2024 – Present - Senior Analyst / Software engineer | Navi- Mumbai, India - Jun-2024 - Built 3+ enterprise web applications using Django, React, and Python, reducing client reporting turnaround by 40% through optimised APIs and responsive UIs - Jun-2024
Designed ETL pipelines and Power BI dashboards processing 1M+ daily records, cutting manual reporting effort by 35% across business units.
Developed and deployed AI Agents and automation workflows eliminating ~20 hours/week of manual data processing and improving operational efficiency significantly.
Delivered projects within Agile sprints, collaborating across business analysts, QA, and DevOps teams while maintaining high code quality through reviews and documentation.

Projects
Data Simplified Tool | React, Django, Python, SQL
Built a full-stack data quality platform connecting to 5+ databases (SSMS, Snowflake), with modules for quality checks, metadata analysis, SQL validation, and cross-database comparison.
Reduced manual data validation effort by 50% and cross-database comparison time from hours to under 10 minutes via a unified interface.
AI Agents Platform (GitHub Copilot-Based) | Python, Azure Data Factory, ADLS, Control-M
Developed AI Agents integrated with ADF, ADLS, Control-M, and databases for natural language-driven pipeline triggering, job fetching, and data validation - reducing operational overhead by 30%.
Implemented an STTM file parser that automated mapping-based validations, eliminating 100% of manual mapping review and cutting setup time from days to minutes.

Skills
Azure, C++, Django, Git, Javascript, Python, React, SQL, SSMS

Education
Bachelor of Technology (B. Tech) - Mechanical Engineering
Acropolis Institute of Technology and Research, Indore 2019 - 2023
CGPA: 7.7 / 10

Certifications
Microsoft Certified: Azure AI Engineer Associate - Microsoft
Microsoft Certified: Azure AI Fundamentals (AI-900) - Microsoft
Microsoft Certified: Azure Fundamentals (AZ-900) - Microsoft
Microsoft Certified: Azure Data Engineer Associate (DP-600) - Microsoft
"""


class ResumeNormalizerRegressionTests(unittest.TestCase):
    def test_aditya_resume_keeps_three_distinct_projects_and_contact_cleanup(self):
        structured = normalize_resume(ResumeNormalizeRequest(rawResumeText=ADITYA_RESUME)).structuredResume

        self.assertEqual(structured.profile.email, "adityarana81027@gmail.com")
        self.assertEqual(structured.profile.location, "Navi Mumbai, India")
        self.assertEqual(
            [project.name for project in structured.projects],
            ["Flight Reservation System", "PCAP Data Analysis (Desktop App)", "Cross-Share Web App"],
        )
        self.assertEqual([len(project.highlights) for project in structured.projects], [3, 3, 3])
        self.assertIn("ASP.NET Core", structured.projects[0].techStack)
        self.assertIn("Electron.js", structured.projects[1].techStack)
        self.assertIn("Django", structured.projects[2].techStack)

    def test_harsh_resume_separates_experience_projects_and_certifications(self):
        structured = normalize_resume(ResumeNormalizeRequest(rawResumeText=HARSH_RESUME)).structuredResume

        self.assertEqual(len(structured.experience), 1)
        experience = structured.experience[0]
        self.assertEqual(experience.company, "Capgemini")
        self.assertEqual(experience.title, "Senior Analyst / Software engineer")
        self.assertEqual(experience.duration, "Jun 2024 - Present")
        self.assertEqual(experience.location, "Navi Mumbai, India")
        self.assertEqual(len(experience.highlights), 4)

        self.assertEqual(
            [project.name for project in structured.projects],
            ["Data Simplified Tool", "AI Agents Platform (GitHub Copilot-Based)"],
        )
        self.assertEqual([len(project.highlights) for project in structured.projects], [2, 2])
        self.assertNotIn("Senior Analyst / Software engineer", " ".join(project.name for project in structured.projects))

        self.assertEqual(len(structured.certifications), 4)
        self.assertTrue(all(cert.startswith("Microsoft Certified:") for cert in structured.certifications))


if __name__ == "__main__":
    unittest.main()
