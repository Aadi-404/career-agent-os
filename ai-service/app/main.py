import re

from fastapi import FastAPI, HTTPException
from fastapi import File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.db import initialize_database
from app.models.analysis import (
    AnalyzeRequest,
    AnalysisResponse,
    CandidateContext,
    CrossQuestion,
    InterviewQuestion,
    OptionalArtifactBuildRequest,
    PreparationBuildRequest,
    PreparationIntelligence,
    RequirementMatch,
    ResumeImprovement,
)
from app.models.extension import (
    ExtensionBootstrapRequest,
    ExtensionBootstrapResponse,
    ExtensionJobDraft,
    ExtensionMatchRequest,
    ExtensionMatchResponse,
    ExtensionPageParseRequest,
    ExtensionResumeOption,
    ExtensionSessionClaimRequest,
    ExtensionSessionClaimResponse,
)
from app.models.history import (
    AnonymousSessionCreateRequest,
    AnonymousSessionRecord,
    AnalysisLookupRequest,
    AnalysisRecord,
    AnalysisSaveRequest,
    JobOpportunityRecord,
    JobOpportunitySaveRequest,
    JobOpportunityStatusUpdateRequest,
    JobDescriptionRecord,
    JobDescriptionSaveRequest,
    PreparationSessionRecord,
    PreparationSessionProgressUpdateRequest,
    PreparationSessionSaveRequest,
    ResumeRecord,
    ResumeSaveRequest,
    UserCreateRequest,
    UserRecord,
    WorkspaceSummary,
)
from app.models.jd_parse import JdParseRequest, JdParseResponse
from app.models.prep_memory import PrepMemoryResponse
from app.models.resume_extract import ResumeExtractResponse
from app.models.resume_normalize import ResumeNormalizeRequest, ResumeNormalizeResponse
from app.services.analyzer_service import analyze_resume_jd, match_resume_jd
from app.services.history_store import (
    create_or_touch_anonymous_session,
    claim_anonymous_session,
    create_or_update_user,
    get_resume,
    get_preparation_session,
    get_workspace_summary,
    list_analyses,
    list_job_descriptions,
    list_job_opportunities_for_anonymous_session,
    list_job_opportunities_for_user,
    list_preparation_sessions,
    list_resumes,
    save_analysis,
    save_job_description,
    save_job_opportunity,
    save_preparation_session,
    lookup_analysis,
    save_resume,
    update_preparation_session_progress,
    update_job_opportunity_status,
)
from app.services.jd_parser import parse_jd
from app.services.optional_artifact_service import (
    build_cross_questions,
    build_interview_questions,
    build_resume_improvements,
)
from app.services.preparation_service import build_preparation_intelligence
from app.services.prep_memory_service import build_prep_memory
from app.services.resume_extractor import extract_resume
from app.services.resume_normalizer import normalize_resume

app = FastAPI(title="Career Agent OS AI Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ai/resume-jd/analyze", response_model=AnalysisResponse)
def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    return analyze_resume_jd(request)


@app.post("/ai/resume-jd/match", response_model=AnalysisResponse)
def match(request: AnalyzeRequest) -> AnalysisResponse:
    return match_resume_jd(request)


@app.post("/ai/match/score", response_model=AnalysisResponse)
def calculate_score(request: AnalyzeRequest) -> AnalysisResponse:
    return match_resume_jd(request)


@app.post("/ai/analysis/gaps", response_model=list[RequirementMatch])
def build_gap_report(request: OptionalArtifactBuildRequest) -> list[RequirementMatch]:
    return [
        match
        for match in request.analysis.requirementMatches
        if match.score < 60
    ][: request.limit]


@app.post("/extension/bootstrap", response_model=ExtensionBootstrapResponse)
def bootstrap_extension(request: ExtensionBootstrapRequest) -> ExtensionBootstrapResponse:
    anonymous_session = create_or_touch_anonymous_session(
        AnonymousSessionCreateRequest(anonymousSessionId=request.anonymousSessionId)
    )
    resumes = list_extension_resumes(request.userId) if request.userId else []
    return ExtensionBootstrapResponse(
        anonymousSession=anonymous_session,
        resumes=resumes,
        manualPasteRequired=not bool(resumes),
        defaultCandidateContext=(
            CandidateContext(
                targetRole="Software Developer",
                experienceYears=0,
                currentStack=["general software engineering"],
                targetMarket="Browser extension job matching",
                relocationOpen=False,
            )
            if not resumes
            else None
        ),
    )


