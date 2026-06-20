from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.analysis import AnalysisResponse, CandidateContext, LlmOptions
from app.models.history import JobOpportunityRecord


OpportunityStatus = Literal["viewed", "shortlisted", "applied", "interview", "rejected", "offer", "archived"]


class ExtensionJobPayload(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    location: str | None = Field(default=None, max_length=180)
    url: str | None = Field(default=None, max_length=1000)
    description: str = Field(min_length=50)


class ExtensionMatchRequest(BaseModel):
    userId: str | None = Field(default=None, min_length=2, max_length=80)
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
        if not self.userId and not self.anonymousSessionId:
            raise ValueError("Either userId or anonymousSessionId is required")
        if self.resumeId and not self.userId:
            raise ValueError("userId is required when matching by resumeId")
        if not self.resumeId and not self.resumeText:
            raise ValueError("Either resumeId or resumeText is required")
        return self


class ExtensionMatchResponse(BaseModel):
    analysis: AnalysisResponse
    jobOpportunity: JobOpportunityRecord | None = None
