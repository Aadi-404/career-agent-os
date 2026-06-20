from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.analysis import AnalysisResponse, AnalyzeRequest, PreparationIntelligence
from app.models.jd_parse import ParsedJobDescription
from app.models.resume_normalize import StructuredResume


class UserCreateRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    displayName: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=180)


class UserRecord(BaseModel):
    id: str
    displayName: str
    email: str | None = None
    createdAt: str


class ResumeSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=160)
    source: Literal["text", "file", "manual"] = "manual"
    rawText: str = Field(min_length=1)
    normalizedText: str | None = None
    structuredResume: StructuredResume | None = None


class ResumeRecord(BaseModel):
    id: str
    userId: str
    title: str
    source: str
    rawText: str
    normalizedText: str | None = None
    structuredResume: StructuredResume | None = None
    createdAt: str
    updatedAt: str


class JobDescriptionSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    rawText: str = Field(min_length=1)
    normalizedText: str | None = None
    parsedJobDescription: ParsedJobDescription | None = None


class JobDescriptionRecord(BaseModel):
    id: str
    userId: str
    title: str
    company: str | None = None
    rawText: str
    normalizedText: str | None = None
    parsedJobDescription: ParsedJobDescription | None = None
    createdAt: str
    updatedAt: str


class AnalysisSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=180)
    resumeId: str | None = None
    jobDescriptionId: str | None = None
    request: AnalyzeRequest
    response: AnalysisResponse


class AnalysisRecord(BaseModel):
    id: str
    userId: str
    resumeId: str | None = None
    jobDescriptionId: str | None = None
    title: str
    technicalMatchScore: int
    fitCategory: str
    request: AnalyzeRequest
    response: AnalysisResponse
    createdAt: str


class PreparationSessionSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    analysisId: str | None = None
    title: str = Field(min_length=2, max_length=180)
    status: Literal["planned", "in_progress", "completed", "paused"] = "planned"
    plan: PreparationIntelligence | dict[str, Any]


class PreparationSessionRecord(BaseModel):
    id: str
    userId: str
    analysisId: str | None = None
    title: str
    status: str
    plan: PreparationIntelligence | dict[str, Any]
    createdAt: str
    updatedAt: str


class WorkspaceSummary(BaseModel):
    user: UserRecord
    resumeCount: int
    jobDescriptionCount: int
    analysisCount: int
    preparationSessionCount: int
    latestAnalysis: AnalysisRecord | None = None
