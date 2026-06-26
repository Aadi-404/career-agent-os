from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

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


class AnonymousSessionCreateRequest(BaseModel):
    anonymousSessionId: str | None = Field(default=None, min_length=8, max_length=120)


class AnonymousSessionRecord(BaseModel):
    id: str
    createdAt: str
    lastSeenAt: str
    convertedUserId: str | None = None


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
    fingerprint: str | None = Field(default=None, min_length=16, max_length=128)
    request: AnalyzeRequest
    response: AnalysisResponse
    optionalArtifacts: dict[str, Any] = Field(default_factory=dict)


class AnalysisLookupRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    fingerprint: str = Field(min_length=16, max_length=128)


class AnalysisRecord(BaseModel):
    id: str
    userId: str
    resumeId: str | None = None
    jobDescriptionId: str | None = None
    title: str
    fingerprint: str | None = None
    technicalMatchScore: int
    fitCategory: str
    request: AnalyzeRequest
    response: AnalysisResponse
    optionalArtifacts: dict[str, Any] = Field(default_factory=dict)
    createdAt: str


class OptionalArtifactUsageUpdateRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    artifactKey: str = Field(min_length=2, max_length=80)
    response: AnalysisResponse


class PreparationSessionSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    analysisId: str | None = None
    title: str = Field(min_length=2, max_length=180)
    status: Literal["planned", "in_progress", "completed", "paused"] = "planned"
    plan: PreparationIntelligence | dict[str, Any]
    progress: dict[str, Any] | None = None


class PreparationSessionProgressUpdateRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    status: Literal["planned", "in_progress", "completed", "paused"] | None = None
    progress: dict[str, Any] = Field(default_factory=dict)


class PreparationSessionRecord(BaseModel):
    id: str
    userId: str
    analysisId: str | None = None
    title: str
    status: str
    plan: PreparationIntelligence | dict[str, Any]
    progress: dict[str, Any] | None = None
    createdAt: str
    updatedAt: str


class JobOpportunitySaveRequest(BaseModel):
    userId: str | None = Field(default=None, min_length=2, max_length=80)
    anonymousSessionId: str | None = Field(default=None, min_length=8, max_length=120)
    resumeId: str | None = None
    analysisId: str | None = None
    title: str = Field(min_length=2, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    location: str | None = Field(default=None, max_length=180)
    url: str | None = Field(default=None, max_length=1000)
    description: str = Field(min_length=20)
    status: Literal["viewed", "shortlisted", "applied", "interview", "rejected", "offer", "archived"] = "viewed"
    technicalMatchScore: int | None = Field(default=None, ge=0, le=100)
    fitCategory: str | None = Field(default=None, max_length=80)
    analysisResponse: AnalysisResponse | None = None
    optionalArtifacts: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_owner(self):
        if not self.userId and not self.anonymousSessionId:
            raise ValueError("Either userId or anonymousSessionId is required")
        return self


class JobOpportunityStatusUpdateRequest(BaseModel):
    status: Literal["viewed", "shortlisted", "applied", "interview", "rejected", "offer", "archived"]


class JobOpportunityRecord(BaseModel):
    id: str
    userId: str | None = None
    anonymousSessionId: str | None = None
    resumeId: str | None = None
    analysisId: str | None = None
    title: str
    company: str | None = None
    location: str | None = None
    url: str | None = None
    description: str
    status: str
    technicalMatchScore: int | None = None
    fitCategory: str | None = None
    analysisResponse: AnalysisResponse | None = None
    optionalArtifacts: dict[str, Any] = Field(default_factory=dict)
    createdAt: str
    updatedAt: str


class WorkspaceSummary(BaseModel):
    user: UserRecord
    resumeCount: int
    jobDescriptionCount: int
    analysisCount: int
    preparationSessionCount: int
    jobOpportunityCount: int = 0
    latestAnalysis: AnalysisRecord | None = None
