from app.db import get_connection, initialize_database
from app.models.analysis import (
    AnalysisResponse,
    AnalyzeRequest,
    CandidateContext,
    CrossQuestion,
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
from app.models.demo import DemoSeedRequest, DemoSeedResponse
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


def seed_demo_workspace(request: DemoSeedRequest) -> DemoSeedResponse:
    initialize_database()
    if request.reset:
        with get_connection() as connection:
            connection.execute("DELETE FROM users WHERE id = ?", (request.userId,))

    user = create_or_update_user_password(
        user_id=request.userId,
        display_name=request.displayName,
        email=request.email,
        password=request.password,
        requested_subscription_tier=request.subscriptionTier,
    )
    resume = save_resume(_demo_resume(request.userId))
    jd = save_job_description(_demo_jd(request.userId))
    analysis_request = _demo_analysis_request(resume.rawText, jd.rawText, request.userId)
    analysis_response = _demo_analysis_response()
    analysis = save_analysis(
        AnalysisSaveRequest(
            userId=request.userId,
            title="Demo Match: Python AI Full Stack Engineer",
            resumeId=resume.id,
            jobDescriptionId=jd.id,
            fingerprint="demo-python-ai-fullstack-ui-0001",
            request=analysis_request,
            response=analysis_response,
            optionalArtifacts={"preparationPlan": True, "gapReport": True, "interviewQuestions": True},
        )
    )
    preparation = save_preparation_session(
        PreparationSessionSaveRequest(
            userId=request.userId,
            analysisId=analysis.id,
            title="Demo 7-day AI full stack prep",
            status="in_progress",
            plan=analysis_response.preparationIntelligence or {},
            progress={"completedDays": [1, 2], "currentDay": 3, "notes": "Demo progress for portfolio review."},
        )
    )
    opportunity = save_job_opportunity(
        JobOpportunitySaveRequest(
            userId=request.userId,
            resumeId=resume.id,
            analysisId=analysis.id,
            title=jd.title,
            company=jd.company,
            location="Bengaluru / Remote",
            url="https://example.com/jobs/python-ai-fullstack",
            description=jd.rawText,
            status="interview",
            technicalMatchScore=analysis_response.technicalMatchScore,
            fitCategory=analysis_response.fitCategory,
            analysisResponse=analysis_response,
            optionalArtifacts={"preparationSessionId": preparation.id},
        )
    )
    save_comparison_run(
        ComparisonRunSaveRequest(
            userId=request.userId,
            title="Demo comparison: resume vs Python AI JD",
            resumeIds=[resume.id],
            jobDescriptionIds=[jd.id],
            results=[
                ComparisonResultItem(
                    id=f"{resume.id}:{jd.id}",
                    resumeId=resume.id,
                    resumeTitle=resume.title,
                    jobDescriptionId=jd.id,
                    jobTitle=jd.title,
                    company=jd.company,
                    score=analysis_response.technicalMatchScore,
                    fitCategory=analysis_response.fitCategory,
                    recommendedAction=analysis_response.recommendedAction,
                )
            ],
        )
    )
    save_extension_validation(
        ExtensionValidationSaveRequest(
            userId=request.userId,
            site="LinkedIn",
            url="https://www.linkedin.com/jobs/view/demo",
            parserRating="partial",
            autoParsed=True,
            manualPasteUsed=True,
            titleFound=True,
            companyFound=True,
            descriptionFound=False,
            notes="Demo validation: title/company detected, manual JD fallback used.",
        )
    )
    save_match_feedback(
        MatchFeedbackSaveRequest(
            userId=request.userId,
            analysisId=analysis.id,
            jobOpportunityId=opportunity.id,
            roleFamily="Data/AI",
            expectedFit="good",
            scoreAccuracy="accurate",
            outcome="interview",
            algorithmScore=analysis_response.technicalMatchScore,
            fitCategory=analysis_response.fitCategory,
            notes="Demo feedback label for calibration dashboard.",
        )
    )
    for module in ("score", "prep_plan", "gap_report", "interview_questions", "extension_match"):
        record_usage_event(module=module, user_id=request.userId, mode="mock", provider="demo", model="seed-data")

    token = create_user_session(request.userId, source="demo-seed")
    summary = get_workspace_summary(request.userId)
    return DemoSeedResponse(
        userId=user.id,
        displayName=user.displayName,
        email=user.email,
        password=request.password,
        subscriptionTier=user.subscriptionTier,
        resumeCount=summary.resumeCount,
        jobDescriptionCount=summary.jobDescriptionCount,
        analysisCount=summary.analysisCount,
        preparationSessionCount=summary.preparationSessionCount,
        jobOpportunityCount=summary.jobOpportunityCount,
        averageMatchScore=summary.averageMatchScore,
        sessionToken=token,
        message="Demo workspace seeded. Use the returned login to show history, score, prep, extension, evaluation, and usage dashboards.",
    )


def _demo_resume(user_id: str) -> ResumeSaveRequest:
    raw_text = """Aditya Demo
Full Stack + AI Developer | Navi Mumbai | demo.aditya@example.com

Summary
Full-stack developer with Python, Django, React, SQL, Power BI, Azure fundamentals, and AI-agent workflow automation experience.

Experience
Senior Analyst / Software Engineer | Capgemini | Navi Mumbai | May 2024 - Present
- Built Django and React applications for enterprise reporting workflows.
- Designed ETL pipelines and Power BI dashboards over operational datasets.
- Developed AI-agent automation for pipeline triggering, job fetching, and validation.

Projects
Data Simplified Tool | React, Django, Python, SQL
- Built data quality modules for metadata analysis, SQL validation, and cross-database comparison.

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
            location="Navi Mumbai",
            email="demo.aditya@example.com",
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
                highlights=["Built metadata analysis, SQL validation, and cross-database comparison modules."],
            ),
            ResumeProject(
                name="AI Agents Platform",
                techStack=["Python", "Azure Data Factory", "ADLS", "Control-M"],
                highlights=["Integrated AI agents with ADF, ADLS, Control-M, and databases."],
            ),
        ],
        skills=["Python", "Django", "React", "SQL", "Power BI", "Azure", "REST APIs", "JavaScript", "ETL", "AI Agents"],
        education=["B.Tech Mechanical Engineering, Acropolis Institute of Technology and Research, 2019-2023"],
        certifications=["Microsoft Certified: Azure AI Fundamentals", "Microsoft Certified: Azure Fundamentals AZ-900"],
    )
    return ResumeSaveRequest(userId=user_id, title="Demo Resume - Full Stack AI", source="manual", rawText=raw_text, normalizedText=raw_text, structuredResume=structured)


def _demo_jd(user_id: str) -> JobDescriptionSaveRequest:
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
        responsibilities=["Build scalable APIs and frontend modules.", "Design ETL validation workflows.", "Integrate AI-assisted automation."],
        locations=["Bengaluru", "Remote"],
        workModes=["remote", "hybrid"],
        senioritySignals=["2-4 years", "API and data workflow ownership"],
    )
    return JobDescriptionSaveRequest(userId=user_id, title="Python AI Full Stack Engineer", company="DemoFin Analytics", rawText=raw_text, normalizedText=raw_text, parsedJobDescription=parsed)


def _demo_analysis_request(resume_text: str, jd_text: str, user_id: str) -> AnalyzeRequest:
    return AnalyzeRequest(
        resumeText=resume_text,
        jobDescriptionText=jd_text,
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
        scoringCalibrationUserId=user_id,
        roleFamily="Data/AI",
    )


def _demo_analysis_response() -> AnalysisResponse:
    prep = PreparationIntelligence(
        summary="Focus on APIs, ETL reliability, AI-agent safety, and cloud fundamentals.",
        priorityTopics=[
            PriorityTopic(topic="AI-agent safety", priority="critical", sourceRequirement="AI-assisted automation", reason="Most differentiated JD requirement.", currentEvidence="AI Agents Platform", targetDepth="Explain tool permissions, validation, audit logs, and rollback.", actions=["Prepare one architecture story.", "List failure modes."]),
            PriorityTopic(topic="ETL validation", priority="high", sourceRequirement="ETL validation workflows", reason="Strong project match.", currentEvidence="Data Simplified Tool", targetDepth="Explain metadata, SQL checks, retries, and reconciliation.", actions=["Revise SQL examples."]),
        ],
        dailyPlan=[
            PreparationDay(day=1, focus="Resume/JD story mapping", goal="Create two project stories", tasks=["Map JD requirements to resume bullets.", "Rewrite AI-agent impact."], output="Two STAR stories."),
            PreparationDay(day=2, focus="Django APIs", goal="Revise backend design", tasks=["Review auth, pagination, idempotency, and errors."], output="API checklist."),
            PreparationDay(day=3, focus="ETL reliability", goal="Handle data workflow questions", tasks=["Revise validation, retries, reconciliation, and audit logs."], output="ETL notes."),
            PreparationDay(day=4, focus="AI-agent architecture", goal="Explain guardrails", tasks=["Prepare tool-calling, permissions, confirmations, and rollback answers."], output="Agent safety checklist."),
        ],
    )
    return AnalysisResponse(
        technicalMatchScore=84,
        shortlistingScore=76,
        interviewReadinessScore=72,
        overallOpportunityScore=79,
        overallSummary="Strong technical overlap for Python, Django, React, SQL, ETL, dashboards, and AI-agent automation.",
        fitCategory="Strong Fit",
        scoreBreakdown=[
            ScoreBreakdownItem(category="coreSkills", weight=25, score=88, weightedScore=22.0, reason="Python, Django, React, SQL, REST APIs, and ETL evidence are present."),
            ScoreBreakdownItem(category="projectEvidence", weight=20, score=86, weightedScore=17.2, reason="Projects show AI agents, ETL validation, and data quality tooling."),
            ScoreBreakdownItem(category="experienceFit", weight=15, score=80, weightedScore=12.0, reason="3 years aligns with the 2-4 year band."),
        ],
        shortlistingFactors=[ShortlistingFactor(factor="Location", impact="positive", reason="Remote/Bengaluru/Pune preferences align."), ShortlistingFactor(factor="Notice period", impact="neutral", reason="60 days is acceptable but not immediate.")],
        requirementMatches=[
            RequirementMatch(requirement="Python backend development", category="backend", importance="high", bestEvidence="Built Django applications and AI-agent automation in Python.", evidenceSource="experience", score=90, matchType="semantic+exact", reason="Direct Python and Django evidence."),
            RequirementMatch(requirement="Cloud fundamentals", category="cloud", importance="medium", bestEvidence="Azure Fundamentals and Azure AI Fundamentals certifications.", evidenceSource="certification", score=72, matchType="certification-equivalent", reason="Certifications support fundamentals."),
        ],
        recommendedAction="Apply. Prepare AI-agent architecture, ETL reliability, SQL optimization, and cloud deployment cross-questions.",
        matchingSkills=[MatchingSkill(skill="Python", evidenceFromResume="Django applications and AI agents", jdRequirement="Python"), MatchingSkill(skill="React", evidenceFromResume="Data Simplified Tool frontend", jdRequirement="React")],
        weaklyEvidencedSkills=[WeaklyEvidencedSkill(skill="Cloud deployment", source="certifications", whyWeak="Cloud appears mostly through certifications.", howToStrengthenResume="Add deployment, monitoring, or release ownership evidence.")],
        missingSkills=[MissingSkill(skill="Production monitoring", importance="medium", whyItMatters="JD expects reliability tradeoffs.", howToPrepare="Revise logs, metrics, alerts, retries, and dashboards.")],
        resumeImprovements=[ResumeImprovement(currentIssue="AI-agent impact is broad.", suggestedBullet="Designed Python AI-agent workflows integrated with ADF, ADLS, Control-M, and SQL validation, reducing manual operational checks by 30%.", reason="Connects tools, action, and measurable impact.")],
        interviewQuestions=[InterviewQuestion(topic="Django APIs", question="How would you design a Django REST API for long-running ETL validation jobs?", difficulty="medium", expectedFocus="Async execution, job state, idempotency, logs, and retries.")],
        crossQuestions=[CrossQuestion(question="How do you prevent an AI agent from triggering the wrong pipeline?", whyAsked="Tests guardrail thinking.", expectedAnswerHint="Discuss tool permissions, validation, audit logs, and confirmation.")],
        systemDesignReadiness=SystemDesignReadiness(level="moderate", reason="Good application and data workflow exposure; sharpen reliability patterns.", topicsToPrepare=["job queues", "observability", "data validation architecture"]),
        sevenDayPlan=[DayPlan(day=1, focus="Story mapping", tasks=["Map JD to resume."]), DayPlan(day=2, focus="Django APIs", tasks=["Review API design."])],
        preparationIntelligence=prep,
        debug=DebugInfo(mode="mock", provider="demo", model="seed-data", promptPreview="Demo seed response", receivedExperienceYears=3, receivedTargetRole="Python AI Full Stack Engineer", receivedCurrentStack=["Python", "Django", "React", "SQL"], scoreReason="Seeded explainable demo score."),
    )
