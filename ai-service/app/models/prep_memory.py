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


class PrepTodayFocus(BaseModel):
    sessionId: str
    sessionTitle: str
    day: int = Field(ge=1, le=30)
    taskId: str | None = None
    task: str
    status: str
    confidence: str | None = None
    urgency: str
    reason: str


class PrepAttentionSession(BaseModel):
    sessionId: str
    title: str
    currentPlanDay: int = Field(ge=1, le=30)
    completionPercent: int = Field(ge=0, le=100)
    overdueTaskCount: int = Field(ge=0)
    lowConfidenceDays: int = Field(ge=0)
    nextTask: str | None = None
    reason: str


class PrepNextAction(BaseModel):
    kind: str
    label: str
    sessionId: str | None = None
    sessionTitle: str | None = None
    day: int | None = Field(default=None, ge=1, le=30)
    taskId: str | None = None
    task: str | None = None
    reason: str


class PrepMemoryResponse(BaseModel):
    summary: str
    repeatedWeakTopics: list[PrepMemoryTopic] = Field(default_factory=list)
    unfinishedPreparation: list[PrepProgressMemory] = Field(default_factory=list)
    todayFocus: list[PrepTodayFocus] = Field(default_factory=list)
    attentionSessions: list[PrepAttentionSession] = Field(default_factory=list)
    nextRecommendedActions: list[str] = Field(default_factory=list)
    nextAction: PrepNextAction | None = None
