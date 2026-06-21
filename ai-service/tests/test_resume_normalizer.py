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


MULTI_EXPERIENCE_RESUME = """
Priya Sharma
Contact: priya.sharma@example.com | +91 9876543210 | linkedin.com/in/priyasharma

Summary
Full stack engineer with experience across Java, Spring Boot, React, AWS, and payment platforms.

Experience
TechNova Solutions Jan 2024 - Present - Software Engineer | Pune, India
Built Spring Boot APIs for order management and payment reconciliation.
Improved React dashboards used by operations teams for daily issue tracking.
Integrated AWS S3 and SQS for asynchronous document processing.

BrightApps Pvt Ltd Jun 2022 - Dec 2023 - Associate Software Developer | Mumbai, India
Developed Java microservices for customer onboarding workflows.
Created reusable React components and reduced duplicate UI code.
Optimized SQL queries and reduced report generation time by 30%.

Projects
Invoice Automation Tool | Java, Spring Boot, React, PostgreSQL
Built invoice upload and approval workflow with role-based access.

Skills
Java, Spring Boot, React, AWS, SQL, PostgreSQL
"""


STACKED_EXPERIENCE_RESUME = """
Rahul Mehta
Contact: rahul.mehta@example.com | +91 9988776655 | linkedin.com/in/rahulmehta

Summary
Backend developer with Java, Spring Boot, SQL, Kafka, and cloud deployment experience.

Experience
Software Engineer
CloudWave Technologies
Jan 2024 - Present
Bangalore, India
Built Spring Boot services for loan processing workflows.
Integrated Kafka consumers for asynchronous status updates.
Improved PostgreSQL query performance for reporting APIs.

Associate Developer
MetroSoft Labs
Jul 2022 - Dec 2023
Hyderabad, India
Developed Java REST APIs for customer profile management.
Created SQL reports for operations and finance users.
Resolved production defects in CI/CD releases.

Projects
Loan Risk Engine | Java, Spring Boot, Kafka, PostgreSQL
Built risk scoring workflow for loan applications.

Skills
Java, Spring Boot, Kafka, PostgreSQL, SQL, Git
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

    def test_multi_experience_resume_splits_jobs_without_mixing_highlights(self):
        structured = normalize_resume(ResumeNormalizeRequest(rawResumeText=MULTI_EXPERIENCE_RESUME)).structuredResume

        self.assertEqual(len(structured.experience), 2)
        self.assertEqual(
            [(item.company, item.title, item.duration, item.location, len(item.highlights)) for item in structured.experience],
            [
                ("TechNova Solutions", "Software Engineer", "Jan 2024 - Present", "Pune, India", 3),
                ("BrightApps Pvt Ltd", "Associate Software Developer", "Jun 2022 - Dec 2023", "Mumbai, India", 3),
            ],
        )
        self.assertIn("Spring Boot APIs", structured.experience[0].highlights[0])
        self.assertIn("Java microservices", structured.experience[1].highlights[0])
        self.assertEqual([project.name for project in structured.projects], ["Invoice Automation Tool"])

    def test_stacked_experience_layout_splits_title_company_date_location(self):
        structured = normalize_resume(ResumeNormalizeRequest(rawResumeText=STACKED_EXPERIENCE_RESUME)).structuredResume

        self.assertEqual(len(structured.experience), 2)
        self.assertEqual(
            [(item.title, item.company, item.duration, item.location, len(item.highlights)) for item in structured.experience],
            [
                ("Software Engineer", "CloudWave Technologies", "Jan 2024 - Present", "Bangalore, India", 3),
                ("Associate Developer", "MetroSoft Labs", "Jul 2022 - Dec 2023", "Hyderabad, India", 3),
            ],
        )
        self.assertIn("Spring Boot services", structured.experience[0].highlights[0])
        self.assertIn("Java REST APIs", structured.experience[1].highlights[0])
        self.assertEqual([project.name for project in structured.projects], ["Loan Risk Engine"])


if __name__ == "__main__":
    unittest.main()
