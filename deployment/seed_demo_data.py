import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_DIR = ROOT / "ai-service"
if str(AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_DIR))

from app.db import get_connection, initialize_database
from app.models.analysis import (
    AnalysisResponse,
    AnalyzeRequest,
    CandidateContext,
    CrossQuestion,
    CrossQuestionChain,
    DayPlan,
    DebugInfo,
    InterviewQuestion,
    LlmOptions,
    MatchingSkill,
    MissingSkill,
    PreparationDay,
    PreparationIntelligence,
    PriorityTopic,
    RequirementMatch,
    ResumeImprovement,
    ScoreBreakdownItem,
    ShortlistingFactor,
    SystemDesignReadiness,
    WeaklyEvidencedSkill,
)
from app.models.evaluation import MatchFeedbackSaveRequest
from app.models.extension import ExtensionValidationSaveRequest
from app.models.history import (
    AnalysisSaveRequest,
    ComparisonResultItem,
    ComparisonRunSaveRequest,
    JobDescriptionSaveRequest,
    JobOpportunitySaveRequest,
    PreparationSessionSaveRequest,
    ResumeSaveRequest,
)
from app.models.jd_parse import ExperienceRange, ParsedJobDescription
from app.models.resume_normalize import ResumeExperience, ResumeProfile, ResumeProject, StructuredResume
from app.services.history_store import (
    create_or_update_user_password,
    create_user_session,
    get_workspace_summary,
    record_usage_event,
    save_analysis,
    save_comparison_run,
    save_extension_validation,
    save_job_description,
    save_job_opportunity,
    save_match_feedback,
    save_preparation_session,
    save_resume,
)