@app.post("/extension/session/claim", response_model=ExtensionSessionClaimResponse)
def claim_extension_session(request: ExtensionSessionClaimRequest) -> ExtensionSessionClaimResponse:
    anonymous_session, migrated_count = claim_anonymous_session(
        request.anonymousSessionId,
        request.userId,
        request.displayName,
        request.email,
    )
    return ExtensionSessionClaimResponse(
        anonymousSession=anonymous_session,
        resumes=list_extension_resumes(request.userId),
        migratedOpportunityCount=migrated_count,
    )


@app.get("/extension/users/{user_id}/resumes", response_model=list[ExtensionResumeOption])
def list_extension_resumes(user_id: str) -> list[ExtensionResumeOption]:
    return [_extension_resume_option(resume) for resume in list_resumes(user_id)]


@app.post("/extension/jobs/parse-page", response_model=ExtensionJobDraft)
def parse_extension_job_page(request: ExtensionPageParseRequest) -> ExtensionJobDraft:
    source_text = (request.selectedText or request.extractedDescription or request.pageText or "").strip()
    warnings = []
    if not request.selectedText:
        warnings.append("No selected text was provided; parsed from visible page text. Manual JD paste may be more accurate.")
    if len(source_text) < 50:
        warnings.append("JD text is short. Ask the user to paste the full job description manually.")
    title = _clean_optional(request.extractedTitle) or _infer_extension_title(request.pageTitle, source_text)
    company = _clean_optional(request.extractedCompany) or _infer_extension_company(request.pageTitle, source_text)
    location = _clean_optional(request.extractedLocation) or _infer_extension_location(source_text)
    parse_confidence = "high" if request.source and request.extractedDescription and len(source_text) >= 300 else "high" if request.selectedText and len(source_text) >= 300 else "medium" if len(source_text) >= 100 else "low"
    return ExtensionJobDraft(
        title=title,
        company=company,
        location=location,
        url=request.pageUrl,
        description=source_text,
        parseConfidence=parse_confidence,
        warnings=warnings,
    )


@app.post("/extension/jobs/match", response_model=ExtensionMatchResponse)
def match_extension_job(request: ExtensionMatchRequest) -> ExtensionMatchResponse:
    if request.anonymousSessionId:
        create_or_touch_anonymous_session(AnonymousSessionCreateRequest(anonymousSessionId=request.anonymousSessionId))

    resume_text = request.resumeText
    if request.resumeId:
        if not request.userId:
            raise HTTPException(status_code=400, detail="userId is required when resumeId is provided")
        resume = get_resume(request.userId, request.resumeId)
        resume_text = resume.normalizedText or resume.rawText

    if not resume_text:
        raise HTTPException(status_code=400, detail="Either resumeId or resumeText is required")

    analysis_request = AnalyzeRequest(
        resumeText=resume_text,
        jobDescriptionText=request.job.description,
        candidateContext=request.candidateContext or _default_extension_candidate_context(request),
        llmOptions=request.llmOptions,
        preparationPlanDays=request.preparationPlanDays,
    )
    analysis = match_resume_jd(analysis_request)
    opportunity = None
    if request.saveOpportunity:
        opportunity = save_job_opportunity(
            JobOpportunitySaveRequest(
                userId=request.userId,
                anonymousSessionId=request.anonymousSessionId,
                resumeId=request.resumeId,
                title=request.job.title,
                company=request.job.company,
                location=request.job.location,
                url=request.job.url,
                description=request.job.description,
                status=request.status,
                technicalMatchScore=analysis.technicalMatchScore,
                fitCategory=analysis.fitCategory,
                analysisResponse=analysis,
            )
        )
    return ExtensionMatchResponse(analysis=analysis, jobOpportunity=opportunity)


@app.post("/ai/preparation/build", response_model=PreparationIntelligence)
def build_preparation(request: PreparationBuildRequest) -> PreparationIntelligence:
    source_request = request.sourceRequest.model_copy(update={"preparationPlanDays": request.preparationPlanDays})
    return build_preparation_intelligence(
        source_request,
        request.analysis.requirementMatches,
        request.analysis.scoreBreakdown,
    )


@app.post("/ai/preparation/plan", response_model=PreparationIntelligence)
def build_preparation_plan_artifact(request: PreparationBuildRequest) -> PreparationIntelligence:
    return build_preparation(request)


@app.post("/ai/resume-improvements/build", response_model=list[ResumeImprovement])
def build_resume_improvement_artifacts(request: OptionalArtifactBuildRequest) -> list[ResumeImprovement]:
    return build_resume_improvements(request.sourceRequest, request.analysis, request.limit)


@app.post("/ai/resume-improvements", response_model=list[ResumeImprovement])
def build_resume_improvement_artifacts_alias(request: OptionalArtifactBuildRequest) -> list[ResumeImprovement]:
    return build_resume_improvement_artifacts(request)


