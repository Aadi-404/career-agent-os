from pydantic import BaseModel, Field


class DemoSeedRequest(BaseModel):
    userId: str = Field(default="demo-aditya", min_length=2, max_length=80)
    displayName: str = Field(default="Aditya Demo", min_length=2, max_length=120)
    email: str | None = Field(default="demo.aditya@example.com", max_length=180)
    password: str = Field(default="DemoPass123!", min_length=8, max_length=160)
    subscriptionTier: str = Field(default="premium", pattern="^(free|premium)$")
    reset: bool = True


class DemoSeedResponse(BaseModel):
    userId: str
    displayName: str
    email: str | None = None
    password: str
    subscriptionTier: str
    resumeCount: int
    jobDescriptionCount: int
    analysisCount: int
    preparationSessionCount: int
    jobOpportunityCount: int
    researchNoteCount: int
    averageMatchScore: int | None = None
    sessionToken: str
    message: str


class DemoCleanupRequest(BaseModel):
    userId: str = Field(default="demo-aditya", min_length=2, max_length=80)
    confirm: bool = False


class DemoCleanupResponse(BaseModel):
    userId: str
    deleted: bool
    resumeCount: int = 0
    jobDescriptionCount: int = 0
    analysisCount: int = 0
    preparationSessionCount: int = 0
    jobOpportunityCount: int = 0
    researchNoteCount: int = 0
    usageEventCount: int = 0
    message: str
