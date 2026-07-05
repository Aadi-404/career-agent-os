from typing import Literal

from pydantic import BaseModel, Field


class CandidateContext(BaseModel):
    targetRole: str = Field(min_length=2, max_length=120)
    experienceYears: float = Field(ge=0, le=50)
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
    scoringCalibrationUserId: str | None = Field(default=None, min_length=2, max_length=80)
    roleFamily: str | None = Field(default=None, max_length=80)


class PreparationBuildRequest(BaseModel):
    sourceRequest: AnalyzeRequest
    analysis: "AnalysisResponse"
    preparationPlanDays: int = Field(default=7, ge=1, le=30)
    researchNotes: list["ResearchContextNote"] = Field(default_factory=list, max_length=20)


class OptionalArtifactBuildRequest(BaseModel):
    sourceRequest: AnalyzeRequest
    analysis: "AnalysisResponse"
    limit: int = Field(default=8, ge=1, le=20)


class ResearchContextSource(BaseModel):
    title: str = Field(min_length=1, max_length=220)
    url: str | None = Field(default=None, max_length=1000)
    sourceType: str = Field(default="manual", max_length=80)
    note: str | None = Field(default=None, max_length=1200)
    citationQuality: str = Field(default="uncited", max_length=40)
    validationIssues: list[str] = Field(default_factory=list, max_length=10)


class ResearchContextNote(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    roleTitle: str | None = Field(default=None, max_length=180)
    researchType: str = Field(default="manual", max_length=80)
    summary: str = Field(min_length=1, max_length=4000)
    keySignals: list[str] = Field(default_factory=list, max_length=30)
    preparationTopics: list[str] = Field(default_factory=list, max_length=30)
    sources: list[ResearchContextSource] = Field(default_factory=list, max_length=20)


class ResearchNoteDraft(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    roleTitle: str | None = Field(default=None, max_length=180)
    researchType: str = Field(default="role", max_length=80)
    summary: str = Field(min_length=10, max_length=4000)
    keySignals: list[str] = Field(default_factory=list, max_length=30)
    preparationTopics: list[str] = Field(default_factory=list, max_length=30)
    sources: list[ResearchContextSource] = Field(default_factory=list, max_length=20)
    researchProvider: str = Field(default="local", max_length=80)
    providerWarnings: list[str] = Field(default_factory=list, max_length=20)
    marketOpportunitySignals: list[str] = Field(default_factory=list, max_length=20)
    roleCompanySynthesis: list[str] = Field(default_factory=list, max_length=20)


class ResearchBuildRequest(BaseModel):
    sourceRequest: AnalyzeRequest
    analysis: "AnalysisResponse"
    company: str | None = Field(default=None, max_length=180)
    roleTitle: str | None = Field(default=None, max_length=180)
    researchType: str = Field(default="role", max_length=80)
    manualContext: str | None = Field(default=None, max_length=5000)
    sourceUrls: list[str] = Field(default_factory=list, max_length=10)


class ApplicationDecisionRequest(BaseModel):
    sourceRequest: AnalyzeRequest
    analysis: "AnalysisResponse"
    researchNotes: list[ResearchContextNote] = Field(default_factory=list, max_length=20)
    opportunityStatus: str | None = Field(default=None, max_length=80)
    company: str | None = Field(default=None, max_length=180)
    roleTitle: str | None = Field(default=None, max_length=180)


class ApplicationDecisionResponse(BaseModel):
    decision: Literal["apply", "prepare_first", "selective_apply", "skip"]
    confidence: Literal["low", "medium", "high"]
    headline: str
    reasoning: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    nextActions: list[str] = Field(default_factory=list)
    researchSignalsUsed: list[str] = Field(default_factory=list)
    scoreSignals: dict[str, int | None] = Field(default_factory=dict)


class ResumeRewriteRequest(BaseModel):
    sourceRequest: AnalyzeRequest
    analysis: "AnalysisResponse"
    resumeText: str = Field(min_length=50, max_length=30000)
    limit: int = Field(default=8, ge=1, le=20)


class ResumeRewriteSuggestion(BaseModel):
    targetRequirement: str
    evidenceSource: str
    originalEvidence: str | None = None
    currentIssue: str
    rewrittenBullet: str
    proofSafety: Literal["safe_from_existing_evidence", "needs_user_verification", "gap_do_not_claim"]
    reason: str


class ResumeRewriteResponse(BaseModel):
    summary: str
    suggestions: list[ResumeRewriteSuggestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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


class PriorityTopic(BaseModel):
    topic: str
    priority: Literal["critical", "high", "medium", "low"]
    sourceRequirement: str
    reason: str
    currentEvidence: str | None = None
    targetDepth: str
    actions: list[str] = Field(default_factory=list)


class PreparationDay(BaseModel):
    day: int = Field(ge=1, le=30)
    focus: str
    goal: str
    tasks: list[str] = Field(min_length=1)
    output: str


class CrossQuestionChain(BaseModel):
    topic: str
    openingQuestion: str
    followUps: list[str] = Field(min_length=1)
    expectedAnswerFocus: str
    risk: str


class PreparationIntelligence(BaseModel):
    summary: str
    priorityTopics: list[PriorityTopic] = Field(default_factory=list)
    dailyPlan: list[PreparationDay] = Field(default_factory=list)
    crossQuestionChains: list[CrossQuestionChain] = Field(default_factory=list)
    phase5ResearchBacklog: list[str] = Field(default_factory=list)


class DebugInfo(BaseModel):
    mode: Literal["mock", "llm"]
    provider: str | None = None
    model: str | None = None
    promptPreview: str
    receivedExperienceYears: float
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
    sevenDayPlan: list[DayPlan] = Field(default_factory=list, max_length=30)
    preparationIntelligence: PreparationIntelligence | None = None
    debug: DebugInfo | None = None


class AgentToolRecommendation(BaseModel):
    tool: Literal[
        "score",
        "research_note",
        "preparation_plan",
        "resume_rewrite",
        "application_decision",
        "interview_questions",
        "cross_questions",
        "gap_report",
        "save_progress",
    ]
    priority: Literal["critical", "high", "medium", "low"]
    reason: str
    endpoint: str | None = None
    estimatedUnits: int = Field(default=1, ge=0, le=10)
    requiresPremium: bool = False
    alreadySatisfied: bool = False


class CareerAgentPlanRequest(BaseModel):
    sourceRequest: AnalyzeRequest
    analysis: AnalysisResponse
    researchNotes: list[ResearchContextNote] = Field(default_factory=list, max_length=20)
    preparation: PreparationIntelligence | None = None
    generatedArtifacts: list[str] = Field(default_factory=list, max_length=30)
    company: str | None = Field(default=None, max_length=180)
    roleTitle: str | None = Field(default=None, max_length=180)


class CareerAgentPlanResponse(BaseModel):
    phase: str = "Phase 8"
    headline: str
    nextBestAction: str
    reasoning: list[str] = Field(default_factory=list)
    recommendations: list[AgentToolRecommendation] = Field(default_factory=list)
    memorySignals: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
