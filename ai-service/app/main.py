from fastapi import FastAPI
from fastapi import File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.models.analysis import AnalyzeRequest, AnalysisResponse
from app.models.jd_parse import JdParseRequest, JdParseResponse
from app.models.resume_extract import ResumeExtractResponse
from app.models.resume_normalize import ResumeNormalizeRequest, ResumeNormalizeResponse
from app.services.analyzer_service import analyze_resume_jd
from app.services.jd_parser import parse_jd
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ai/resume-jd/analyze", response_model=AnalysisResponse)
def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    return analyze_resume_jd(request)


@app.post("/ai/resume/extract", response_model=ResumeExtractResponse)
async def extract(file: UploadFile = File(...)) -> ResumeExtractResponse:
    return await extract_resume(file)


@app.post("/ai/resume/normalize", response_model=ResumeNormalizeResponse)
def normalize(request: ResumeNormalizeRequest) -> ResumeNormalizeResponse:
    return normalize_resume(request)


@app.post("/ai/jd/parse", response_model=JdParseResponse)
def parse_job_description(request: JdParseRequest) -> JdParseResponse:
    return parse_jd(request)
