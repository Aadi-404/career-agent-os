from typing import Literal

from pydantic import BaseModel, Field


class CandidateContext(BaseModel):
    targetRole: str = Field(min_length=2, max_length=120)
    experienceYears: int = Field(ge=0, le=50)
    currentStack: list[str] = Field(min_length=1, max_length=30)
    targetMarket: str = Field(min_length=2, max_length=120)
    currentLocation: str | None = Field(default=None, max_length=120)
    preferredLocations: list[str] = Field(default_factory=list, max_length=20)
    noticePeriodDays: int | None = Field(default=None, ge=0, le=365)
    servingNotice: bool | None = None
    lastWorkingDay: str | None = Field(default=None, max_length=40)
    currentCtcLpa: float | None = Field(default=None, ge=0, le=500)
    expectedCtcLpa: float | None = Field(default=None, ge=0, le=500)
    workModePreference: list[str] = Field(default_factory=list, max_length=10)
    relocationOpen: bool | None = None
    companyTypePreference: list[str] = Field(default_factory=list, max_length=10)


class LlmOptions(BaseModel):
    mode: Literal["mock", "live"] = "mock"
    provider: Literal["openai", "gemini", "groq"] = "groq"
    model: str = Field(default="llama-3.3-70b-versatile", min_length=2, max_length=120)


class AnalyzeRequest(BaseModel):
    resumeText: str = Field(min_length=50)
    jobDescriptionText: str = Field(min_length=50)
    candidateContext: CandidateContext
    llmOptions: LlmOptions | None = None
    preparationPlanDays: int = Field(default=7, ge=1, le=30)


class MatchingSkill(BaseModel):
    skill: str
    evidenceFromResume: str
    jdRequirement: str


class WeaklyEvidencedSkill(BaseModel):
    skill: str
    source: str
    whyWeak: str
    howToStrengthenResume: str


class MissingSkill(BaseModel):
    skill: str
    importance: Literal["high", "medium", "low"]
    whyItMatters: str
    howToPrepare: str


class ResumeImprovement(BaseModel):
    currentIssue: str
    suggestedBullet: str
    reason: str


class InterviewQuestion(BaseModel):
    topic: str
    question: str
    difficulty: Literal["easy", "medium", "hard"]
    expectedFocus: str


class CrossQuestion(BaseModel):
    question: str
    whyAsked: str
    expectedAnswerHint: str


class SystemDesignReadiness(BaseModel):
    level: Literal["strong", "moderate", "weak"]
    reason: str
    topicsToPrepare: list[str]


class DayPlan(BaseModel):
    day: int = Field(ge=1, le=30)
    focus: str
    tasks: list[str] = Field(min_length=1)


class DebugInfo(BaseModel):
    mode: Literal["mock", "llm"]
    provider: str | None = None
    model: str | None = None
    promptPreview: str
    receivedExperienceYears: int
    receivedTargetRole: str
    receivedCurrentStack: list[str]
    scoreReason: str


class ScoreBreakdownItem(BaseModel):
    category: str
    weight: int = Field(ge=0, le=100)
    score: int = Field(ge=0, le=100)
    weightedScore: float = Field(ge=0, le=100)
    reason: str


class ShortlistingFactor(BaseModel):
    factor: str
    impact: Literal["positive", "neutral", "negative"]
    reason: str


class RequirementMatch(BaseModel):
    requirement: str
    category: str
    importance: Literal["high", "medium", "low"]
    bestEvidence: str | None = None
    evidenceSource: Literal["experience", "project", "skills", "certification", "achievement", "candidate_context", "other", "missing"]
    score: int = Field(ge=0, le=100)
    matchType: str
    reason: str


class AnalysisResponse(BaseModel):
    technicalMatchScore: int = Field(ge=0, le=100)
    shortlistingScore: int | None = Field(default=None, ge=0, le=100)
    interviewReadinessScore: int | None = Field(default=None, ge=0, le=100)
    overallOpportunityScore: int | None = Field(default=None, ge=0, le=100)
    overallSummary: str
    fitCategory: Literal["Strong Fit", "Good Fit", "Partial Fit", "Weak Fit"]
    scoreBreakdown: list[ScoreBreakdownItem] = Field(default_factory=list)
    shortlistingFactors: list[ShortlistingFactor] = Field(default_factory=list)
    requirementMatches: list[RequirementMatch] = Field(default_factory=list)
    recommendedAction: str | None = None
    matchingSkills: list[MatchingSkill]
    weaklyEvidencedSkills: list[WeaklyEvidencedSkill]
    missingSkills: list[MissingSkill]
    resumeImprovements: list[ResumeImprovement]
    interviewQuestions: list[InterviewQuestion]
    crossQuestions: list[CrossQuestion]
    systemDesignReadiness: SystemDesignReadiness
    sevenDayPlan: list[DayPlan] = Field(min_length=1, max_length=30)
    debug: DebugInfo | None = None
