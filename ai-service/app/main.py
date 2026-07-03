import json
import logging
import re
import time
import hmac
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi import File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db import initialize_database
from app.core.config import get_settings
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
from app.models.auth import UserLoginRequest, UserPasswordRegisterRequest, UserSessionResponse
from app.models.evaluation import (
    MatchFeedbackDataset,
    MatchFeedbackImportRequest,
    MatchFeedbackRecord,
    MatchFeedbackSaveRequest,
    MatchFeedbackSummary,
)
from app.models.extension import (
    ExtensionBootstrapRequest,
    ExtensionBootstrapResponse,
    ExtensionDiagnosticsRequest,
    ExtensionDiagnosticsResponse,
    ExtensionJobDraft,
    ExtensionMatchRequest,
    ExtensionMatchResponse,
    ExtensionPageParseRequest,
    ExtensionResumeOption,
    ExtensionSessionClaimRequest,
    ExtensionSessionClaimResponse,
    ExtensionUserSession,
    ExtensionValidationRecord,
    ExtensionValidationSaveRequest,
)
from app.models.history import (
    AnonymousSessionCreateRequest,
    AnonymousSessionRecord,
    AnalysisLookupRequest,
    AnalysisRecord,
    AnalysisSaveRequest,
    BillingWebhookSubscriptionEvent,
    ComparisonRunDeleteRequest,
    ComparisonRunRecord,
    ComparisonRunSaveRequest,
    ComparisonRunUpdateRequest,
    JobOpportunityRecord,
    JobOpportunitySaveRequest,
    JobOpportunityStatusUpdateRequest,
    JobDescriptionRecord,
    JobDescriptionSaveRequest,
    OptionalArtifactUsageUpdateRequest,
    PreparationSessionRecord,
    PreparationSessionProgressUpdateRequest,
    PreparationSessionSaveRequest,
    ResumeRecord,
    ResumeSaveRequest,
    UserBillingUpdateRequest,
    UserCreateRequest,
    UserRecord,
    UserSubscriptionTierUpdateRequest,
    WorkspaceSummary,
)
from app.models.jd_parse import JdParseRequest, JdParseResponse
from app.models.prep_memory import PrepMemoryResponse
from app.models.resume_extract import ResumeExtractResponse
from app.models.resume_normalize import ResumeNormalizeRequest, ResumeNormalizeResponse
from app.models.scoring_config import (
    ScoringCalibrationAuditRecord,
    ScoringCalibrationConfig,
    ScoringCalibrationListResponse,
    ScoringCalibrationRecommendation,
    ScoringCalibrationRestoreRequest,
    ScoringCalibrationUpdateRequest,
)
from app.models.system import ProductionReadinessResponse, ReadinessCheck, SystemDiagnostics
from app.services.analyzer_service import analyze_resume_jd, match_resume_jd
from app.services.history_store import (
    create_or_touch_anonymous_session,
    claim_anonymous_session,
    authenticate_user_password,
    create_user_session,
    create_or_update_user,
    create_or_update_user_password,
    delete_comparison_run,
    get_resume,
    get_preparation_session,
    get_workspace_summary,
    list_comparison_runs,
    list_users,
    resolve_user_session,
    list_analyses,
    list_job_descriptions,
    list_job_opportunities_for_anonymous_session,
    list_job_opportunities_for_user,
    list_preparation_sessions,
    list_resumes,
    save_analysis,
    save_comparison_run,
    search_analyses,
    update_analysis_optional_artifact,
    update_comparison_run,
    save_job_description,
    save_job_opportunity,
    save_preparation_session,
    lookup_analysis,
    save_resume,
    update_preparation_session_progress,
    update_job_opportunity_status,
    update_job_opportunity_optional_artifact,
    save_extension_validation,
    list_extension_validations,
    save_match_feedback,
    get_match_feedback_summary,
    export_match_feedback_dataset,
    import_match_feedback_dataset,
    update_user_billing,
    update_user_subscription_tier,
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
from app.services.scoring_config_service import (
    list_scoring_calibration_audit,
    list_scoring_calibrations,
    recommend_scoring_calibration,
    restore_scoring_calibration,
    save_scoring_calibration,
)

settings = get_settings()
logger = logging.getLogger("career-agent-os")
logger.setLevel(getattr(logging, settings.log_level))
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.propagate = False

app = FastAPI(title="Career Agent OS AI Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.exception(
            json.dumps(
                {
                    "event": "request_error",
                    "requestId": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "durationMs": duration_ms,
                }
            )
        )
        response = JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "requestId": request_id,
            },
        )

    response.headers["X-Request-ID"] = request_id
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        json.dumps(
            {
                "event": "request_completed",
                "requestId": request_id,
                "method": request.method,
                "path": request.url.path,
                "statusCode": response.status_code,
                "durationMs": duration_ms,
            }
        )
    )
    return response


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    initialize_database()
    return {
        "status": "ready",
        "environment": settings.environment,
        "corsOrigins": settings.cors_allow_origins,
    }


