from pydantic import BaseModel, Field


class ExperienceRange(BaseModel):
    minYears: float | None = Field(default=None, ge=0, le=50)
    maxYears: float | None = Field(default=None, ge=0, le=50)


class ParsedJobDescription(BaseModel):
    roleTitle: str | None = None
    experienceRange: ExperienceRange = Field(default_factory=ExperienceRange)
    requiredSkills: list[str] = Field(default_factory=list)
    preferredSkills: list[str] = Field(default_factory=list)
    requiredCertifications: list[str] = Field(default_factory=list)
    emphasizedRequirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    workModes: list[str] = Field(default_factory=list)
    senioritySignals: list[str] = Field(default_factory=list)


class JdParseRequest(BaseModel):
    rawJobDescriptionText: str = Field(min_length=20)


class JdParseResponse(BaseModel):
    normalizedJobDescriptionText: str
    parsedJobDescription: ParsedJobDescription
    warnings: list[str] = Field(default_factory=list)