DEMO_USER_ID = "demo-aditya"
DEMO_PASSWORD = "DemoPass123!"


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Career Agent OS demo data for portfolio reviews.")
    parser.add_argument("--user-id", default=DEMO_USER_ID, help="Demo user id to create/update.")
    parser.add_argument("--display-name", default="Aditya Demo", help="Demo display name.")
    parser.add_argument("--email", default="demo.aditya@example.com", help="Demo email.")
    parser.add_argument("--password", default=DEMO_PASSWORD, help="Password to set for the demo user.")
    parser.add_argument("--premium", action="store_true", help="Seed the user as premium instead of free.")
    parser.add_argument("--reset", action="store_true", help="Delete this demo user and all cascaded demo records before seeding.")
    parser.add_argument("--print-token", action="store_true", help="Create and print a web-demo session token.")
    args = parser.parse_args()

    initialize_database()
    if args.reset:
        reset_demo_user(args.user_id)

    user = create_or_update_user_password(
        user_id=args.user_id,
        display_name=args.display_name,
        email=args.email,
        password=args.password,
        requested_subscription_tier="premium" if args.premium else "free",
    )

    resume_primary = save_resume(primary_resume(args.user_id))
    resume_alt = save_resume(alternate_resume(args.user_id))
    jd_python_ai = save_job_description(python_ai_jd(args.user_id))
    jd_dotnet = save_job_description(dotnet_jd(args.user_id))

    analysis = save_analysis(
        AnalysisSaveRequest(
            userId=args.user_id,
            title="Demo Match: Python AI Full Stack Engineer",
            resumeId=resume_primary.id,
            jobDescriptionId=jd_python_ai.id,
            fingerprint="demo-python-ai-fullstack-0001",
            request=analysis_request(),
            response=analysis_response(),
            optionalArtifacts={
                "preparationPlan": True,
                "gapReport": True,
                "interviewQuestions": True,
                "crossQuestions": True,
            },
        )
    )
    preparation = save_preparation_session(
        PreparationSessionSaveRequest(
            userId=args.user_id,
            analysisId=analysis.id,
            title="7-day Python AI Full Stack prep",
            status="in_progress",
            plan=preparation_intelligence(),
            progress={
                "completedDays": [1, 2],
                "currentDay": 3,
                "notes": "REST API and Django revision done. Next focus: ETL design and AI-agent validation tradeoffs.",
            },
        )
    )
    opportunity = save_job_opportunity(
        JobOpportunitySaveRequest(
            userId=args.user_id,
            resumeId=resume_primary.id,
            analysisId=analysis.id,
            title="Python AI Full Stack Engineer",
            company="DemoFin Analytics",
            location="Bengaluru / Remote",
            url="https://example.com/jobs/python-ai-fullstack",
            description=jd_python_ai.rawText,
            status="interview",
            technicalMatchScore=analysis.response.technicalMatchScore,
            fitCategory=analysis.response.fitCategory,
            analysisResponse=analysis.response,
            optionalArtifacts={"preparationSessionId": preparation.id},
        )
    )
    save_job_opportunity(
        JobOpportunitySaveRequest(
            userId=args.user_id,
            resumeId=resume_alt.id,
            title=".NET Full Stack Developer",
            company="RetailCloud Systems",
            location="Pune",
            url="https://example.com/jobs/dotnet-fullstack",
            description=jd_dotnet.rawText,
            status="applied",
            technicalMatchScore=78,
            fitCategory="Good Fit",
        )
    )
    save_comparison_run(
        ComparisonRunSaveRequest(
            userId=args.user_id,
            title="Demo comparison: saved resumes vs saved JDs",
            resumeIds=[resume_primary.id, resume_alt.id],
            jobDescriptionIds=[jd_python_ai.id, jd_dotnet.id],
            results=[
                ComparisonResultItem(
                    id=f"{resume_primary.id}:{jd_python_ai.id}",
                    resumeId=resume_primary.id,
                    resumeTitle=resume_primary.title,
                    jobDescriptionId=jd_python_ai.id,
                    jobTitle=jd_python_ai.title,
                    company=jd_python_ai.company,
                    score=84,
                    fitCategory="Strong Fit",
                    recommendedAction="Apply and prepare AI-agent design, ETL reliability, and Django API deep dives.",
                ),
                ComparisonResultItem(
                    id=f"{resume_alt.id}:{jd_dotnet.id}",
                    resumeId=resume_alt.id,
                    resumeTitle=resume_alt.title,
                    jobDescriptionId=jd_dotnet.id,
                    jobTitle=jd_dotnet.title,
                    company=jd_dotnet.company,
                    score=78,
                    fitCategory="Good Fit",
                    recommendedAction="Apply if location and notice period fit. Strengthen Azure deployment evidence.",
                ),
            ],
        )
    )
    save_extension_validation(
        ExtensionValidationSaveRequest(
            userId=args.user_id,
            site="LinkedIn",
            url="https://www.linkedin.com/jobs/view/demo",
            parserRating="partial",
            autoParsed=True,
            manualPasteUsed=True,
            titleFound=True,
            companyFound=True,
            descriptionFound=False,
            notes="Demo record: title/company detected, JD manually pasted because page body was incomplete.",
        )
    )
    save_match_feedback(
        MatchFeedbackSaveRequest(
            userId=args.user_id,
            analysisId=analysis.id,
            jobOpportunityId=opportunity.id,
            roleFamily="Data/AI",
            expectedFit="good",
            scoreAccuracy="accurate",
            outcome="interview",
            algorithmScore=84,
            fitCategory="Strong Fit",
            notes="Demo label: score is acceptable because resume has Python, Django, React, SQL, Power BI, and AI-agent evidence.",
        )
    )
    for module in ("score", "prep_plan", "gap_report", "interview_questions", "extension_match"):
        record_usage_event(module=module, user_id=args.user_id, mode="mock", provider="demo", model="seed-data", estimated_units=1)

    session_token = create_user_session(args.user_id, source="demo-seed") if args.print_token else None
    summary = get_workspace_summary(args.user_id)
    payload = {
        "user": user.model_dump(),
        "resumeCount": summary.resumeCount,
        "jobDescriptionCount": summary.jobDescriptionCount,
        "analysisCount": summary.analysisCount,
        "preparationSessionCount": summary.preparationSessionCount,
        "jobOpportunityCount": summary.jobOpportunityCount,
        "averageMatchScore": summary.averageMatchScore,
        "sessionToken": session_token,
        "login": {"userIdOrEmail": args.user_id, "password": args.password},
    }
    print(json.dumps(payload, indent=2))
    return 0


def reset_demo_user(user_id: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))