@app.post("/ai/interview-questions/build", response_model=list[InterviewQuestion])
def build_interview_question_artifacts(request: OptionalArtifactBuildRequest) -> list[InterviewQuestion]:
    return build_interview_questions(request.sourceRequest, request.analysis, request.limit)


@app.post("/ai/interview/questions", response_model=list[InterviewQuestion])
def build_interview_question_artifacts_alias(request: OptionalArtifactBuildRequest) -> list[InterviewQuestion]:
    return build_interview_question_artifacts(request)


@app.post("/ai/cross-questions/build", response_model=list[CrossQuestion])
def build_cross_question_artifacts(request: OptionalArtifactBuildRequest) -> list[CrossQuestion]:
    return build_cross_questions(request.sourceRequest, request.analysis, request.limit)


@app.post("/ai/cross-questions", response_model=list[CrossQuestion])
def build_cross_question_artifacts_alias(request: OptionalArtifactBuildRequest) -> list[CrossQuestion]:
    return build_cross_question_artifacts(request)


@app.post("/ai/resume/extract", response_model=ResumeExtractResponse)
async def extract(file: UploadFile = File(...)) -> ResumeExtractResponse:
    return await extract_resume(file)


@app.post("/ai/resume/normalize", response_model=ResumeNormalizeResponse)
def normalize(request: ResumeNormalizeRequest) -> ResumeNormalizeResponse:
    return normalize_resume(request)


@app.post("/ai/jd/parse", response_model=JdParseResponse)
def parse_job_description(request: JdParseRequest) -> JdParseResponse:
    return parse_jd(request)


@app.post("/history/users", response_model=UserRecord)
def upsert_user(request: UserCreateRequest) -> UserRecord:
    return create_or_update_user(request)


@app.post("/auth/anonymous", response_model=AnonymousSessionRecord)
def create_anonymous_session(request: AnonymousSessionCreateRequest | None = None) -> AnonymousSessionRecord:
    return create_or_touch_anonymous_session(request or AnonymousSessionCreateRequest())


@app.get("/history/users/{user_id}/workspace", response_model=WorkspaceSummary)
def workspace_summary(user_id: str) -> WorkspaceSummary:
    return get_workspace_summary(user_id)


@app.post("/history/resumes", response_model=ResumeRecord)
def create_resume_record(request: ResumeSaveRequest) -> ResumeRecord:
    return save_resume(request)


@app.get("/history/users/{user_id}/resumes", response_model=list[ResumeRecord])
def get_resume_records(user_id: str) -> list[ResumeRecord]:
    return list_resumes(user_id)


@app.post("/history/job-descriptions", response_model=JobDescriptionRecord)
def create_job_description_record(request: JobDescriptionSaveRequest) -> JobDescriptionRecord:
    return save_job_description(request)


@app.get("/history/users/{user_id}/job-descriptions", response_model=list[JobDescriptionRecord])
def get_job_description_records(user_id: str) -> list[JobDescriptionRecord]:
    return list_job_descriptions(user_id)


@app.post("/history/analyses", response_model=AnalysisRecord)
def create_analysis_record(request: AnalysisSaveRequest) -> AnalysisRecord:
    return save_analysis(request)


@app.post("/history/analyses/lookup", response_model=AnalysisRecord | None)
def lookup_analysis_record(request: AnalysisLookupRequest) -> AnalysisRecord | None:
    return lookup_analysis(request)


@app.get("/history/users/{user_id}/analyses", response_model=list[AnalysisRecord])
def get_analysis_records(user_id: str) -> list[AnalysisRecord]:
    return list_analyses(user_id)


@app.post("/history/preparation-sessions", response_model=PreparationSessionRecord)
def create_preparation_session_record(request: PreparationSessionSaveRequest) -> PreparationSessionRecord:
    return save_preparation_session(request)


@app.get("/history/users/{user_id}/preparation-sessions", response_model=list[PreparationSessionRecord])
def get_preparation_session_records(user_id: str) -> list[PreparationSessionRecord]:
    return list_preparation_sessions(user_id)


@app.get("/ai/preparation/memory/{user_id}", response_model=PrepMemoryResponse)
def get_preparation_memory(user_id: str) -> PrepMemoryResponse:
    return build_prep_memory(list_analyses(user_id), list_preparation_sessions(user_id))


@app.get("/history/users/{user_id}/preparation-sessions/{session_id}", response_model=PreparationSessionRecord)
def get_preparation_session_record(user_id: str, session_id: str) -> PreparationSessionRecord:
    return get_preparation_session(user_id, session_id)


