from pydantic import BaseModel, Field


class WorkspaceMemoryItem(BaseModel):
    id: str
    sourceType: str
    title: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    score: int = Field(ge=0, le=100)
    createdAt: str | None = None


class WorkspaceMemoryGap(BaseModel):
    topic: str
    occurrences: int = Field(ge=0)
    latestEvidence: str | None = None
    recommendation: str


class WorkspaceMemoryResponse(BaseModel):
    userId: str
    summary: str
    memoryScore: int = Field(ge=0, le=100)
    totalItems: int = Field(ge=0)
    topEvidence: list[WorkspaceMemoryItem] = Field(default_factory=list)
    recurringGaps: list[WorkspaceMemoryGap] = Field(default_factory=list)
    researchSignals: list[str] = Field(default_factory=list)
    preparationSignals: list[str] = Field(default_factory=list)
    retrievalQueries: list[str] = Field(default_factory=list)
    nextActions: list[str] = Field(default_factory=list)