def primary_resume(user_id: str) -> ResumeSaveRequest:
    raw_text = """Aditya Demo
Full Stack + AI Developer
Navi Mumbai, India | demo.aditya@example.com | github.com/Aadi-404

Summary
Full-stack developer with 3 years of experience across Django, React, Python, SQL, Power BI, Azure fundamentals, and AI-agent workflow automation.

Experience
Senior Analyst / Software Engineer | Capgemini | Navi Mumbai | May 2024 - Present
- Built Django and React applications for enterprise reporting workflows.
- Designed ETL pipelines and Power BI dashboards over high-volume operational datasets.
- Developed AI-agent automation for pipeline triggering, job fetching, and validation.

Projects
Data Simplified Tool | React, Django, Python, SQL
- Built a data quality platform connecting to SSMS and Snowflake.
- Added metadata analysis, SQL validation, and cross-database comparison.

AI Agents Platform | Python, Azure Data Factory, ADLS, Control-M
- Integrated AI agents with ADF, ADLS, Control-M, and databases.
- Reduced manual validation overhead by automating STTM parsing and checks.

Skills
Python, Django, React, SQL, Power BI, Azure, REST APIs, JavaScript, ETL, AI Agents

Certifications
Microsoft Certified: Azure AI Fundamentals
Microsoft Certified: Azure Fundamentals AZ-900
"""
    structured = StructuredResume(
        profile=ResumeProfile(
            name="Aditya Demo",
            location="Navi Mumbai, India",
            email="demo.aditya@example.com",
            github="github.com/Aadi-404",
            summary="Full-stack and AI-focused developer with Django, React, SQL, Power BI, Azure, and automation experience.",
        ),
        experience=[
            ResumeExperience(
                title="Senior Analyst / Software Engineer",
                company="Capgemini",
                duration="May 2024 - Present",
                location="Navi Mumbai",
                highlights=[
                    "Built Django and React applications for enterprise reporting workflows.",
                    "Designed ETL pipelines and Power BI dashboards over operational datasets.",
                    "Developed AI-agent automation for pipeline triggering, job fetching, and validation.",
                ],
            )
        ],
        projects=[
            ResumeProject(
                name="Data Simplified Tool",
                techStack=["React", "Django", "Python", "SQL"],
                highlights=[
                    "Built a data quality platform connecting to SSMS and Snowflake.",
                    "Added metadata analysis, SQL validation, and cross-database comparison.",
                ],
            ),
            ResumeProject(
                name="AI Agents Platform",
                techStack=["Python", "Azure Data Factory", "ADLS", "Control-M"],
                highlights=[
                    "Integrated AI agents with ADF, ADLS, Control-M, and databases.",
                    "Reduced manual validation overhead by automating STTM parsing and checks.",
                ],
            ),
        ],
        skills=["Python", "Django", "React", "SQL", "Power BI", "Azure", "REST APIs", "JavaScript", "ETL", "AI Agents"],
        education=["B.Tech Mechanical Engineering, Acropolis Institute of Technology and Research, 2019-2023"],
        certifications=["Microsoft Certified: Azure AI Fundamentals", "Microsoft Certified: Azure Fundamentals AZ-900"],
    )
    return ResumeSaveRequest(userId=user_id, title="Demo Resume - Full Stack AI", source="manual", rawText=raw_text, normalizedText=raw_text, structuredResume=structured)


def alternate_resume(user_id: str) -> ResumeSaveRequest:
    raw_text = """Aditya Demo
.NET Full Stack Developer

Experience
Software Engineer | Capgemini | Navi Mumbai
- Built ASP.NET Core APIs, Angular screens, SQL Server queries, and Entity Framework data access.
- Supported production issue triage and API performance improvements.

Projects
Flight Reservation System | ASP.NET Core, Angular, SQL Server
- Built booking, search, admin, and CRUD modules.

Skills
C#, ASP.NET Core, Angular, SQL Server, Entity Framework, REST APIs, Azure Fundamentals
"""
    structured = StructuredResume(
        profile=ResumeProfile(name="Aditya Demo", location="Navi Mumbai", email="demo.aditya@example.com"),
        experience=[
            ResumeExperience(
                title="Software Engineer",
                company="Capgemini",
                duration="May 2024 - Present",
                location="Navi Mumbai",
                highlights=["Built ASP.NET Core APIs, Angular screens, SQL Server queries, and Entity Framework data access."],
            )
        ],
        projects=[
            ResumeProject(
                name="Flight Reservation System",
                techStack=["ASP.NET Core", "Angular", "SQL Server"],
                highlights=["Built booking, search, admin, and CRUD modules."],
            )
        ],
        skills=["C#", "ASP.NET Core", "Angular", "SQL Server", "Entity Framework", "REST APIs", "Azure Fundamentals"],
        education=["B.Tech Mechanical Engineering, Acropolis Institute of Technology and Research, 2019-2023"],
        certifications=["Microsoft Certified: Azure Fundamentals AZ-900"],
    )
    return ResumeSaveRequest(userId=user_id, title="Demo Resume - .NET Full Stack", source="manual", rawText=raw_text, normalizedText=raw_text, structuredResume=structured)