@app.patch("/history/preparation-sessions/{session_id}/progress", response_model=PreparationSessionRecord)
def update_preparation_progress_record(session_id: str, request: PreparationSessionProgressUpdateRequest) -> PreparationSessionRecord:
    return update_preparation_session_progress(session_id, request)


@app.post("/history/job-opportunities", response_model=JobOpportunityRecord)
def create_job_opportunity_record(request: JobOpportunitySaveRequest) -> JobOpportunityRecord:
    return save_job_opportunity(request)


@app.get("/history/users/{user_id}/job-opportunities", response_model=list[JobOpportunityRecord])
def get_user_job_opportunities(user_id: str) -> list[JobOpportunityRecord]:
    return list_job_opportunities_for_user(user_id)


@app.get("/history/anonymous-sessions/{anonymous_session_id}/job-opportunities", response_model=list[JobOpportunityRecord])
def get_anonymous_job_opportunities(anonymous_session_id: str) -> list[JobOpportunityRecord]:
    return list_job_opportunities_for_anonymous_session(anonymous_session_id)


@app.patch("/history/job-opportunities/{job_opportunity_id}/status", response_model=JobOpportunityRecord)
def update_job_opportunity_status_record(
    job_opportunity_id: str,
    request: JobOpportunityStatusUpdateRequest,
) -> JobOpportunityRecord:
    return update_job_opportunity_status(job_opportunity_id, request)


def _default_extension_candidate_context(request: ExtensionMatchRequest) -> CandidateContext:
    inferred_stack = _infer_stack_from_text(request.job.description)
    return CandidateContext(
        targetRole=request.job.title,
        experienceYears=0,
        currentStack=inferred_stack or ["general software engineering"],
        targetMarket="Browser extension job matching",
        currentLocation=request.job.location,
        preferredLocations=[request.job.location] if request.job.location else [],
        relocationOpen=False,
    )


def _infer_stack_from_text(text: str) -> list[str]:
    known_terms = [
        ".NET",
        "AI",
        "Angular",
        "AWS",
        "Azure",
        "Django",
        "Docker",
        "FastAPI",
        "GCP",
        "Java",
        "JavaScript",
        "Kubernetes",
        "Node",
        "PostgreSQL",
        "Python",
        "React",
        "SQL",
        "Spring",
        "TypeScript",
    ]
    lowered = text.lower()
    return [term for term in known_terms if term.lower() in lowered][:12]


def _extension_resume_option(resume: ResumeRecord) -> ExtensionResumeOption:
    structured = resume.structuredResume
    profile = structured.profile if structured else None
    summary_parts = [
        profile.name if profile and profile.name else None,
        f"{len(structured.experience)} exp" if structured else None,
        f"{len(structured.projects)} projects" if structured else None,
        f"{len(structured.skills)} skills" if structured else None,
    ]
    summary = " | ".join(part for part in summary_parts if part) or resume.rawText[:120]
    return ExtensionResumeOption(
        id=resume.id,
        title=resume.title,
        updatedAt=resume.updatedAt,
        summary=summary,
        isStructured=bool(structured),
    )


def _infer_extension_title(page_title: str | None, text: str) -> str | None:
    if page_title:
        return page_title.split("|")[0].split("-")[0].strip()[:180] or None
    for line in text.splitlines()[:8]:
        if any(token in line.lower() for token in ["developer", "engineer", "analyst", "architect"]):
            return line.strip()[:180]
    return None


def _infer_extension_company(page_title: str | None, text: str) -> str | None:
    if page_title and " at " in page_title.lower():
        return page_title.lower().split(" at ", 1)[1].split("|")[0].strip().title()[:180]
    company_match = re.search(r"(?i)\b(?:company|organization)\s*:\s*([^.\n|;]+)", text)
    if company_match:
        company = company_match.group(1).strip(" ,:-")
        if company:
            return company[:180]
    for line in text.splitlines()[:12]:
        lowered = line.lower()
        if lowered.startswith("company") or lowered.startswith("organization"):
            return line.split(":", 1)[-1].strip()[:180]
    return None


def _infer_extension_location(text: str) -> str | None:
    location_match = re.search(r"(?i)\blocation\s*:\s*([^.\n|;]+)", text)
    if location_match:
        location = location_match.group(1).strip(" ,:-")
        if location:
            return location[:180]
    for line in text.splitlines()[:20]:
        lowered = line.lower()
        if "location" in lowered:
            return line.split(":", 1)[-1].strip()[:180]
    for city in ["Mumbai", "Pune", "Bangalore", "Bengaluru", "Hyderabad", "Delhi", "Noida", "Gurgaon", "Remote"]:
        if city.lower() in text.lower():
            return city
    return None


def _clean_optional(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None
