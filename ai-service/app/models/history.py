from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.models.analysis import AnalysisResponse, AnalyzeRequest, PreparationIntelligence
from app.models.jd_parse import ParsedJobDescription
from app.models.resume_normalize import StructuredResume


class UserCreateRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    displayName: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=180)
    role: Literal["member", "admin"] | None = None
    subscriptionTier: Literal["free", "premium"] | None = None


class UserRecord(BaseModel):
    id: str
    displayName: str
    email: str | None = None
    role: str = "member"
    subscriptionTier: str = "free"
    subscriptionStatus: str = "inactive"
    subscriptionPlanId: str | None = None
    billingProviderCustomerId: str | None = None
    billingProviderSubscriptionId: str | None = None
    billingPeriodEnd: str | None = None
    createdAt: str


class UserSubscriptionTierUpdateRequest(BaseModel):
    subscriptionTier: Literal["free", "premium"]


class UserBillingUpdateRequest(BaseModel):
    subscriptionTier: Literal["free", "premium"] | None = None
    subscriptionStatus: Literal["inactive", "trialing", "active", "past_due", "canceled"] = "inactive"
    subscriptionPlanId: str | None = Field(default=None, max_length=120)
    billingProviderCustomerId: str | None = Field(default=None, max_length=180)
    billingProviderSubscriptionId: str | None = Field(default=None, max_length=180)
    billingPeriodEnd: str | None = Field(default=None, max_length=80)


class BillingCheckoutResponse(BaseModel):
    provider: Literal["manual", "stripe", "razorpay", "paddle"]
    checkoutUrl: str | None = None
    successUrl: str | None = None
    cancelUrl: str | None = None
    configured: bool = False
    message: str


class BillingWebhookSubscriptionEvent(BaseModel):
    provider: Literal["stripe", "razorpay", "paddle", "manual", "other"] = "other"
    eventId: str | None = Field(default=None, max_length=180)
    eventType: str | None = Field(default=None, max_length=180)
    userId: str | None = Field(default=None, min_length=2, max_length=80)
    subscriptionTier: Literal["free", "premium"] | None = None
    subscriptionStatus: Literal["inactive", "trialing", "active", "past_due", "canceled"] = "inactive"
    subscriptionPlanId: str | None = Field(default=None, max_length=120)
    billingProviderCustomerId: str | None = Field(default=None, max_length=180)
    billingProviderSubscriptionId: str | None = Field(default=None, max_length=180)
    billingPeriodEnd: str | None = Field(default=None, max_length=80)
    providerPayload: dict[str, Any] = Field(default_factory=dict)


class AnonymousSessionCreateRequest(BaseModel):
    anonymousSessionId: str | None = Field(default=None, min_length=8, max_length=120)


class AnonymousSessionRecord(BaseModel):
    id: str
    createdAt: str
    lastSeenAt: str
    convertedUserId: str | None = None


class ResumeSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=160)
    source: Literal["text", "file", "manual"] = "manual"
    rawText: str = Field(min_length=1)
    normalizedText: str | None = None
    structuredResume: StructuredResume | None = None


class ResumeRecord(BaseModel):
    id: str
    userId: str
    title: str
    source: str
    rawText: str
    normalizedText: str | None = None
    structuredResume: StructuredResume | None = None
    createdAt: str
    updatedAt: str


class ResumeVersionSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    resumeId: str = Field(min_length=2, max_length=80)
    analysisId: str | None = Field(default=None, min_length=2, max_length=80)
    acceptedRewriteId: str | None = Field(default=None, min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=180)
    changeSummary: str = Field(min_length=2, max_length=1000)
    normalizedText: str = Field(min_length=1)
    structuredResume: StructuredResume


class ResumeVersionRecord(BaseModel):
    id: str
    userId: str
    resumeId: str
    analysisId: str | None = None
    acceptedRewriteId: str | None = None
    title: str
    changeSummary: str
    normalizedText: str
    structuredResume: StructuredResume
    createdAt: str


class ResumeVersionRestoreSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    resumeVersionId: str = Field(min_length=2, max_length=80)
    resumeId: str = Field(min_length=2, max_length=80)
    analysisId: str | None = Field(default=None, min_length=2, max_length=80)
    reason: str = Field(min_length=2, max_length=1000)


class ResumeVersionRestoreRecord(BaseModel):
    id: str
    userId: str
    resumeVersionId: str
    resumeId: str
    analysisId: str | None = None
    reason: str
    createdAt: str


class JobDescriptionSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    rawText: str = Field(min_length=1)
    normalizedText: str | None = None
    parsedJobDescription: ParsedJobDescription | None = None


class JobDescriptionRecord(BaseModel):
    id: str
    userId: str
    title: str
    company: str | None = None
    rawText: str
    normalizedText: str | None = None
    parsedJobDescription: ParsedJobDescription | None = None
    createdAt: str
    updatedAt: str


class AnalysisSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=180)
    resumeId: str | None = None
    jobDescriptionId: str | None = None
    fingerprint: str | None = Field(default=None, min_length=16, max_length=128)
    request: AnalyzeRequest
    response: AnalysisResponse
    optionalArtifacts: dict[str, Any] = Field(default_factory=dict)


class AnalysisLookupRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    fingerprint: str = Field(min_length=16, max_length=128)


class AnalysisRecord(BaseModel):
    id: str
    userId: str
    resumeId: str | None = None
    jobDescriptionId: str | None = None
    title: str
    fingerprint: str | None = None
    technicalMatchScore: int
    fitCategory: str
    request: AnalyzeRequest
    response: AnalysisResponse
    optionalArtifacts: dict[str, Any] = Field(default_factory=dict)
    createdAt: str


class OptionalArtifactUsageUpdateRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    artifactKey: str = Field(min_length=2, max_length=80)
    response: AnalysisResponse


class ComparisonResultItem(BaseModel):
    id: str = Field(min_length=3, max_length=220)
    resumeId: str = Field(min_length=3, max_length=120)
    resumeTitle: str = Field(min_length=1, max_length=180)
    jobDescriptionId: str = Field(min_length=3, max_length=120)
    jobTitle: str = Field(min_length=1, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    score: int = Field(ge=0, le=100)
    fitCategory: str = Field(min_length=1, max_length=120)
    recommendedAction: str | None = Field(default=None, max_length=1000)


class ComparisonRunSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=180)
    resumeIds: list[str] = Field(min_length=1, max_length=9)
    jobDescriptionIds: list[str] = Field(min_length=1, max_length=9)
    results: list[ComparisonResultItem] = Field(min_length=1, max_length=9)


class ComparisonRunUpdateRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=180)


class ComparisonRunDeleteRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)


class ComparisonRunRecord(BaseModel):
    id: str
    userId: str
    title: str
    resumeIds: list[str]
    jobDescriptionIds: list[str]
    results: list[ComparisonResultItem]
    createdAt: str


class PreparationSessionSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    analysisId: str | None = None
    title: str = Field(min_length=2, max_length=180)
    status: Literal["planned", "in_progress", "completed", "paused"] = "planned"
    plan: PreparationIntelligence | dict[str, Any]
    progress: dict[str, Any] | None = None


class PreparationSessionProgressUpdateRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    status: Literal["planned", "in_progress", "completed", "paused"] | None = None
    progress: dict[str, Any] = Field(default_factory=dict)


class PreparationSessionRecord(BaseModel):
    id: str
    userId: str
    analysisId: str | None = None
    title: str
    status: str
    plan: PreparationIntelligence | dict[str, Any]
    progress: dict[str, Any] | None = None
    createdAt: str
    updatedAt: str