def python_ai_jd(user_id: str) -> JobDescriptionSaveRequest:
    raw_text = """Python AI Full Stack Engineer
Company: DemoFin Analytics
Location: Bengaluru / Remote
Experience: 2-4 years

Required skills: Python, Django or FastAPI, React, SQL, REST APIs, ETL pipelines, cloud fundamentals.
Preferred skills: Power BI, Azure Data Factory, AI agents, LLM workflow automation.
Responsibilities:
- Build scalable APIs and frontend modules for data products.
- Design ETL validation workflows and dashboards.
- Integrate AI-assisted automation with existing data pipelines.
- Explain tradeoffs around reliability, monitoring, and security.
"""
    parsed = ParsedJobDescription(
        roleTitle="Python AI Full Stack Engineer",
        experienceRange=ExperienceRange(minYears=2, maxYears=4),
        requiredSkills=["Python", "Django or FastAPI", "React", "SQL", "REST APIs", "ETL pipelines", "cloud fundamentals"],
        preferredSkills=["Power BI", "Azure Data Factory", "AI agents", "LLM workflow automation"],
        emphasizedRequirements=["AI-assisted automation", "ETL validation workflows", "reliability and monitoring"],
        responsibilities=[
            "Build scalable APIs and frontend modules for data products.",
            "Design ETL validation workflows and dashboards.",
            "Integrate AI-assisted automation with existing data pipelines.",
        ],
        locations=["Bengaluru", "Remote"],
        workModes=["remote", "hybrid"],
        senioritySignals=["2-4 years", "ownership of APIs and data workflows"],
    )
    return JobDescriptionSaveRequest(userId=user_id, title="Python AI Full Stack Engineer", company="DemoFin Analytics", rawText=raw_text, normalizedText=raw_text, parsedJobDescription=parsed)


def dotnet_jd(user_id: str) -> JobDescriptionSaveRequest:
    raw_text = """Senior .NET Full Stack Developer
Company: RetailCloud Systems
Location: Pune
Experience: 2-5 years

Required skills: ASP.NET Core, C#, Angular, SQL Server, Entity Framework, REST APIs.
Preferred skills: Azure, CI/CD, production debugging, microservices basics.
Responsibilities:
- Build backend APIs and Angular dashboards.
- Improve SQL query performance and API reliability.
- Support releases and production issue analysis.
"""
    parsed = ParsedJobDescription(
        roleTitle="Senior .NET Full Stack Developer",
        experienceRange=ExperienceRange(minYears=2, maxYears=5),
        requiredSkills=["ASP.NET Core", "C#", "Angular", "SQL Server", "Entity Framework", "REST APIs"],
        preferredSkills=["Azure", "CI/CD", "production debugging", "microservices basics"],
        emphasizedRequirements=["API reliability", "SQL performance", "production support"],
        responsibilities=["Build backend APIs and Angular dashboards.", "Improve SQL query performance and API reliability."],
        locations=["Pune"],
        workModes=["hybrid"],
        senioritySignals=["2-5 years", "production issue analysis"],
    )
    return JobDescriptionSaveRequest(userId=user_id, title="Senior .NET Full Stack Developer", company="RetailCloud Systems", rawText=raw_text, normalizedText=raw_text, parsedJobDescription=parsed)


def analysis_request() -> AnalyzeRequest:
    return AnalyzeRequest(
        resumeText=primary_resume("demo-aditya").rawText,
        jobDescriptionText=python_ai_jd("demo-aditya").rawText,
        candidateContext=CandidateContext(
            targetRole="Python AI Full Stack Engineer",
            experienceYears=3,
            currentStack=["Python", "Django", "React", "SQL", "Power BI", "Azure"],
            targetMarket="India product and analytics companies",
            currentLocation="Navi Mumbai",
            preferredLocations=["Remote", "Bengaluru", "Pune"],
            noticePeriodDays=60,
            workModePreference=["remote", "hybrid"],
            relocationOpen=True,
        ),
        llmOptions=LlmOptions(mode="mock", provider="groq", model="demo-seed"),
        preparationPlanDays=7,
        roleFamily="Data/AI",
    )


