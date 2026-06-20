from fastapi import FastAPI
from fastapi import File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.db import initialize_database
from app.models.analysis import (
    AnalyzeRequest,
    AnalysisResponse,
    CrossQuestion,
    InterviewQuestion,
    OptionalArtifactBuildRequest,
    PreparationBuildRequest,
    PreparationIntelligence,
    ResumeImprovement,
)
from app.models.history import (
    AnalysisRecord,
    AnalysisSaveRequest,
    JobDescriptionRecord,
    JobDescriptionSaveRequest,
    PreparationSessionRecord,
    PreparationSessionSaveRequest,
    ResumeRecord,
    ResumeSaveRequest,
    UserCreateRequest,
    UserRecord,
    WorkspaceSummary,
)
from app.models.jd_parse import JdParseRequest, JdParseResponse
from app.models.resume_extract import ResumeExtractResponse
from app.models.resume_normalize import ResumeNormalizeRequest, ResumeNormalizeResponse
from app.services.analyzer_service import analyze_resume_jd, match_resume_jd
from app.services.history_store import (
    create_or_update_user,
    get_workspace_summary,
    list_analyses,
    list_job_descriptions,
    list_preparation_sessions,
    list_resumes,
    save_analysis,
    save_job_description,
    save_preparation_session,
    save_resume,
)
from app.services.jd_parser import parse_jd
from app.services.optional_artifact_service import (
    build_cross_questions,
    build_interview_questions,
    build_resume_improvements,
)
from app.services.preparation_service import build_preparation_intelligence
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


@app.post("/ai/preparation/build", response_model=PreparationIntelligence)
def build_preparation(request: PreparationBuildRequest) -> PreparationIntelligence:
    source_request = request.sourceRequest.model_copy(update={"preparationPlanDays": request.preparationPlanDays})
    return build_preparation_intelligence(
        source_request,
        request.analysis.requirementMatches,
        request.analysis.scoreBreakdown,
    )


@app.post("/ai/resume-improvements/build", response_model=list[ResumeImprovement])
def build_resume_improvement_artifacts(request: OptionalArtifactBuildRequest) -> list[ResumeImprovement]:
    return build_resume_improvements(request.sourceRequest, request.analysis, request.limit)


@app.post("/ai/interview-questions/build", response_model=list[InterviewQuestion])
def build_interview_question_artifacts(request: OptionalArtifactBuildRequest) -> list[InterviewQuestion]:
    return build_interview_questions(request.sourceRequest, request.analysis, request.limit)


@app.post("/ai/cross-questions/build", response_model=list[CrossQuestion])
def build_cross_question_artifacts(request: OptionalArtifactBuildRequest) -> list[CrossQuestion]:
    return build_cross_questions(request.sourceRequest, request.analysis, request.limit)


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


@app.get("/history/users/{user_id}/analyses", response_model=list[AnalysisRecord])
def get_analysis_records(user_id: str) -> list[AnalysisRecord]:
    return list_analyses(user_id)


@app.post("/history/preparation-sessions", response_model=PreparationSessionRecord)
def create_preparation_session_record(request: PreparationSessionSaveRequest) -> PreparationSessionRecord:
    return save_preparation_session(request)


@app.get("/history/users/{user_id}/preparation-sessions", response_model=list[PreparationSessionRecord])
def get_preparation_session_records(user_id: str) -> list[PreparationSessionRecord]:
    return list_preparation_sessions(user_id)
