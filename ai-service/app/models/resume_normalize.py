from pydantic import BaseModel, Field


class ResumeProfile(BaseModel):
    name: str | None = None
    location: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    summary: str | None = None


class ResumeExperience(BaseModel):
    title: str | None = None
    company: str | None = None
    duration: str | None = None
    location: str | None = None
    highlights: list[str] = Field(default_factory=list)


class ResumeProject(BaseModel):
    name: str
    duration: str | None = None
    techStack: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class StructuredResume(BaseModel):
    profile: ResumeProfile = Field(default_factory=ResumeProfile)
    experience: list[ResumeExperience] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class ResumeNormalizeRequest(BaseModel):
    rawResumeText: str = Field(min_length=20)


class ResumeParserDebug(BaseModel):
    detectedSections: dict[str, int] = Field(default_factory=dict)
    parsedCounts: dict[str, int] = Field(default_factory=dict)
    rawLineCount: int = 0
    parserNotes: list[str] = Field(default_factory=list)


class ResumeNormalizeResponse(BaseModel):
    normalizedResumeText: str
    structuredResume: StructuredResume
    warnings: list[str] = Field(default_factory=list)
    parserDebug: ResumeParserDebug | None = None
