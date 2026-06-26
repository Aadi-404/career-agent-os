from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.analysis import AnalysisResponse, CandidateContext, LlmOptions
from app.models.history import AnonymousSessionRecord, JobOpportunityRecord


OpportunityStatus = Literal["viewed", "shortlisted", "applied", "interview", "rejected", "offer", "archived"]


class ExtensionJobPayload(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    location: str | None = Field(default=None, max_length=180)
    url: str | None = Field(default=None, max_length=1000)
    description: str = Field(min_length=50)


class ExtensionJobDraft(BaseModel):
    title: str | None = Field(default=None, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    location: str | None = Field(default=None, max_length=180)
    url: str | None = Field(default=None, max_length=1000)
    description: str = Field(default="", max_length=20000)
    parseConfidence: Literal["high", "medium", "low"] = "low"
    warnings: list[str] = Field(default_factory=list)


class ExtensionPageParseRequest(BaseModel):
    pageTitle: str | None = Field(default=None, max_length=300)
    pageUrl: str | None = Field(default=None, max_length=1000)
    selectedText: str | None = Field(default=None, max_length=20000)
    pageText: str | None = Field(default=None, max_length=50000)
    extractedTitle: str | None = Field(default=None, max_length=180)
    extractedCompany: str | None = Field(default=None, max_length=180)
    extractedLocation: str | None = Field(default=None, max_length=180)
    extractedDescription: str | None = Field(default=None, max_length=50000)
    source: str | None = Field(default=None, max_length=80)


class ExtensionResumeOption(BaseModel):
    id: str
    title: str
    updatedAt: str
    summary: str
    isStructured: bool


class ExtensionBootstrapRequest(BaseModel):
    userId: str | None = Field(default=None, min_length=2, max_length=80)
    sessionToken: str | None = Field(default=None, min_length=20, max_length=240)
    anonymousSessionId: str | None = Field(default=None, min_length=8, max_length=120)


class ExtensionUserSession(BaseModel):
    userId: str
    displayName: str
    sessionToken: str


class ExtensionBootstrapResponse(BaseModel):
    anonymousSession: AnonymousSessionRecord
    userSession: ExtensionUserSession | None = None
    resumes: list[ExtensionResumeOption] = Field(default_factory=list)
    manualPasteRequired: bool = False
    defaultCandidateContext: CandidateContext | None = None


class ExtensionSessionClaimRequest(BaseModel):
    anonymousSessionId: str = Field(min_length=8, max_length=120)
    userId: str = Field(min_length=2, max_length=80)
    displayName: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=180)


class ExtensionSessionClaimResponse(BaseModel):
    anonymousSession: AnonymousSessionRecord
    userSession: ExtensionUserSession
    resumes: list[ExtensionResumeOption] = Field(default_factory=list)
    migratedOpportunityCount: int = Field(ge=0)


class ExtensionMatchRequest(BaseModel):
    userId: str | None = Field(default=None, min_length=2, max_length=80)
    sessionToken: str | None = Field(default=None, min_length=20, max_length=240)
    anonymousSessionId: str | None = Field(default=None, min_length=8, max_length=120)
    resumeId: str | None = Field(default=None, min_length=2, max_length=80)
    resumeText: str | None = Field(default=None, min_length=50)
    job: ExtensionJobPayload
    candidateContext: CandidateContext | None = None
    llmOptions: LlmOptions | None = None
    preparationPlanDays: int = Field(default=7, ge=1, le=30)
    saveOpportunity: bool = True
    status: OpportunityStatus = "viewed"

    @model_validator(mode="after")
    def validate_match_inputs(self):
        if not self.userId and not self.sessionToken and not self.anonymousSessionId:
            raise ValueError("Either userId, sessionToken, or anonymousSessionId is required")
        if self.resumeId and not self.userId and not self.sessionToken:
            raise ValueError("userId or sessionToken is required when matching by resumeId")
        if not self.resumeId and not self.resumeText:
            raise ValueError("Either resumeId or resumeText is required")
        return self


class ExtensionMatchResponse(BaseModel):
    analysis: AnalysisResponse
    jobOpportunity: JobOpportunityRecord | None = None