@app.get("/diagnostics/system", response_model=SystemDiagnostics)
def system_diagnostics(userId: str | None = None, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> SystemDiagnostics:
    warnings: list[str] = []
    database_ok = True
    workspace_counts: dict[str, int] = {}
    try:
        initialize_database()
        if userId:
            _authorize_user(userId, session_token)
            summary = get_workspace_summary(userId)
            workspace_counts = {
                "resumes": summary.resumeCount,
                "jobDescriptions": summary.jobDescriptionCount,
                "analyses": summary.analysisCount,
                "preparationSessions": summary.preparationSessionCount,
                "jobOpportunities": summary.jobOpportunityCount,
            }
    except Exception as exc:
        database_ok = False
        warnings.append(f"Database check failed: {exc}")

    llm_key_configured = _llm_key_configured(settings)
    if settings.llm_mode == "live" and not llm_key_configured:
        warnings.append("Live LLM mode is enabled but no API key is configured for the selected provider.")
    if settings.embedding_provider != "local" and not settings.embedding_fallback_local:
        warnings.append("Remote embeddings are selected without local fallback.")

    return SystemDiagnostics(
        status="ready" if database_ok else "degraded",
        environment=settings.environment,
        databaseOk=database_ok,
        llmMode=settings.llm_mode,
        llmProvider=settings.llm_provider,
        llmModel=settings.llm_model,
        llmKeyConfigured=llm_key_configured,
        embeddingProvider=settings.embedding_provider,
        embeddingModel=settings.embedding_model or "auto",
        embeddingFallbackLocal=settings.embedding_fallback_local,
        jdParserMode=settings.jd_parser_mode,
        corsOrigins=[origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()],
        workspaceCounts=workspace_counts,
        warnings=warnings,
    )


@app.get("/diagnostics/production-readiness", response_model=ProductionReadinessResponse)
def production_readiness(userId: str | None = None, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> ProductionReadinessResponse:
    database_ok = True
    database_error = ""
    try:
        initialize_database()
    except Exception as exc:
        database_ok = False
        database_error = str(exc)
    if userId:
        _authorize_user(userId, session_token)

    checks = _build_production_readiness_checks(database_ok, database_error)
    warnings = [check.detail for check in checks if check.status in {"warn", "fail"}]
    return ProductionReadinessResponse(
        environment=settings.environment,
        readyForProduction=all(check.status != "fail" for check in checks),
        checks=checks,
        warnings=warnings,
    )


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
    user_session = _extension_user_session_from_token(request.sessionToken) if request.sessionToken else None
    user_id = user_session.userId if user_session else request.userId
    resumes = list_extension_resumes(user_id) if user_id else []
    return ExtensionBootstrapResponse(
        anonymousSession=anonymous_session,
        userSession=user_session,
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


@app.post("/extension/diagnostics", response_model=ExtensionDiagnosticsResponse)
def extension_diagnostics(request: ExtensionDiagnosticsRequest) -> ExtensionDiagnosticsResponse:
    checks = ["Backend API reachable", "PostgreSQL schema initialized"]
    warnings = []
    user_id = request.userId
    session_ok = False
    if request.sessionToken:
        try:
            user_session = _extension_user_session_from_token(request.sessionToken)
            user_id = user_session.userId
            session_ok = True
            checks.append("Extension session token resolved")
        except HTTPException:
            warnings.append("Session token is invalid or expired. Reconnect from the extension.")
    elif user_id:
        checks.append("Development user id provided")
    else:
        warnings.append("No user id or session token provided. Extension can parse pages but cannot load saved resumes.")

    resume_count = 0
    if user_id:
        try:
            resume_count = len(list_extension_resumes(user_id))
            if resume_count:
                checks.append("Saved resumes available")
            else:
                warnings.append("No saved resumes found. Save a resume from the web app before matching from the extension.")
        except HTTPException:
            warnings.append("User was not found. Create or connect the user before extension matching.")
            user_id = None

    if request.anonymousSessionId:
        create_or_touch_anonymous_session(AnonymousSessionCreateRequest(anonymousSessionId=request.anonymousSessionId))
        checks.append("Anonymous session available for pre-login tracking")

    return ExtensionDiagnosticsResponse(
        backendOk=True,
        sessionOk=session_ok,
        userId=user_id,
        resumeCount=resume_count,
        canMatchSavedResume=bool(user_id and resume_count),
        manualPasteRequired=not bool(resume_count),
        checks=checks,
        warnings=warnings,
    )


@app.post("/extension/session/claim", response_model=ExtensionSessionClaimResponse)
def claim_extension_session(request: ExtensionSessionClaimRequest) -> ExtensionSessionClaimResponse:
    create_or_touch_anonymous_session(AnonymousSessionCreateRequest(anonymousSessionId=request.anonymousSessionId))
    anonymous_session, migrated_count = claim_anonymous_session(
        request.anonymousSessionId,
        request.userId,
        request.displayName,
        request.email,
    )
    token = create_user_session(request.userId, source="extension")
    return ExtensionSessionClaimResponse(
        anonymousSession=anonymous_session,
        userSession=ExtensionUserSession(
            userId=request.userId,
            displayName=request.displayName or request.userId,
            sessionToken=token,
        ),
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

    session_user = resolve_user_session(request.sessionToken) if request.sessionToken else None
    user_id = session_user.id if session_user else request.userId
    resume_text = request.resumeText
    if request.resumeId:
        if not user_id:
            raise HTTPException(status_code=400, detail="userId or sessionToken is required when resumeId is provided")
        resume = get_resume(user_id, request.resumeId)
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
    analysis_record = None
    if user_id:
        analysis_record = save_analysis(
            AnalysisSaveRequest(
                userId=user_id,
                title=f"{request.job.title} - {analysis.technicalMatchScore}%",
                resumeId=request.resumeId,
                request=analysis_request,
                response=analysis,
            )
        )
    opportunity = None
    if request.saveOpportunity:
        opportunity = save_job_opportunity(
            JobOpportunitySaveRequest(
                userId=user_id,
                anonymousSessionId=request.anonymousSessionId,
                resumeId=request.resumeId,
                analysisId=analysis_record.id if analysis_record else None,
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


@app.post("/auth/session/claim", response_model=UserSessionResponse)
def claim_user_session(request: UserCreateRequest) -> UserSessionResponse:
    user = create_or_update_user(request)
    token = create_user_session(user.id, source="web")
    return UserSessionResponse(user=user, sessionToken=token)


@app.post("/auth/register", response_model=UserSessionResponse)
def register_user_password(request: UserPasswordRegisterRequest) -> UserSessionResponse:
    user = create_or_update_user_password(
        request.userId,
        request.displayName,
        request.email,
        request.password,
        request.role,
        request.subscriptionTier,
    )
    token = create_user_session(user.id, source="password")
    return UserSessionResponse(user=user, sessionToken=token)


@app.post("/auth/login", response_model=UserSessionResponse)
def login_user_password(request: UserLoginRequest) -> UserSessionResponse:
    user = authenticate_user_password(request.userIdOrEmail, request.password)
    token = create_user_session(user.id, source="password")
    return UserSessionResponse(user=user, sessionToken=token)


@app.patch("/auth/users/{user_id}/subscription-tier", response_model=UserRecord)
def update_subscription_tier(user_id: str, request: UserSubscriptionTierUpdateRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> UserRecord:
    _authorize_user(user_id, session_token)
    return update_user_subscription_tier(user_id, request)


@app.patch("/admin/users/{user_id}/billing", response_model=UserRecord)
def update_user_billing_metadata(user_id: str, request: UserBillingUpdateRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> UserRecord:
    _authorize_admin(session_token)
    return update_user_billing(user_id, request)


@app.post("/billing/webhooks/subscription", response_model=UserRecord)
def ingest_subscription_webhook(
    request: BillingWebhookSubscriptionEvent,
    billing_webhook_secret: str | None = Header(default=None, alias="X-Billing-Webhook-Secret"),
) -> UserRecord:
    _authorize_billing_webhook(billing_webhook_secret)
    user_id, billing_update = _billing_update_from_webhook(request)
    return update_user_billing(user_id, billing_update)


@app.post("/auth/anonymous", response_model=AnonymousSessionRecord)
def create_anonymous_session(request: AnonymousSessionCreateRequest | None = None) -> AnonymousSessionRecord:
    return create_or_touch_anonymous_session(request or AnonymousSessionCreateRequest())


@app.get("/admin/users", response_model=list[UserRecord])
def get_admin_users(session_token: str | None = Header(default=None, alias="X-Session-Token")) -> list[UserRecord]:
    _authorize_admin(session_token)
    return list_users()


@app.get("/admin/analyses", response_model=list[AnalysisRecord])
def search_admin_analyses(
    query: str | None = None,
    userId: str | None = None,
    limit: int = 50,
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
) -> list[AnalysisRecord]:
    _authorize_admin(session_token)
    return search_analyses(query=query, user_id=userId, limit=limit)


@app.get("/history/users/{user_id}/workspace", response_model=WorkspaceSummary)
def workspace_summary(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> WorkspaceSummary:
    _authorize_user(user_id, session_token)
    return get_workspace_summary(user_id)


@app.post("/history/resumes", response_model=ResumeRecord)
def create_resume_record(request: ResumeSaveRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> ResumeRecord:
    _authorize_user(request.userId, session_token)
    return save_resume(request)


@app.get("/history/users/{user_id}/resumes", response_model=list[ResumeRecord])
def get_resume_records(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> list[ResumeRecord]:
    _authorize_user(user_id, session_token)
    return list_resumes(user_id)


@app.post("/history/job-descriptions", response_model=JobDescriptionRecord)
def create_job_description_record(request: JobDescriptionSaveRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> JobDescriptionRecord:
    _authorize_user(request.userId, session_token)
    return save_job_description(request)


@app.get("/history/users/{user_id}/job-descriptions", response_model=list[JobDescriptionRecord])
def get_job_description_records(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> list[JobDescriptionRecord]:
    _authorize_user(user_id, session_token)
    return list_job_descriptions(user_id)


@app.post("/history/analyses", response_model=AnalysisRecord)
def create_analysis_record(request: AnalysisSaveRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> AnalysisRecord:
    _authorize_user(request.userId, session_token)
    return save_analysis(request)


@app.post("/history/analyses/lookup", response_model=AnalysisRecord | None)
def lookup_analysis_record(request: AnalysisLookupRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> AnalysisRecord | None:
    _authorize_user(request.userId, session_token)
    return lookup_analysis(request)


@app.get("/history/users/{user_id}/analyses", response_model=list[AnalysisRecord])
def get_analysis_records(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> list[AnalysisRecord]:
    _authorize_user(user_id, session_token)
    return list_analyses(user_id)


@app.post("/history/comparisons", response_model=ComparisonRunRecord)
def create_comparison_run_record(request: ComparisonRunSaveRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> ComparisonRunRecord:
    _authorize_user(request.userId, session_token)
    return save_comparison_run(request)


@app.get("/history/users/{user_id}/comparisons", response_model=list[ComparisonRunRecord])
def get_comparison_run_records(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> list[ComparisonRunRecord]:
    _authorize_user(user_id, session_token)
    return list_comparison_runs(user_id)


@app.patch("/history/comparisons/{comparison_id}", response_model=ComparisonRunRecord)
def update_comparison_run_record(comparison_id: str, request: ComparisonRunUpdateRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> ComparisonRunRecord:
    _authorize_user(request.userId, session_token)
    return update_comparison_run(comparison_id, request)


@app.delete("/history/comparisons/{comparison_id}")
def delete_comparison_run_record(comparison_id: str, request: ComparisonRunDeleteRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> dict[str, str]:
    _authorize_user(request.userId, session_token)
    return delete_comparison_run(comparison_id, request)


@app.patch("/history/analyses/{analysis_id}/optional-artifacts", response_model=AnalysisRecord)
def update_analysis_optional_artifact_record(analysis_id: str, request: OptionalArtifactUsageUpdateRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> AnalysisRecord:
    _authorize_user(request.userId, session_token)
    return update_analysis_optional_artifact(analysis_id, request)


@app.post("/history/preparation-sessions", response_model=PreparationSessionRecord)
def create_preparation_session_record(request: PreparationSessionSaveRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> PreparationSessionRecord:
    _authorize_user(request.userId, session_token)
    return save_preparation_session(request)


@app.get("/history/users/{user_id}/preparation-sessions", response_model=list[PreparationSessionRecord])
def get_preparation_session_records(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> list[PreparationSessionRecord]:
    _authorize_user(user_id, session_token)
    return list_preparation_sessions(user_id)


@app.get("/ai/preparation/memory/{user_id}", response_model=PrepMemoryResponse)
def get_preparation_memory(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> PrepMemoryResponse:
    _authorize_user(user_id, session_token)
    return build_prep_memory(list_analyses(user_id), list_preparation_sessions(user_id))


@app.get("/history/users/{user_id}/preparation-sessions/{session_id}", response_model=PreparationSessionRecord)
def get_preparation_session_record(user_id: str, session_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> PreparationSessionRecord:
    _authorize_user(user_id, session_token)
    return get_preparation_session(user_id, session_id)


@app.patch("/history/preparation-sessions/{session_id}/progress", response_model=PreparationSessionRecord)
def update_preparation_progress_record(session_id: str, request: PreparationSessionProgressUpdateRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> PreparationSessionRecord:
    _authorize_user(request.userId, session_token)
    return update_preparation_session_progress(session_id, request)


@app.post("/history/job-opportunities", response_model=JobOpportunityRecord)
def create_job_opportunity_record(request: JobOpportunitySaveRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> JobOpportunityRecord:
    if request.userId:
        _authorize_user(request.userId, session_token)
    return save_job_opportunity(request)


@app.get("/history/users/{user_id}/job-opportunities", response_model=list[JobOpportunityRecord])
def get_user_job_opportunities(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> list[JobOpportunityRecord]:
    _authorize_user(user_id, session_token)
    return list_job_opportunities_for_user(user_id)


@app.get("/history/anonymous-sessions/{anonymous_session_id}/job-opportunities", response_model=list[JobOpportunityRecord])
def get_anonymous_job_opportunities(anonymous_session_id: str) -> list[JobOpportunityRecord]:
    return list_job_opportunities_for_anonymous_session(anonymous_session_id)


@app.patch("/history/job-opportunities/{job_opportunity_id}/status", response_model=JobOpportunityRecord)
def update_job_opportunity_status_record(
    job_opportunity_id: str,
    request: JobOpportunityStatusUpdateRequest,
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
) -> JobOpportunityRecord:
    if request.userId:
        _authorize_user(request.userId, session_token)
    elif settings.require_user_auth:
        raise HTTPException(status_code=401, detail="userId is required when auth is enabled")
    return update_job_opportunity_status(job_opportunity_id, request)


@app.patch("/history/job-opportunities/{job_opportunity_id}/optional-artifacts", response_model=JobOpportunityRecord)
def update_job_opportunity_optional_artifact_record(
    job_opportunity_id: str,
    request: OptionalArtifactUsageUpdateRequest,
    session_token: str | None = Header(default=None, alias="X-Session-Token"),
) -> JobOpportunityRecord:
    _authorize_user(request.userId, session_token)
    return update_job_opportunity_optional_artifact(job_opportunity_id, request)


@app.post("/extension/validation-results", response_model=ExtensionValidationRecord)
def create_extension_validation_result(request: ExtensionValidationSaveRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> ExtensionValidationRecord:
    _authorize_user(request.userId, session_token)
    return save_extension_validation(request)


@app.get("/extension/users/{user_id}/validation-results", response_model=list[ExtensionValidationRecord])
def get_extension_validation_results(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> list[ExtensionValidationRecord]:
    _authorize_user(user_id, session_token)
    return list_extension_validations(user_id)


@app.post("/evaluation/match-feedback", response_model=MatchFeedbackRecord)
def create_match_feedback(request: MatchFeedbackSaveRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> MatchFeedbackRecord:
    _authorize_user(request.userId, session_token)
    return save_match_feedback(request)


@app.get("/evaluation/users/{user_id}/summary", response_model=MatchFeedbackSummary)
def get_evaluation_summary(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> MatchFeedbackSummary:
    _authorize_user(user_id, session_token)
    return get_match_feedback_summary(user_id)


@app.get("/evaluation/users/{user_id}/dataset", response_model=MatchFeedbackDataset)
def export_evaluation_dataset(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> MatchFeedbackDataset:
    _authorize_user(user_id, session_token)
    return export_match_feedback_dataset(user_id)


@app.post("/evaluation/dataset/import", response_model=MatchFeedbackDataset)
def import_evaluation_dataset(request: MatchFeedbackImportRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> MatchFeedbackDataset:
    _authorize_user(request.userId, session_token)
    return import_match_feedback_dataset(request)


@app.get("/settings/users/{user_id}/scoring-calibration", response_model=ScoringCalibrationListResponse)
def get_scoring_calibration_settings(user_id: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> ScoringCalibrationListResponse:
    _authorize_user(user_id, session_token)
    _authorize_admin(session_token)
    return list_scoring_calibrations(user_id)


@app.put("/settings/scoring-calibration", response_model=ScoringCalibrationConfig)
def update_scoring_calibration_settings(request: ScoringCalibrationUpdateRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> ScoringCalibrationConfig:
    _authorize_user(request.userId, session_token)
    _authorize_admin(session_token)
    return save_scoring_calibration(request)


@app.get("/settings/users/{user_id}/scoring-calibration/{role_family}/recommendation", response_model=ScoringCalibrationRecommendation)
def get_scoring_calibration_recommendation(user_id: str, role_family: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> ScoringCalibrationRecommendation:
    _authorize_user(user_id, session_token)
    _authorize_admin(session_token)
    return recommend_scoring_calibration(user_id, role_family)


@app.get("/settings/users/{user_id}/scoring-calibration-recommendation", response_model=ScoringCalibrationRecommendation)
def get_scoring_calibration_recommendation_by_query(user_id: str, roleFamily: str, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> ScoringCalibrationRecommendation:
    _authorize_user(user_id, session_token)
    _authorize_admin(session_token)
    return recommend_scoring_calibration(user_id, roleFamily)


@app.get("/settings/users/{user_id}/scoring-calibration-audit", response_model=list[ScoringCalibrationAuditRecord])
def get_scoring_calibration_audit(user_id: str, roleFamily: str | None = None, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> list[ScoringCalibrationAuditRecord]:
    _authorize_user(user_id, session_token)
    _authorize_admin(session_token)
    return list_scoring_calibration_audit(user_id, roleFamily)


@app.post("/settings/scoring-calibration/restore", response_model=ScoringCalibrationConfig)
def restore_scoring_calibration_settings(request: ScoringCalibrationRestoreRequest, session_token: str | None = Header(default=None, alias="X-Session-Token")) -> ScoringCalibrationConfig:
    _authorize_user(request.userId, session_token)
    _authorize_admin(session_token)
    try:
        return restore_scoring_calibration(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


def _build_production_readiness_checks(database_ok: bool, database_error: str = "") -> list[ReadinessCheck]:
    is_production = settings.environment == "production"
    cors_origins = [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]
    has_local_cors = any(_is_local_origin(origin) for origin in cors_origins)
    has_wildcard_cors = "*" in cors_origins
    llm_key_configured = _llm_key_configured(settings)
    embedding_key_configured = _embedding_key_configured(settings)
    admin_ids = [item.strip() for item in settings.admin_user_ids.split(",") if item.strip()]

    checks: list[ReadinessCheck] = [
        ReadinessCheck(
            key="database",
            label="Database connection",
            status="pass" if database_ok else "fail",
            detail="PostgreSQL is reachable and schema initialization completed." if database_ok else f"Database check failed: {database_error}",
        ),
        ReadinessCheck(
            key="environment",
            label="Environment mode",
            status="pass" if is_production else "warn",
            detail="Application is running in production mode." if is_production else f"Current mode is {settings.environment}; switch ENVIRONMENT=production before public deployment.",
        ),
        ReadinessCheck(
            key="auth",
            label="User auth enforcement",
            status="pass" if settings.require_user_auth else ("fail" if is_production else "warn"),
            detail="User-scoped APIs require X-Session-Token." if settings.require_user_auth else "REQUIRE_USER_AUTH is disabled; enable it before multi-user deployment.",
        ),
        ReadinessCheck(
            key="adminBootstrap",
            label="Admin bootstrap",
            status="pass" if admin_ids else ("fail" if is_production else "warn"),
            detail=f"{len(admin_ids)} admin user id(s) configured." if admin_ids else "ADMIN_USER_IDS is empty; configure at least one admin before deployment.",
        ),
        ReadinessCheck(
            key="billingWebhook",
            label="Billing webhook secret",
            status="pass" if settings.billing_webhook_secret else ("fail" if is_production else "warn"),
            detail="Billing webhook secret is configured." if settings.billing_webhook_secret else "BILLING_WEBHOOK_SECRET is empty; configure it before enabling paid subscription webhooks.",
        ),
        ReadinessCheck(
            key="cors",
            label="CORS origins",
            status="fail" if is_production and (not cors_origins or has_local_cors or has_wildcard_cors) else ("warn" if has_wildcard_cors else "pass"),
            detail=_cors_readiness_detail(cors_origins, is_production, has_local_cors, has_wildcard_cors),
        ),
        ReadinessCheck(
            key="llm",
            label="LLM configuration",
            status="fail" if settings.llm_mode == "live" and not llm_key_configured else ("warn" if is_production and settings.llm_mode != "live" else "pass"),
            detail=_llm_readiness_detail(llm_key_configured, is_production),
        ),
        ReadinessCheck(
            key="embeddings",
            label="Embedding configuration",
            status="pass" if settings.embedding_provider == "local" or embedding_key_configured or settings.embedding_fallback_local else ("fail" if is_production else "warn"),
            detail=_embedding_readiness_detail(embedding_key_configured),
        ),
        ReadinessCheck(
            key="jdParser",
            label="JD parser mode",
            status="warn" if settings.jd_parser_mode == "llm" and (settings.llm_mode != "live" or not llm_key_configured) else "pass",
            detail=_jd_parser_readiness_detail(llm_key_configured),
        ),
        ReadinessCheck(
            key="logging",
            label="Logging level",
            status="warn" if is_production and settings.log_level == "DEBUG" else "pass",
            detail="DEBUG logging is enabled; use INFO or higher for production." if is_production and settings.log_level == "DEBUG" else f"LOG_LEVEL is {settings.log_level}.",
        ),
    ]
    return checks


def _cors_readiness_detail(cors_origins: list[str], is_production: bool, has_local_cors: bool, has_wildcard_cors: bool) -> str:
    if not cors_origins:
        return "No CORS origins are configured."
    if is_production and has_wildcard_cors:
        return "Wildcard CORS is unsafe for production; use the deployed frontend and extension origins only."
    if is_production and has_local_cors:
        return "Production CORS still includes localhost/127.0.0.1; replace with deployed frontend and extension origins."
    return f"{len(cors_origins)} origin(s) configured."


def _llm_readiness_detail(llm_key_configured: bool, is_production: bool) -> str:
    if settings.llm_mode == "live" and llm_key_configured:
        return f"Live LLM is configured for {settings.llm_provider} / {settings.llm_model}."
    if settings.llm_mode == "live":
        return f"Live LLM mode is selected for {settings.llm_provider}, but the provider key is missing."
    if is_production:
        return "LLM mode is mock; paid optional artifacts will return deterministic placeholders."
    return "Mock LLM mode is active, which is fine for local development."


def _embedding_readiness_detail(embedding_key_configured: bool) -> str:
    if settings.embedding_provider == "local":
        return "Local embeddings are active; no remote key is required."
    if embedding_key_configured:
        return f"{settings.embedding_provider} embeddings have a provider key configured."
    if settings.embedding_fallback_local:
        return f"{settings.embedding_provider} embeddings can fall back to local embeddings when the remote key is unavailable."
    return f"{settings.embedding_provider} embeddings are selected without a provider key or local fallback."


def _jd_parser_readiness_detail(llm_key_configured: bool) -> str:
    if settings.jd_parser_mode == "llm" and (settings.llm_mode != "live" or not llm_key_configured):
        return "JD parser is set to LLM mode, but live LLM access is not fully configured."
    return f"JD parser mode is {settings.jd_parser_mode}."


def _embedding_key_configured(current_settings) -> bool:
    if current_settings.embedding_provider == "openai":
        return bool(current_settings.openai_api_key or current_settings.llm_api_key)
    if current_settings.embedding_provider == "gemini":
        return bool(current_settings.gemini_api_key or current_settings.google_api_key or current_settings.llm_api_key)
    if current_settings.embedding_provider == "auto":
        return bool(
            current_settings.openai_api_key
            or current_settings.gemini_api_key
            or current_settings.google_api_key
            or current_settings.llm_api_key
        )
    return True


def _is_local_origin(origin: str) -> bool:
    lowered = origin.lower()
    return "localhost" in lowered or "127.0.0.1" in lowered or "[::1]" in lowered


def _llm_key_configured(current_settings) -> bool:
    if current_settings.llm_provider == "groq":
        return bool(current_settings.groq_api_key or current_settings.llm_api_key)
    if current_settings.llm_provider == "openai":
        return bool(current_settings.openai_api_key or current_settings.llm_api_key)
    if current_settings.llm_provider == "gemini":
        return bool(current_settings.gemini_api_key or current_settings.google_api_key or current_settings.llm_api_key)
    return bool(current_settings.llm_api_key)


def _billing_update_from_webhook(event: BillingWebhookSubscriptionEvent) -> tuple[str, UserBillingUpdateRequest]:
    payload = event.providerPayload or {}
    provider_values: dict[str, Any] = {}
    if event.provider == "stripe":
        provider_values = _stripe_subscription_values(payload)
    elif event.provider == "razorpay":
        provider_values = _razorpay_subscription_values(payload)
    elif event.provider == "paddle":
        provider_values = _paddle_subscription_values(payload)

    user_id = event.userId or _first_text(provider_values.get("userId"))
    if not user_id:
        raise HTTPException(status_code=400, detail="Billing webhook must include userId directly or in provider metadata")

    status = event.subscriptionStatus
    if event.subscriptionStatus == "inactive" and provider_values.get("subscriptionStatus"):
        status = _coerce_subscription_status(str(provider_values["subscriptionStatus"]), event.provider)

    return user_id, UserBillingUpdateRequest(
        subscriptionTier=event.subscriptionTier,
        subscriptionStatus=status,
        subscriptionPlanId=event.subscriptionPlanId or _first_text(provider_values.get("subscriptionPlanId")),
        billingProviderCustomerId=event.billingProviderCustomerId or _first_text(provider_values.get("billingProviderCustomerId")),
        billingProviderSubscriptionId=event.billingProviderSubscriptionId or _first_text(provider_values.get("billingProviderSubscriptionId")),
        billingPeriodEnd=event.billingPeriodEnd or _billing_period_end_text(provider_values.get("billingPeriodEnd")),
    )


def _stripe_subscription_values(payload: dict[str, Any]) -> dict[str, Any]:
    subscription = _nested(payload, "data", "object") or payload
    metadata = subscription.get("metadata") if isinstance(subscription.get("metadata"), dict) else {}
    first_item = _first_list_item(_nested(subscription, "items", "data"))
    return {
        "userId": _metadata_user_id(metadata),
        "subscriptionStatus": subscription.get("status"),
        "subscriptionPlanId": _nested(subscription, "plan", "id") or _nested(first_item, "price", "id"),
        "billingProviderCustomerId": subscription.get("customer"),
        "billingProviderSubscriptionId": subscription.get("id"),
        "billingPeriodEnd": subscription.get("current_period_end"),
    }


def _razorpay_subscription_values(payload: dict[str, Any]) -> dict[str, Any]:
    subscription = _nested(payload, "payload", "subscription", "entity") or payload
    notes = subscription.get("notes") if isinstance(subscription.get("notes"), dict) else {}
    return {
        "userId": _metadata_user_id(notes),
        "subscriptionStatus": subscription.get("status"),
        "subscriptionPlanId": subscription.get("plan_id"),
        "billingProviderCustomerId": subscription.get("customer_id"),
        "billingProviderSubscriptionId": subscription.get("id"),
        "billingPeriodEnd": subscription.get("current_end") or subscription.get("end_at"),
    }


def _paddle_subscription_values(payload: dict[str, Any]) -> dict[str, Any]:
    subscription = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    custom_data = subscription.get("custom_data") if isinstance(subscription.get("custom_data"), dict) else {}
    first_item = _first_list_item(subscription.get("items"))
    return {
        "userId": _metadata_user_id(custom_data),
        "subscriptionStatus": subscription.get("status"),
        "subscriptionPlanId": _nested(first_item, "price", "id"),
        "billingProviderCustomerId": subscription.get("customer_id"),
        "billingProviderSubscriptionId": subscription.get("id"),
        "billingPeriodEnd": _nested(subscription, "current_billing_period", "ends_at"),
    }


def _coerce_subscription_status(status: str, provider: str) -> str:
    normalized = status.strip().lower()
    if normalized in {"active", "trialing", "past_due", "canceled", "inactive"}:
        return normalized
    if provider == "razorpay":
        if normalized == "authenticated":
            return "active"
        if normalized in {"created", "pending"}:
            return "trialing"
        if normalized == "halted":
            return "past_due"
        if normalized in {"cancelled", "cancelled_by_user"}:
            return "canceled"
    if provider == "stripe" and normalized in {"unpaid", "incomplete"}:
        return "past_due"
    return "inactive"


def _billing_period_end_text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, UTC).isoformat().replace("+00:00", "Z")
    return str(value)


def _metadata_user_id(metadata: dict[str, Any]) -> str | None:
    return _first_text(metadata.get("userId") or metadata.get("user_id") or metadata.get("appUserId") or metadata.get("app_user_id"))


def _nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first_list_item(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def _first_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _authorize_billing_webhook(provided_secret: str | None) -> None:
    expected_secret = settings.billing_webhook_secret.strip()
    if not expected_secret:
        raise HTTPException(status_code=503, detail="Billing webhook secret is not configured")
    if not provided_secret or not hmac.compare_digest(provided_secret, expected_secret):
        raise HTTPException(status_code=401, detail="Invalid billing webhook secret")


def _authorize_user(user_id: str, session_token: str | None) -> None:
    if not settings.require_user_auth:
        return
    if not session_token:
        raise HTTPException(status_code=401, detail="Session token is required")
    user = resolve_user_session(session_token)
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Session token does not match requested user")


def _authorize_admin(session_token: str | None) -> None:
    if not settings.require_user_auth:
        return
    if not session_token:
        raise HTTPException(status_code=401, detail="Session token is required")
    user = resolve_user_session(session_token)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role is required")


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


def _extension_user_session_from_token(token: str) -> ExtensionUserSession:
    user = resolve_user_session(token)
    return ExtensionUserSession(
        userId=user.id,
        displayName=user.displayName,
        sessionToken=token,
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