def analysis_response() -> AnalysisResponse:
    prep = preparation_intelligence()
    return AnalysisResponse(
        technicalMatchScore=84,
        shortlistingScore=76,
        interviewReadinessScore=72,
        overallOpportunityScore=79,
        overallSummary="Strong technical overlap for Python, Django, React, SQL, ETL, dashboards, and AI-agent automation. Cloud depth and production monitoring examples should be strengthened before interviews.",
        fitCategory="Strong Fit",
        scoreBreakdown=[
            ScoreBreakdownItem(category="coreSkills", weight=25, score=88, weightedScore=22.0, reason="Python, Django, React, SQL, REST APIs, and ETL evidence are present."),
            ScoreBreakdownItem(category="projectEvidence", weight=20, score=86, weightedScore=17.2, reason="Projects show AI agents, ETL validation, SQL checks, and data quality tooling."),
            ScoreBreakdownItem(category="experienceFit", weight=15, score=80, weightedScore=12.0, reason="3 years aligns with the 2-4 year band."),
            ScoreBreakdownItem(category="cloudAndData", weight=15, score=74, weightedScore=11.1, reason="Azure fundamentals and ADF evidence exist, but deployment ownership is not deep."),
        ],
        shortlistingFactors=[
            ShortlistingFactor(factor="Location", impact="positive", reason="Remote/Bengaluru/Pune preferences align with JD flexibility."),
            ShortlistingFactor(factor="Notice period", impact="neutral", reason="60 days is acceptable but weaker than immediate availability."),
        ],
        requirementMatches=[
            RequirementMatch(requirement="Python backend development", category="backend", importance="high", bestEvidence="Built Django applications and AI-agent automation in Python.", evidenceSource="experience", score=90, matchType="semantic+exact", reason="Resume directly shows Python and Django production-style work."),
            RequirementMatch(requirement="ETL validation workflows", category="data", importance="high", bestEvidence="Designed ETL pipelines and data quality modules with SQL validation.", evidenceSource="project", score=86, matchType="semantic", reason="Evidence matches workflow meaning even when wording differs."),
            RequirementMatch(requirement="Cloud fundamentals", category="cloud", importance="medium", bestEvidence="Azure Fundamentals and Azure AI Fundamentals certifications.", evidenceSource="certification", score=72, matchType="certification-equivalent", reason="Certifications support fundamentals, but hands-on deployment evidence is limited."),
        ],
        recommendedAction="Apply. Prepare AI-agent architecture, ETL reliability, SQL optimization, and cloud deployment cross-questions.",
        matchingSkills=[
            MatchingSkill(skill="Python", evidenceFromResume="AI Agents Platform and Django applications", jdRequirement="Python"),
            MatchingSkill(skill="React", evidenceFromResume="Data Simplified Tool frontend", jdRequirement="React"),
            MatchingSkill(skill="SQL", evidenceFromResume="SQL validation and cross-database comparison", jdRequirement="SQL"),
        ],
        weaklyEvidencedSkills=[
            WeaklyEvidencedSkill(skill="Cloud deployment", source="certifications", whyWeak="Cloud appears mostly through Azure fundamentals and ADF integration.", howToStrengthenResume="Add one bullet on deployment, monitoring, access control, or release ownership."),
        ],
        missingSkills=[
            MissingSkill(skill="Production monitoring", importance="medium", whyItMatters="JD expects reliability and monitoring tradeoffs.", howToPrepare="Revise logs, metrics, alerting, retry, timeout, and dashboarding patterns."),
        ],
        resumeImprovements=[
            ResumeImprovement(currentIssue="AI-agent impact is broad but architecture is not explicit.", suggestedBullet="Designed Python AI-agent workflows integrated with ADF, ADLS, Control-M, and SQL validation, reducing manual operational checks by 30%.", reason="Connects tools, action, and measurable impact."),
        ],
        interviewQuestions=[
            InterviewQuestion(topic="Django APIs", question="How would you design a Django REST API for long-running ETL validation jobs?", difficulty="medium", expectedFocus="Async execution, job state, idempotency, logs, and retries."),
            InterviewQuestion(topic="AI agents", question="How do you prevent an AI agent from triggering the wrong data pipeline?", difficulty="hard", expectedFocus="Tool permissions, confirmation, validation, audit logs, and rollback."),
        ],
        crossQuestions=[
            CrossQuestion(question="Why did you choose Django instead of FastAPI?", whyAsked="Tests framework tradeoff understanding.", expectedAnswerHint="Discuss team familiarity, ORM/admin needs, async requirements, and performance constraints."),
        ],
        systemDesignReadiness=SystemDesignReadiness(level="moderate", reason="Good application and data workflow exposure, but should sharpen scalability and reliability patterns.", topicsToPrepare=["API rate limiting", "job queues", "observability", "data validation architecture"]),
        sevenDayPlan=[DayPlan(day=day.day, focus=day.focus, tasks=day.tasks) for day in prep.dailyPlan],
        preparationIntelligence=prep,
        debug=DebugInfo(mode="mock", provider="demo", model="seed-data", promptPreview="Demo seed response", receivedExperienceYears=3, receivedTargetRole="Python AI Full Stack Engineer", receivedCurrentStack=["Python", "Django", "React", "SQL"], scoreReason="Seeded explainable demo score."),
    )


