from typing import Literal

from pydantic import BaseModel, Field


class OpportunityNextAction(BaseModel):
    opportunityId: str
    title: str
    company: str | None = None
    currentStatus: str
    recommendedStatus: Literal["viewed", "shortlisted", "applied", "interview", "rejected", "offer", "archived"] | None = None
    artifactKey: Literal["resume_improvements", "interview_questions", "cross_questions"] | None = None
    endpoint: str | None = None
    priority: Literal["critical", "high", "medium", "low"]
    action: str
    reason: str
    score: int | None = Field(default=None, ge=0, le=100)


class OpportunityNextActionsResponse(BaseModel):
    summary: str
    actions: list[OpportunityNextAction] = Field(default_factory=list)
