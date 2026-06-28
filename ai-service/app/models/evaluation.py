from typing import Literal

from pydantic import BaseModel, Field


class MatchFeedbackSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    analysisId: str | None = Field(default=None, min_length=2, max_length=80)
    jobOpportunityId: str | None = Field(default=None, min_length=2, max_length=80)
    roleFamily: str | None = Field(default=None, max_length=80)
    algorithmScore: int | None = Field(default=None, ge=0, le=100)
    fitCategory: str | None = Field(default=None, max_length=80)
    expectedFit: Literal["strong", "good", "partial", "weak"]
    scoreAccuracy: Literal["accurate", "too_high", "too_low"]
    outcome: Literal["not_applied", "applied", "shortlisted", "interview", "rejected", "offer", "no_response"] = "not_applied"
    notes: str | None = Field(default=None, max_length=1200)


class MatchFeedbackRecord(BaseModel):
    id: str
    userId: str
    analysisId: str | None = None
    jobOpportunityId: str | None = None
    roleFamily: str | None = None
    expectedFit: str
    scoreAccuracy: str
    outcome: str
    algorithmScore: int | None = None
    fitCategory: str | None = None
    notes: str | None = None
    createdAt: str


class MatchFeedbackSegmentSummary(BaseModel):
    feedbackCount: int
    accurateCount: int
    tooHighCount: int
    tooLowCount: int
    accuracyRate: float | None = None
    averageAlgorithmScore: float | None = None
    calibrationRecommendation: str


class MatchFeedbackSummary(BaseModel):
    feedbackCount: int
    accurateCount: int
    tooHighCount: int
    tooLowCount: int
    accuracyRate: float | None = None
    averageScoreByAccuracy: dict[str, float] = Field(default_factory=dict)
    outcomeCounts: dict[str, int] = Field(default_factory=dict)
    calibrationRecommendation: str
    averageAlgorithmScore: float | None = None
    roleFamilyBreakdown: dict[str, MatchFeedbackSegmentSummary] = Field(default_factory=dict)
    latestFeedback: list[MatchFeedbackRecord] = Field(default_factory=list)


class MatchFeedbackDataset(BaseModel):
    userId: str
    exportedAt: str
    records: list[MatchFeedbackRecord] = Field(default_factory=list)


class MatchFeedbackImportRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    records: list[MatchFeedbackSaveRequest] = Field(default_factory=list, max_length=500)