def preparation_intelligence() -> PreparationIntelligence:
    return PreparationIntelligence(
        summary="Focus on converting project evidence into interview-ready stories around APIs, ETL reliability, AI-agent safety, and cloud fundamentals.",
        priorityTopics=[
            PriorityTopic(topic="AI-agent safety", priority="critical", sourceRequirement="Integrate AI-assisted automation with data pipelines.", reason="This is the most differentiated JD requirement.", currentEvidence="AI Agents Platform", targetDepth="Explain tool permissions, validation, audit logs, and rollback.", actions=["Prepare one architecture diagram.", "Write one failure-mode story."]),
            PriorityTopic(topic="ETL validation", priority="high", sourceRequirement="Design ETL validation workflows.", reason="Strong project match and likely cross-question area.", currentEvidence="Data Simplified Tool", targetDepth="Explain schema checks, metadata checks, SQL validation, and comparison logic.", actions=["Revise SQL validation examples.", "Prepare edge cases."]),
        ],
        dailyPlan=[
            PreparationDay(day=1, focus="JD and resume story alignment", goal="Create two STAR stories", tasks=["Map each JD requirement to a resume bullet.", "Rewrite AI-agent and ETL project explanations."], output="Two polished project stories."),
            PreparationDay(day=2, focus="Django and REST APIs", goal="Revise backend design", tasks=["Review serializers, auth, pagination, idempotency.", "Practice API design cross-questions."], output="API checklist."),
            PreparationDay(day=3, focus="ETL reliability", goal="Handle data workflow questions", tasks=["Revise validation, retries, reconciliation, and audit logs."], output="ETL design notes."),
            PreparationDay(day=4, focus="React and UX", goal="Explain frontend decisions", tasks=["Revise state handling, forms, API errors, and loading states."], output="Frontend answer notes."),
            PreparationDay(day=5, focus="Cloud basics", goal="Connect AZ-900 to practical deployment", tasks=["Revise Azure services, IAM basics, networking, and monitoring."], output="Cloud revision sheet."),
            PreparationDay(day=6, focus="AI-agent architecture", goal="Explain guardrails", tasks=["Prepare tool-calling, permissions, confirmations, and rollback answers."], output="Agent safety checklist."),
            PreparationDay(day=7, focus="Mock interview", goal="Combine all stories", tasks=["Run one mock interview.", "Review weak answers and update notes."], output="Final interview checklist."),
        ],
        crossQuestionChains=[
            CrossQuestionChain(topic="AI Agents Platform", openingQuestion="How does your AI agent trigger a pipeline?", followUps=["How do you validate the requested pipeline?", "What happens if the agent calls the wrong tool?", "How do you audit the action?"], expectedAnswerFocus="Tool registry, permission checks, validation, audit logs, and human confirmation.", risk="Avoid sounding like the LLM has unrestricted production access."),
        ],
        phase5ResearchBacklog=["Search recent Python AI full stack interview experiences.", "Compare Django/FastAPI expectations for Indian product companies."],
    )


if __name__ == "__main__":
    sys.exit(main())
