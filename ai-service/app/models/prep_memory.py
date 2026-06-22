from pydantic import BaseModel, Field


class PrepMemoryTopic(BaseModel):
    topic: str
    occurrences: int = Field(ge=0)
    averageScore: int = Field(ge=0, le=100)
    latestEvidence: str | None = None
    recommendation: str


class PrepProgressMemory(BaseModel):
    sessionId: str
    title: str
    status: str
    completionPercent: int = Field(ge=0, le=100)
    unfinishedTaskCount: int = Field(ge=0)
    lowConfidenceDays: int = Field(ge=0)


class PrepMemoryResponse(BaseModel):
    summary: str
    repeatedWeakTopics: list[PrepMemoryTopic] = Field(default_factory=list)
    unfinishedPreparation: list[PrepProgressMemory] = Field(default_factory=list)
    nextRecommendedActions: list[str] = Field(default_factory=list)
