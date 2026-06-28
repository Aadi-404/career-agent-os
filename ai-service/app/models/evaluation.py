from typing import Literal

from pydantic import BaseModel, Field


class MatchFeedbackSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    analysisId: str | None = Field(default=None, min_length=2, max_length=80)
    jobOpportunityId: str | None = Field(default=None, min_length=2, max_length=80)
    expectedFit: Literal["strong", "good", "partial", "weak"]
    scoreAccuracy: Literal["accurate", "too_high", "too_low"]
    outcome: Literal["not_applied", "applied", "shortlisted", "interview", "rejected", "offer", "no_response"] = "not_applied"
    notes: str | None = Field(default=None, max_length=1200)


class MatchFeedbackRecord(BaseModel):
    id: str
    userId: str
    analysisId: str | None = None
    jobOpportunityId: str | None = None
    expectedFit: str
    scoreAccuracy: str
    outcome: str
    algorithmScore: int | None = None
    fitCategory: str | None = None
    notes: str | None = None
    createdAt: str


class MatchFeedbackSummary(BaseModel):
    feedbackCount: int
    accurateCount: int
    tooHighCount: int
    tooLowCount: int
    averageAlgorithmScore: float | None = None
    latestFeedback: list[MatchFeedbackRecord] = Field(default_factory=list)