class JobOpportunitySaveRequest(BaseModel):
    userId: str | None = Field(default=None, min_length=2, max_length=80)
    anonymousSessionId: str | None = Field(default=None, min_length=8, max_length=120)
    resumeId: str | None = None
    analysisId: str | None = None
    title: str = Field(min_length=2, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    location: str | None = Field(default=None, max_length=180)
    url: str | None = Field(default=None, max_length=1000)
    description: str = Field(min_length=20)
    status: Literal["viewed", "shortlisted", "applied", "interview", "rejected", "offer", "archived"] = "viewed"
    technicalMatchScore: int | None = Field(default=None, ge=0, le=100)
    fitCategory: str | None = Field(default=None, max_length=80)
    analysisResponse: AnalysisResponse | None = None
    optionalArtifacts: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_owner(self):
        if not self.userId and not self.anonymousSessionId:
            raise ValueError("Either userId or anonymousSessionId is required")
        return self


class JobOpportunityStatusUpdateRequest(BaseModel):
    userId: str | None = Field(default=None, min_length=2, max_length=80)
    status: Literal["viewed", "shortlisted", "applied", "interview", "rejected", "offer", "archived"]


class JobOpportunityRecord(BaseModel):
    id: str
    userId: str | None = None
    anonymousSessionId: str | None = None
    resumeId: str | None = None
    analysisId: str | None = None
    title: str
    company: str | None = None
    location: str | None = None
    url: str | None = None
    description: str
    status: str
    technicalMatchScore: int | None = None
    fitCategory: str | None = None
    analysisResponse: AnalysisResponse | None = None
    optionalArtifacts: dict[str, Any] = Field(default_factory=dict)
    createdAt: str
    updatedAt: str


class ResearchSource(BaseModel):
    title: str = Field(min_length=1, max_length=220)
    url: str | None = Field(default=None, max_length=1000)
    sourceType: Literal["manual", "job_post", "interview_experience", "company_page", "market_signal", "other"] = "manual"
    note: str | None = Field(default=None, max_length=1200)


class ResearchNoteSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    roleTitle: str | None = Field(default=None, max_length=180)
    researchType: Literal["company", "role", "market", "interview", "manual"] = "manual"
    summary: str = Field(min_length=10, max_length=4000)
    keySignals: list[str] = Field(default_factory=list, max_length=30)
    preparationTopics: list[str] = Field(default_factory=list, max_length=30)
    sources: list[ResearchSource] = Field(default_factory=list, max_length=20)


class ResearchNoteRecord(BaseModel):
    id: str
    userId: str
    title: str
    company: str | None = None
    roleTitle: str | None = None
    researchType: str
    summary: str
    keySignals: list[str] = Field(default_factory=list)
    preparationTopics: list[str] = Field(default_factory=list)
    sources: list[ResearchSource] = Field(default_factory=list)
    createdAt: str
    updatedAt: str


class AcceptedResumeRewriteSaveRequest(BaseModel):
    userId: str = Field(min_length=2, max_length=80)
    analysisId: str | None = Field(default=None, min_length=2, max_length=80)
    resumeId: str | None = Field(default=None, min_length=2, max_length=80)
    jobDescriptionId: str | None = Field(default=None, min_length=2, max_length=80)
    targetRequirement: str = Field(min_length=2, max_length=500)
    evidenceSource: str = Field(min_length=2, max_length=120)
    proofSafety: Literal["safe_from_existing_evidence", "needs_user_verification"]
    originalEvidence: str | None = Field(default=None, max_length=4000)
    currentIssue: str = Field(min_length=2, max_length=2000)
    acceptedBullet: str = Field(min_length=2, max_length=2000)
    reason: str = Field(min_length=2, max_length=2000)
    targetSection: Literal["experience", "project", "skills", "certifications", "achievements"]
    targetLabel: str | None = Field(default=None, max_length=240)


class AcceptedResumeRewriteRecord(BaseModel):
    id: str
    userId: str
    analysisId: str | None = None
    resumeId: str | None = None
    jobDescriptionId: str | None = None
    targetRequirement: str
    evidenceSource: str
    proofSafety: str
    originalEvidence: str | None = None
    currentIssue: str
    acceptedBullet: str
    reason: str
    targetSection: str
    targetLabel: str | None = None
    createdAt: str


class WorkspaceSummary(BaseModel):
    user: UserRecord
    resumeCount: int
    jobDescriptionCount: int
    analysisCount: int
    preparationSessionCount: int
    jobOpportunityCount: int = 0
    researchNoteCount: int = 0
    averageMatchScore: int | None = None
    bestMatchScore: int | None = None
    activeOpportunityCount: int = 0
    interviewOpportunityCount: int = 0
    offerOpportunityCount: int = 0
    completedPreparationCount: int = 0
    pipelineStatusCounts: dict[str, int] = Field(default_factory=dict)
    applicationToInterviewRate: int | None = None
    interviewToOfferRate: int | None = None
    positiveOutcomeRate: int | None = None
    latestAnalysis: AnalysisRecord | None = None


class UsageEventRecord(BaseModel):
    id: str
    userId: str | None = None
    anonymousSessionId: str | None = None
    module: str
    mode: str | None = None
    provider: str | None = None
    model: str | None = None
    estimatedUnits: int = 1
    createdAt: str


class UsageQuotaStatus(BaseModel):
    userId: str | None = None
    anonymousSessionId: str | None = None
    tier: str
    window: str = "monthly"
    windowStartAt: str
    resetAt: str
    usedUnits: int
    limitUnits: int | None = None
    remainingUnits: int | None = None
    unlimited: bool = False


class UsageSummary(BaseModel):
    totalEvents: int
    totalEstimatedUnits: int
    byModule: dict[str, int]
    byUser: dict[str, int]
    latestEvents: list[UsageEventRecord]
    quota: UsageQuotaStatus | None = None
