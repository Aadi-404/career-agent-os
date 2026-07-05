import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type AnalysisResponse = {
  technicalMatchScore: number;
  shortlistingScore?: number | null;
  interviewReadinessScore?: number | null;
  overallOpportunityScore?: number | null;
  overallSummary: string;
  fitCategory: "Strong Fit" | "Good Fit" | "Partial Fit" | "Weak Fit";
  scoreBreakdown: Array<{ category: string; weight: number; score: number; weightedScore: number; reason: string }>;
  shortlistingFactors: Array<{ factor: string; impact: "positive" | "neutral" | "negative"; reason: string }>;
  requirementMatches: Array<{
    requirement: string;
    category: string;
    importance: "high" | "medium" | "low";
    bestEvidence?: string | null;
    evidenceSource: "experience" | "project" | "skills" | "certification" | "achievement" | "candidate_context" | "other" | "missing";
    score: number;
    matchType: string;
    reason: string;
  }>;
  recommendedAction?: string | null;
  matchingSkills: Array<{ skill: string; evidenceFromResume: string; jdRequirement: string }>;
  weaklyEvidencedSkills: Array<{ skill: string; source: string; whyWeak: string; howToStrengthenResume: string }>;
  missingSkills: Array<{ skill: string; importance: "high" | "medium" | "low"; whyItMatters: string; howToPrepare: string }>;
  resumeImprovements: Array<{ currentIssue: string; suggestedBullet: string; reason: string }>;
  interviewQuestions: Array<{ topic: string; question: string; difficulty: "easy" | "medium" | "hard"; expectedFocus: string }>;
  crossQuestions: Array<{ question: string; whyAsked: string; expectedAnswerHint: string }>;
  systemDesignReadiness: { level: "strong" | "moderate" | "weak"; reason: string; topicsToPrepare: string[] };
  sevenDayPlan: Array<{ day: number; focus: string; tasks: string[] }>;
  preparationIntelligence?: {
    summary: string;
    priorityTopics: Array<{
      topic: string;
      priority: "critical" | "high" | "medium" | "low";
      sourceRequirement: string;
      reason: string;
      currentEvidence?: string | null;
      targetDepth: string;
      actions: string[];
    }>;
    dailyPlan: Array<{
      day: number;
      focus: string;
      goal: string;
      tasks: string[];
      output: string;
    }>;
    crossQuestionChains: Array<{
      topic: string;
      openingQuestion: string;
      followUps: string[];
      expectedAnswerFocus: string;
      risk: string;
    }>;
    phase5ResearchBacklog: string[];
  } | null;
  debug?: {
    mode: "mock" | "llm";
    provider?: string | null;
    model?: string | null;
    promptPreview: string;
    receivedExperienceYears: number;
    receivedTargetRole: string;
    receivedCurrentStack: string[];
    scoreReason: string;
  } | null;
};

type LlmMode = "mock" | "live";
type LlmProvider = "groq" | "openai" | "gemini";
type ResumeSource = "text" | "file";
type ScoreStep = "upload" | "review" | "score";
type ReviewPane = "resume" | "jd";
type ActiveTask = "command" | "matching" | "review" | "report" | "preparation" | "progress" | "history" | "compare" | "research" | "agent" | "decision" | "rewrite" | "extension" | "evaluation" | "settings";
type CostMode = "free" | "standard" | "premium";
type AccessTier = "free" | "premium" | "admin";
type PreparationIntelligence = NonNullable<AnalysisResponse["preparationIntelligence"]>;
type LaunchChecklistState = Record<string, boolean>;

type AnalyzeRequestPayload = {
  resumeText: string;
  jobDescriptionText: string;
  candidateContext: {
    targetRole: string;
    experienceYears: number;
    currentStack: string[];
    targetMarket: string;
    currentLocation: string | null;
    preferredLocations: string[];
    noticePeriodDays: number;
    currentCtcLpa: number | null;
    expectedCtcLpa: number | null;
    workModePreference: string[];
    relocationOpen: boolean;
  };
  llmOptions: {
    mode: LlmMode;
    provider: LlmProvider;
    model: string;
  };
  preparationPlanDays: number;
  scoringCalibrationUserId?: string | null;
  roleFamily?: string | null;
};

type ScoringCalibrationConfig = {
  userId: string;
  roleFamily: string;
  categoryWeights: Record<string, number>;
  isDefault: boolean;
  updatedAt?: string | null;
};

type ScoringCalibrationRecommendation = {
  userId: string;
  roleFamily: string;
  currentWeights: Record<string, number>;
  suggestedWeights: Record<string, number>;
  confidence: string;
  sampleSize: number;
  reason: string;
  changes: string[];
};

type ScoringCalibrationAuditRecord = {
  id: string;
  userId: string;
  roleFamily: string;
  previousWeights: Record<string, number>;
  newWeights: Record<string, number>;
  changeSource: string;
  createdAt: string;
};

type SystemDiagnostics = {
  status: string;
  environment: string;
  databaseOk: boolean;
  llmMode: string;
  llmProvider: string;
  llmModel: string;
  llmKeyConfigured: boolean;
  embeddingProvider: string;
  embeddingModel: string;
  embeddingFallbackLocal: boolean;
  jdParserMode: string;
  corsOrigins: string[];
  workspaceCounts: Record<string, number>;
  warnings: string[];
};

type ProductionReadiness = {
  environment: string;
  readyForProduction: boolean;
  checks: Array<{
    key: string;
    label: string;
    status: "pass" | "warn" | "fail";
    detail: string;
  }>;
  warnings: string[];
};

type AdminUserRecord = {
  id: string;
  displayName: string;
  email?: string | null;
  role: string;
  subscriptionTier?: AccessTier | null;
  subscriptionStatus?: string | null;
  subscriptionPlanId?: string | null;
  billingProviderCustomerId?: string | null;
  billingProviderSubscriptionId?: string | null;
  billingPeriodEnd?: string | null;
  createdAt: string;
};

type BillingDraft = {
  userId: string;
  subscriptionTier: "free" | "premium";
  subscriptionStatus: "inactive" | "trialing" | "active" | "past_due" | "canceled";
  subscriptionPlanId: string;
  billingProviderCustomerId: string;
  billingProviderSubscriptionId: string;
  billingPeriodEnd: string;
};

type HistoryAnalysisRecord = {
  id: string;
  userId: string;
  resumeId?: string | null;
  jobDescriptionId?: string | null;
  title: string;
  fingerprint?: string | null;
  technicalMatchScore: number;
  fitCategory: string;
  createdAt: string;
  request: AnalyzeRequestPayload;
  response: AnalysisResponse;
  optionalArtifacts?: Record<string, { generatedAt: string }>;
};

type HistoryResumeRecord = {
  id: string;
  title: string;
  createdAt: string;
  source: string;
  rawText: string;
  normalizedText?: string | null;
  structuredResume?: StructuredResume | null;
};

type HistoryJobDescriptionRecord = {
  id: string;
  title: string;
  company?: string | null;
  createdAt: string;
  rawText: string;
  normalizedText?: string | null;
  parsedJobDescription?: ParsedJobDescription | null;
};

type HistoryPreparationRecord = {
  id: string;
  title: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  plan: PreparationIntelligence;
  progress?: PreparationProgress | null;
};

type ComparisonResult = {
  id: string;
  resumeId: string;
  resumeTitle: string;
  jobDescriptionId: string;
  jobTitle: string;
  company?: string | null;
  score: number;
  fitCategory: string;
  recommendedAction?: string | null;
};

type HistoryComparisonRecord = {
  id: string;
  userId: string;
  title: string;
  resumeIds: string[];
  jobDescriptionIds: string[];
  results: ComparisonResult[];
  createdAt: string;
};

type ResearchSource = {
  title: string;
  url?: string | null;
  sourceType: "manual" | "job_post" | "interview_experience" | "company_page" | "market_signal" | "other";
  note?: string | null;
  citationQuality?: "verified_url" | "manual_note" | "weak" | "uncited";
  validationIssues?: string[];
};

type ResearchType = "company" | "role" | "market" | "interview" | "manual";

type ResearchNoteRecord = {
  id: string;
  userId: string;
  title: string;
  company?: string | null;
  roleTitle?: string | null;
  researchType: ResearchType;
  summary: string;
  keySignals: string[];
  preparationTopics: string[];
  sources: ResearchSource[];
  createdAt: string;
  updatedAt: string;
};

type ResearchNoteDraft = Omit<ResearchNoteRecord, "id" | "userId" | "createdAt" | "updatedAt"> & {
  researchProvider?: string;
  providerWarnings?: string[];
  marketOpportunitySignals?: string[];
  roleCompanySynthesis?: string[];
};

type ApplicationDecisionResponse = {
  decision: "apply" | "prepare_first" | "selective_apply" | "skip";
  confidence: "low" | "medium" | "high";
  headline: string;
  reasoning: string[];
  blockers: string[];
  nextActions: string[];
  researchSignalsUsed: string[];
  scoreSignals: Record<string, number | null>;
};

type AgentPlanResponse = {
  phase: string;
  headline: string;
  nextBestAction: string;
  reasoning: string[];
  recommendations: Array<{
    tool: "score" | "research_note" | "preparation_plan" | "resume_rewrite" | "application_decision" | "interview_questions" | "cross_questions" | "gap_report" | "save_progress";
    priority: "critical" | "high" | "medium" | "low";
    reason: string;
    endpoint?: string | null;
    estimatedUnits: number;
    requiresPremium: boolean;
    alreadySatisfied: boolean;
  }>;
  memorySignals: string[];
  guardrails: string[];
};

type ResumeRewriteResponse = {
  summary: string;
  suggestions: Array<{
    targetRequirement: string;
    evidenceSource: string;
    originalEvidence?: string | null;
    currentIssue: string;
    rewrittenBullet: string;
    proofSafety: "safe_from_existing_evidence" | "needs_user_verification" | "gap_do_not_claim";
    reason: string;
  }>;
  warnings: string[];
};
type ResumeRewriteSuggestion = ResumeRewriteResponse["suggestions"][number];

type AcceptedResumeRewriteRecord = {
  id: string;
  userId: string;
  analysisId?: string | null;
  resumeId?: string | null;
  jobDescriptionId?: string | null;
  targetRequirement: string;
  evidenceSource: string;
  proofSafety: "safe_from_existing_evidence" | "needs_user_verification";
  originalEvidence?: string | null;
  currentIssue: string;
  acceptedBullet: string;
  reason: string;
  targetSection: "experience" | "project" | "skills" | "certifications" | "achievements";
  targetLabel?: string | null;
  createdAt: string;
};

type ResumeVersionRecord = {
  id: string;
  userId: string;
  resumeId: string;
  analysisId?: string | null;
  acceptedRewriteId?: string | null;
  title: string;
  changeSummary: string;
  normalizedText: string;
  structuredResume: StructuredResume;
  createdAt: string;
};

type ResumeVersionRestoreRecord = {
  id: string;
  userId: string;
  resumeVersionId: string;
  resumeId: string;
  analysisId?: string | null;
  reason: string;
  createdAt: string;
};

type ResumeVersionComparison = {
  versionId: string;
  title: string;
  summary: string;
  currentCounts: ResumeSnapshotCounts;
  versionCounts: ResumeSnapshotCounts;
  addedInVersion: string[];
  missingFromVersion: string[];
};

type ResumeSnapshotCounts = {
  experience: number;
  projects: number;
  skills: number;
  certifications: number;
  bullets: number;
};

type UsageEventRecord = {
  id: string;
  userId?: string | null;
  module: string;
  mode?: string | null;
  provider?: string | null;
  model?: string | null;
  estimatedUnits: number;
  createdAt: string;
};

type UsageQuotaStatus = {
  userId?: string | null;
  anonymousSessionId?: string | null;
  tier: string;
  window: string;
  windowStartAt: string;
  resetAt: string;
  usedUnits: number;
  limitUnits?: number | null;
  remainingUnits?: number | null;
  unlimited: boolean;
};

type BillingCheckoutResponse = {
  provider: "manual" | "stripe" | "razorpay" | "paddle";
  checkoutUrl?: string | null;
  successUrl?: string | null;
  cancelUrl?: string | null;
  configured: boolean;
  message: string;
};

type DemoSeedResponse = {
  userId: string;
  displayName: string;
  email?: string | null;
  password: string;
  subscriptionTier: "free" | "premium";
  resumeCount: number;
  jobDescriptionCount: number;
  analysisCount: number;
  preparationSessionCount: number;
  jobOpportunityCount: number;
  researchNoteCount: number;
  averageMatchScore?: number | null;
  sessionToken: string;
  message: string;
};

type UsageSummary = {
  totalEvents: number;
  totalEstimatedUnits: number;
  byModule: Record<string, number>;
  byUser: Record<string, number>;
  latestEvents: UsageEventRecord[];
  quota?: UsageQuotaStatus | null;
};

type TaskStatus = "todo" | "in_progress" | "done" | "skipped";
type ConfidenceLevel = "low" | "medium" | "high";

type PreparationProgress = {
  tasks: Record<string, TaskStatus>;
  notes: Record<string, string>;
  confidence: Record<string, ConfidenceLevel>;
};

type PrepMemoryResponse = {
  summary: string;
  repeatedWeakTopics: Array<{
    topic: string;
    occurrences: number;
    averageScore: number;
    latestEvidence?: string | null;
    recommendation: string;
  }>;
  unfinishedPreparation: Array<{
    sessionId: string;
    title: string;
    status: string;
    completionPercent: number;
    unfinishedTaskCount: number;
    lowConfidenceDays: number;
  }>;
  nextRecommendedActions: string[];
  nextAction?: {
    kind: string;
    label: string;
    sessionId?: string | null;
    sessionTitle?: string | null;
    day?: number | null;
    taskId?: string | null;
    task?: string | null;
    reason: string;
  } | null;
};

type JobOpportunityStatus = "viewed" | "shortlisted" | "applied" | "interview" | "rejected" | "offer" | "archived";

type OpportunityNextAction = {
  opportunityId: string;
  title: string;
  company?: string | null;
  currentStatus: JobOpportunityStatus;
  recommendedStatus?: JobOpportunityStatus | null;
  artifactKey?: "resume_improvements" | "interview_questions" | "cross_questions" | null;
  endpoint?: string | null;
  priority: "critical" | "high" | "medium" | "low";
  action: string;
  reason: string;
  score?: number | null;
};

type OpportunityNextActionsResponse = {
  summary: string;
  actions: OpportunityNextAction[];
};

type CommandCenterResponse = {
  summary: string;
  workspace: WorkspaceSummary;
  preparationMemory: PrepMemoryResponse;
  opportunityActions: OpportunityNextActionsResponse;
  topActions: string[];
};

type HistoryJobOpportunityRecord = {
  id: string;
  resumeId?: string | null;
  analysisId?: string | null;
  title: string;
  company?: string | null;
  location?: string | null;
  url?: string | null;
  description: string;
  status: JobOpportunityStatus;
  technicalMatchScore?: number | null;
  fitCategory?: string | null;
  analysisResponse?: AnalysisResponse | null;
  optionalArtifacts?: Record<string, { generatedAt: string }>;
  createdAt: string;
  updatedAt: string;
};

type ExtensionDiagnostics = {
  backendOk: boolean;
  sessionOk: boolean;
  userId?: string | null;
  resumeCount: number;
  canMatchSavedResume: boolean;
  manualPasteRequired: boolean;
  checks: string[];
  warnings: string[];
};

type ExtensionValidationRecord = {
  id: string;
  site: string;
  url?: string | null;
  parserRating: "pass" | "partial" | "fail";
  autoParsed: boolean;
  manualPasteUsed: boolean;
  titleFound: boolean;
  companyFound: boolean;
  descriptionFound: boolean;
  notes?: string | null;
  createdAt: string;
};

type MatchFeedbackSummary = {
  feedbackCount: number;
  accurateCount: number;
  tooHighCount: number;
  tooLowCount: number;
  accuracyRate?: number | null;
  averageScoreByAccuracy: Record<string, number>;
  outcomeCounts: Record<string, number>;
  calibrationRecommendation: string;
  averageAlgorithmScore?: number | null;
  roleFamilyBreakdown: Record<string, {
    feedbackCount: number;
    accurateCount: number;
    tooHighCount: number;
    tooLowCount: number;
    accuracyRate?: number | null;
    averageAlgorithmScore?: number | null;
    calibrationRecommendation: string;
  }>;
  latestFeedback: Array<{
    id: string;
    roleFamily?: string | null;
    expectedFit: string;
    scoreAccuracy: string;
    outcome: string;
    algorithmScore?: number | null;
    fitCategory?: string | null;
    notes?: string | null;
    createdAt: string;
  }>;
};

type MatchFeedbackDataset = {
  userId: string;
  exportedAt: string;
  records: Array<{
    id?: string;
    analysisId?: string | null;
    jobOpportunityId?: string | null;
    roleFamily?: string | null;
    expectedFit: "strong" | "good" | "partial" | "weak";
    scoreAccuracy: "accurate" | "too_high" | "too_low";
    outcome: "not_applied" | "applied" | "shortlisted" | "interview" | "rejected" | "offer" | "no_response";
    algorithmScore?: number | null;
    fitCategory?: string | null;
    notes?: string | null;
  }>;
};

type WorkspaceSummary = {
  resumeCount: number;
  jobDescriptionCount: number;
  analysisCount: number;
  preparationSessionCount: number;
  jobOpportunityCount: number;
  researchNoteCount: number;
  averageMatchScore?: number | null;
  bestMatchScore?: number | null;
  activeOpportunityCount: number;
  interviewOpportunityCount: number;
  offerOpportunityCount: number;
  completedPreparationCount: number;
  pipelineStatusCounts: Record<JobOpportunityStatus, number>;
  applicationToInterviewRate?: number | null;
  interviewToOfferRate?: number | null;
  positiveOutcomeRate?: number | null;
  latestAnalysis?: HistoryAnalysisRecord | null;
};

type StructuredResume = {
  profile: {
    name?: string | null;
    location?: string | null;
    email?: string | null;
    phone?: string | null;
    linkedin?: string | null;
    github?: string | null;
    summary?: string | null;
  };
  experience: Array<{
    title?: string | null;
    company?: string | null;
    duration?: string | null;
    location?: string | null;
    highlights: string[];
  }>;
  projects: Array<{
    name: string;
    duration?: string | null;
    techStack: string[];
    highlights: string[];
  }>;
  skills: string[];
  education: string[];
  achievements: string[];
  certifications: string[];
};

type ParsedJobDescription = {
  roleTitle?: string | null;
  experienceRange: { minYears?: number | null; maxYears?: number | null };
  requiredSkills: string[];
  preferredSkills: string[];
  requiredCertifications: string[];
  emphasizedRequirements: string[];
  responsibilities: string[];
  locations: string[];
  workModes: string[];
  senioritySignals: string[];
};

type ResumeParserDebug = {
  detectedSections: Record<string, number>;
  parsedCounts: Record<string, number>;
  rawLineCount: number;
  parserNotes: string[];
};

type JdParseResponse = {
  normalizedJobDescriptionText: string;
  warnings: string[];
  parsedJobDescription: ParsedJobDescription;
};

const modelOptions: Record<LlmProvider, string[]> = {
  groq: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
  openai: ["gpt-4.1-mini", "gpt-4o-mini"],
  gemini: ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"],
};

const jobOpportunityStatuses: JobOpportunityStatus[] = ["viewed", "shortlisted", "applied", "interview", "rejected", "offer", "archived"];

const defaultResume =
  "3 years .NET fullstack developer at Capgemini. Worked on ASP.NET Core APIs, SQL Server, React UI changes, bug fixes, production support, API integration, and Agile delivery. Familiar with Java, Python, C++, and basic cloud concepts.";

const defaultJd =
  "Looking for a skilled .NET Developer with 2 to 5 years of experience in ASP.NET, .NET Core, C#, Web API, MVC and Azure Cloud Services. Strong knowledge of LINQ, Entity Framework, HTML, CSS, JavaScript, jQuery, Azure DevOps CI/CD pipelines, code compliance and enterprise application development.";

const defaultWorkspaceUserId = "local-aditya";
const workspaceUserStorageKey = "careerAgentWorkspaceUserId";
const sessionTokenStorageKey = "careerAgentSessionToken";
const sessionIssuedAtStorageKey = "careerAgentSessionIssuedAt";
const accountTierStorageKey = "careerAgentAccountTier";
const launchChecklistStorageKey = "careerAgentLaunchChecklist";

const launchChecklistItems = [
  {
    id: "admin_bootstrap",
    title: "Admin bootstrap verified",
    detail: "First admin user can login and Settings admin controls are available.",
  },
  {
    id: "demo_seed",
    title: "Demo workspace seeded",
    detail: "Portfolio demo user has saved resume, JD, score, prep, opportunity, evaluation, and usage records.",
  },
  {
    id: "staging_smoke",
    title: "Staging smoke check passed",
    detail: "Run smoke_check.py against deployed staging API and frontend with a real session token.",
  },
  {
    id: "extension_validation",
    title: "Extension real-site validation done",
    detail: "LinkedIn, Naukri, Indeed, and one company careers page tested with manual JD fallback.",
  },
  {
    id: "backup_export",
    title: "Backup export verified",
    detail: "PostgreSQL JSON backup was generated and reviewed with non-sensitive staging data.",
  },
  {
    id: "live_ai_split",
    title: "Live AI modules tested separately",
    detail: "Score, prep plan, gap report, interview questions, and cross-questions tested one at a time.",
  },
  {
    id: "billing_handoff",
    title: "Billing handoff checked",
    detail: "Checkout config or manual premium unlock path verified in Settings and backend smoke checks.",
  },
  {
    id: "production_readiness",
    title: "Production readiness has no failed checks",
    detail: "Settings readiness panel and diagnostics endpoint are clean for deployment.",
  },
] as const;

function authHeaders(contentType = true): HeadersInit {
  const token = window.localStorage.getItem(sessionTokenStorageKey) || "";
  return {
    ...(contentType ? { "Content-Type": "application/json" } : {}),
    ...(token ? { "X-Session-Token": token } : {}),
  };
}

function storedAccountTier(user: AdminUserRecord): AccessTier {
  return user.subscriptionTier === "premium" ? "premium" : "free";
}

function loadLaunchChecklist(): LaunchChecklistState {
  try {
    const stored = window.localStorage.getItem(launchChecklistStorageKey);
    return stored ? JSON.parse(stored) as LaunchChecklistState : {};
  } catch {
    return {};
  }
}

function App() {
  const [activeTask, setActiveTask] = useState<ActiveTask>("command");
  const [workspaceUserId, setWorkspaceUserId] = useState(() => window.localStorage.getItem(workspaceUserStorageKey) || defaultWorkspaceUserId);
  const [workspaceUserDraft, setWorkspaceUserDraft] = useState(workspaceUserId);
  const [resumeText, setResumeText] = useState(defaultResume);
  const [resumeParseSourceText, setResumeParseSourceText] = useState(defaultResume);
  const [jobDescriptionText, setJobDescriptionText] = useState(defaultJd);
  const [targetRole, setTargetRole] = useState("Full Stack Developer with AI Integration");
  const [experienceYears, setExperienceYears] = useState(3);
  const [preparationPlanDays, setPreparationPlanDays] = useState(7);
  const [currentStack, setCurrentStack] = useState(".NET, React, SQL, Java Spring Boot, Python");
  const [targetMarket, setTargetMarket] = useState("Indian software job market");
  const [currentLocation, setCurrentLocation] = useState("Navi Mumbai");
  const [preferredLocations, setPreferredLocations] = useState("Mumbai, Pune, Bangalore, Remote");
  const [noticePeriodDays, setNoticePeriodDays] = useState(60);
  const [currentCtcLpa, setCurrentCtcLpa] = useState("");
  const [expectedCtcLpa, setExpectedCtcLpa] = useState("");
  const [workModePreference, setWorkModePreference] = useState("hybrid, remote");
  const [relocationOpen, setRelocationOpen] = useState(true);
  const [llmMode, setLlmMode] = useState<LlmMode>("mock");
  const [llmProvider, setLlmProvider] = useState<LlmProvider>("groq");
  const [llmModel, setLlmModel] = useState("llama-3.3-70b-versatile");
  const [scoreStep, setScoreStep] = useState<ScoreStep>("upload");
  const [reviewPane, setReviewPane] = useState<ReviewPane>("resume");
  const [resumeSource, setResumeSource] = useState<ResumeSource>("text");
  const [uploading, setUploading] = useState(false);
  const [jdUploading, setJdUploading] = useState(false);
  const [normalizing, setNormalizing] = useState(false);
  const [parsingJd, setParsingJd] = useState(false);
  const [uploadInfo, setUploadInfo] = useState("");
  const [jdUploadInfo, setJdUploadInfo] = useState("");
  const [normalizeInfo, setNormalizeInfo] = useState("");
  const [jdParseInfo, setJdParseInfo] = useState("");
  const [structuredResume, setStructuredResume] = useState<StructuredResume | null>(null);
  const [resumeParserDebug, setResumeParserDebug] = useState<ResumeParserDebug | null>(null);
  const [parsedJd, setParsedJd] = useState<JdParseResponse["parsedJobDescription"] | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [lastAnalysisRequest, setLastAnalysisRequest] = useState<AnalyzeRequestPayload | null>(null);
  const [lastSavedAnalysisId, setLastSavedAnalysisId] = useState<string | null>(null);
  const [lastSavedResumeId, setLastSavedResumeId] = useState<string | null>(null);
  const [lastSavedJobDescriptionId, setLastSavedJobDescriptionId] = useState<string | null>(null);
  const [lastAnalysisFingerprint, setLastAnalysisFingerprint] = useState<string | null>(null);
  const [activePreparationSession, setActivePreparationSession] = useState<HistoryPreparationRecord | null>(null);
  const [progressSaving, setProgressSaving] = useState(false);
  const [progressInfo, setProgressInfo] = useState("");
  const [prepMemory, setPrepMemory] = useState<PrepMemoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [artifactLoading, setArtifactLoading] = useState("");
  const [costMode, setCostMode] = useState<CostMode>("free");
  const [costModeInfo, setCostModeInfo] = useState("");
  const [accountTier, setAccountTier] = useState<AccessTier>(() => (window.localStorage.getItem(accountTierStorageKey) as AccessTier | null) || "free");
  const [error, setError] = useState("");
  const [preparationInfo, setPreparationInfo] = useState("");
  const [historyInfo, setHistoryInfo] = useState("");
  const [historyLoading, setHistoryLoading] = useState(false);
  const [extensionSetupInfo, setExtensionSetupInfo] = useState("");
  const [extensionChecking, setExtensionChecking] = useState(false);
  const [extensionResumeCount, setExtensionResumeCount] = useState<number | null>(null);
  const [extensionDiagnostics, setExtensionDiagnostics] = useState<ExtensionDiagnostics | null>(null);
  const [extensionValidations, setExtensionValidations] = useState<ExtensionValidationRecord[]>([]);
  const [extensionValidationInfo, setExtensionValidationInfo] = useState("");
  const [evaluationSummary, setEvaluationSummary] = useState<MatchFeedbackSummary | null>(null);
  const [evaluationInfo, setEvaluationInfo] = useState("");
  const [scoringConfigs, setScoringConfigs] = useState<ScoringCalibrationConfig[]>([]);
  const [scoringRecommendation, setScoringRecommendation] = useState<ScoringCalibrationRecommendation | null>(null);
  const [scoringAudit, setScoringAudit] = useState<ScoringCalibrationAuditRecord[]>([]);
  const [systemDiagnostics, setSystemDiagnostics] = useState<SystemDiagnostics | null>(null);
  const [productionReadiness, setProductionReadiness] = useState<ProductionReadiness | null>(null);
  const [commandCenterInfo, setCommandCenterInfo] = useState("");
  const [commandCenterLoading, setCommandCenterLoading] = useState(false);
  const [adminUsers, setAdminUsers] = useState<AdminUserRecord[]>([]);
  const [adminAnalyses, setAdminAnalyses] = useState<HistoryAnalysisRecord[]>([]);
  const [usageSummary, setUsageSummary] = useState<UsageSummary | null>(null);
  const [usageQuota, setUsageQuota] = useState<UsageQuotaStatus | null>(null);
  const [billingDraft, setBillingDraft] = useState<BillingDraft | null>(null);
  const [demoSeedResult, setDemoSeedResult] = useState<DemoSeedResponse | null>(null);
  const [launchChecklist, setLaunchChecklist] = useState<LaunchChecklistState>(() => loadLaunchChecklist());
  const [settingsInfo, setSettingsInfo] = useState("");
  const [sessionInfo, setSessionInfo] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authDisplayName, setAuthDisplayName] = useState(workspaceUserId);
  const [authEmail, setAuthEmail] = useState("");
  const [currentUser, setCurrentUser] = useState<AdminUserRecord | null>(null);
  const [workspaceSummary, setWorkspaceSummary] = useState<WorkspaceSummary | null>(null);
  const [analysisHistory, setAnalysisHistory] = useState<HistoryAnalysisRecord[]>([]);
  const [resumeHistory, setResumeHistory] = useState<HistoryResumeRecord[]>([]);
  const [jdHistory, setJdHistory] = useState<HistoryJobDescriptionRecord[]>([]);
  const [preparationHistory, setPreparationHistory] = useState<HistoryPreparationRecord[]>([]);
  const [jobOpportunityHistory, setJobOpportunityHistory] = useState<HistoryJobOpportunityRecord[]>([]);
  const [opportunityActions, setOpportunityActions] = useState<OpportunityNextActionsResponse | null>(null);
  const [comparisonHistory, setComparisonHistory] = useState<HistoryComparisonRecord[]>([]);
  const [researchNotes, setResearchNotes] = useState<ResearchNoteRecord[]>([]);
  const [researchInfo, setResearchInfo] = useState("");
  const [researchSaving, setResearchSaving] = useState(false);
  const [researchGenerating, setResearchGenerating] = useState(false);
  const [researchTitle, setResearchTitle] = useState("Company and role research note");
  const [researchCompany, setResearchCompany] = useState("");
  const [researchRoleTitle, setResearchRoleTitle] = useState("");
  const [researchType, setResearchType] = useState<ResearchType>("manual");
  const [researchSummary, setResearchSummary] = useState("");
  const [researchKeySignals, setResearchKeySignals] = useState("");
  const [researchPreparationTopics, setResearchPreparationTopics] = useState("");
  const [researchManualContext, setResearchManualContext] = useState("");
  const [researchSourcesDraft, setResearchSourcesDraft] = useState("");
  const [researchDraftProvider, setResearchDraftProvider] = useState("");
  const [researchDraftWarnings, setResearchDraftWarnings] = useState<string[]>([]);
  const [researchDraftMarketSignals, setResearchDraftMarketSignals] = useState<string[]>([]);
  const [researchDraftSynthesis, setResearchDraftSynthesis] = useState<string[]>([]);
  const [agentPlan, setAgentPlan] = useState<AgentPlanResponse | null>(null);
  const [agentInfo, setAgentInfo] = useState("");
  const [agentLoading, setAgentLoading] = useState(false);
  const [applicationDecision, setApplicationDecision] = useState<ApplicationDecisionResponse | null>(null);
  const [decisionInfo, setDecisionInfo] = useState("");
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [resumeRewrite, setResumeRewrite] = useState<ResumeRewriteResponse | null>(null);
  const [appliedRewriteKeys, setAppliedRewriteKeys] = useState<string[]>([]);
  const [acceptedResumeRewrites, setAcceptedResumeRewrites] = useState<AcceptedResumeRewriteRecord[]>([]);
  const [resumeVersions, setResumeVersions] = useState<ResumeVersionRecord[]>([]);
  const [resumeVersionRestores, setResumeVersionRestores] = useState<ResumeVersionRestoreRecord[]>([]);
  const [selectedResumeVersionComparison, setSelectedResumeVersionComparison] = useState<ResumeVersionComparison | null>(null);
  const [rewriteInfo, setRewriteInfo] = useState("");
  const [rewriteLoading, setRewriteLoading] = useState(false);
  const [comparisonResumeIds, setComparisonResumeIds] = useState<string[]>([]);
  const [comparisonJdIds, setComparisonJdIds] = useState<string[]>([]);
  const [comparisonResults, setComparisonResults] = useState<ComparisonResult[]>([]);
  const [activeComparisonId, setActiveComparisonId] = useState<string | null>(null);
  const [comparisonInfo, setComparisonInfo] = useState("");
  const [comparisonLoading, setComparisonLoading] = useState(false);

  useEffect(() => {
    refreshSessionInfo();
    ensureLocalUser().then(() => {
      void loadWorkspaceSummary();
      void loadResumeLibrary();
      void loadJdLibrary();
      void loadCurrentQuota();
    }).catch(() => {
      setHistoryInfo("History is offline until the backend database is available.");
    });
  }, [workspaceUserId]);

  useEffect(() => {
    importResearchDraftFromUrl();
  }, []);

  useEffect(() => {
    if (activeTask === "command") {
      void loadCommandCenter();
    }
    if (activeTask === "history") {
      loadHistory();
    }
    if (activeTask === "compare") {
      void loadResumeLibrary();
      void loadJdLibrary();
      void loadComparisonHistory();
    }
    if (activeTask === "research") {
      void loadResearchNotes();
    }
    if (activeTask === "agent") {
      void loadResearchNotes();
    }
    if (activeTask === "rewrite") {
      void loadAcceptedResumeRewrites();
      void loadResumeVersions();
      void loadResumeVersionRestores();
    }
    if (activeTask === "extension") {
      loadExtensionValidations();
    }
    if (activeTask === "evaluation") {
      loadEvaluationSummary();
    }
    if (activeTask === "settings") {
      loadScoringConfigs();
      loadSystemDiagnostics();
      loadProductionReadiness();
      loadAdminUsers();
      loadAdminAnalyses();
      loadUsageSummary();
    }
  }, [activeTask, workspaceUserId]);

  function buildAnalyzeRequest(): AnalyzeRequestPayload {
    return {
      resumeText: structuredResume ? formatStructuredResume(structuredResume) : resumeText,
      jobDescriptionText: parsedJd ? formatParsedJd(parsedJd) : jobDescriptionText,
      candidateContext: {
        targetRole,
        experienceYears,
        currentStack: currentStack.split(",").map((item) => item.trim()).filter(Boolean),
        targetMarket,
        currentLocation,
        preferredLocations: preferredLocations.split(",").map((item) => item.trim()).filter(Boolean),
        noticePeriodDays,
        currentCtcLpa: currentCtcLpa ? Number(currentCtcLpa) : null,
        expectedCtcLpa: expectedCtcLpa ? Number(expectedCtcLpa) : null,
        workModePreference: workModePreference.split(",").map((item) => item.trim()).filter(Boolean),
        relocationOpen,
      },
      llmOptions: {
        mode: llmMode,
        provider: llmProvider,
        model: llmModel,
      },
      preparationPlanDays,
      scoringCalibrationUserId: workspaceUserId,
      roleFamily: inferRoleFamily(`${targetRole} ${currentStack} ${jobDescriptionText}`),
    };
  }

  function updateResumeDraft(value: string) {
    setResumeText(value);
    setResumeParseSourceText(value);
    setStructuredResume(null);
    setResumeParserDebug(null);
    setNormalizeInfo("");
    setResult(null);
  }

  function updateJdDraft(value: string) {
    setJobDescriptionText(value);
    setParsedJd(null);
    setJdParseInfo("");
    setResult(null);
  }

  function goToScoreStep(step: ScoreStep) {
    if (step === "review" && (!structuredResume || !parsedJd)) {
      setError("Parse the resume and JD before opening review.");
      return;
    }
    if (step === "score" && (!structuredResume || !parsedJd)) {
      setError("Review the parsed resume and JD before calculating the score.");
      return;
    }
    setError("");
    setScoreStep(step);
  }

  async function ensureLocalUser() {
    const response = await fetch(`${API_BASE_URL}/auth/session/claim`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: workspaceUserId,
        displayName: workspaceUserId,
        email: null,
        role: "admin",
      }),
    });
    if (response.ok) {
      const payload = await response.json() as { user: AdminUserRecord; sessionToken: string };
      window.localStorage.setItem(sessionTokenStorageKey, payload.sessionToken);
      window.localStorage.setItem(sessionIssuedAtStorageKey, new Date().toISOString());
      setCurrentUser(payload.user);
      setAuthDisplayName(payload.user.displayName);
      setAuthEmail(payload.user.email ?? "");
      setAccountTier(storedAccountTier(payload.user));
      window.localStorage.setItem(accountTierStorageKey, storedAccountTier(payload.user));
      refreshSessionInfo();
    } else if (response.status === 401 || response.status === 403) {
      clearStoredSession("Saved session was invalid. Reconnect to continue.");
      throw new Error("Session was invalid. Reconnect to continue.");
    } else {
      throw new Error("Session claim failed");
    }
  }

  function refreshSessionInfo() {
    const token = window.localStorage.getItem(sessionTokenStorageKey) || "";
    const issuedAt = window.localStorage.getItem(sessionIssuedAtStorageKey);
    setSessionInfo(token ? `Session active${issuedAt ? ` since ${formatDate(issuedAt)}` : ""}` : "No saved session token");
  }

  async function reconnectSession() {
    setSessionInfo("Refreshing session...");
    try {
      await ensureLocalUser();
    } catch (err) {
      setSessionInfo(err instanceof Error ? err.message : "Session refresh failed");
    }
  }

  function clearStoredSession(message = "Session cleared. Reconnect before guarded actions.") {
    window.localStorage.removeItem(sessionTokenStorageKey);
    window.localStorage.removeItem(sessionIssuedAtStorageKey);
    setCurrentUser(null);
    setSessionInfo(message);
  }

  function importResearchDraftFromUrl() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("task") !== "research") return;
    const encoded = params.get("researchDraft");
    if (!encoded) {
      setActiveTask("research");
      return;
    }
    try {
      const payload = decodeResearchHandoff(encoded);
      const title = payload.title || "Imported job research";
      const company = payload.company || "";
      const description = payload.description || "";
      const sourceUrl = payload.url || "";
      setActiveTask("research");
      setResearchTitle(`${company ? `${company} ` : ""}${title} research signals`.slice(0, 180));
      setResearchCompany(company);
      setResearchRoleTitle(title);
      setResearchType("role");
      setResearchSummary(
        `Imported from browser extension for ${title}${company ? ` at ${company}` : ""}. Review the JD text and generate or save a research note for preparation planning.`
      );
      setResearchManualContext(description);
      setResearchKeySignals([
        "Imported from browser extension job page.",
        sourceUrl ? "Original job source URL is attached." : "No source URL was available.",
        payload.location ? `Location signal: ${payload.location}` : "",
      ].filter(Boolean).join("\n"));
      setResearchPreparationTopics(["Role-specific JD emphasis", "Company-specific interview preparation"].join("\n"));
      setResearchSourcesDraft(sourceUrl ? `Job page | ${sourceUrl} | job_post | Imported from browser extension` : "");
      setResearchInfo("Imported job page into Research Notes from the browser extension.");
      window.history.replaceState({}, document.title, window.location.pathname);
    } catch {
      setActiveTask("research");
      setResearchInfo("Could not import the extension research payload.");
    }
  }

  function applyWorkspaceUser() {
    const nextUserId = workspaceUserDraft.trim();
    if (nextUserId.length < 2) {
      setSessionInfo("Workspace user id must be at least 2 characters.");
      return;
    }
    if (nextUserId === workspaceUserId) {
      void reconnectSession();
      return;
    }
    window.localStorage.setItem(workspaceUserStorageKey, nextUserId);
    clearStoredSession("Workspace user changed. Refresh session to connect.");
    setWorkspaceUserId(nextUserId);
    setWorkspaceUserDraft(nextUserId);
    setAuthDisplayName(nextUserId);
    setWorkspaceSummary(null);
    setAnalysisHistory([]);
    setResumeHistory([]);
    setJdHistory([]);
    setPreparationHistory([]);
    setJobOpportunityHistory([]);
    setOpportunityActions(null);
    setComparisonHistory([]);
    setResearchNotes([]);
    setActiveComparisonId(null);
    setExtensionValidations([]);
    setEvaluationSummary(null);
    setScoringConfigs([]);
    setScoringRecommendation(null);
    setScoringAudit([]);
    setSystemDiagnostics(null);
    setProductionReadiness(null);
    setAdminUsers([]);
    setAdminAnalyses([]);
    setUsageSummary(null);
  }

  function applyAuthenticatedSession(payload: { user: AdminUserRecord; sessionToken: string }, message: string) {
    window.localStorage.setItem(workspaceUserStorageKey, payload.user.id);
    window.localStorage.setItem(sessionTokenStorageKey, payload.sessionToken);
    window.localStorage.setItem(sessionIssuedAtStorageKey, new Date().toISOString());
    setWorkspaceUserId(payload.user.id);
    setWorkspaceUserDraft(payload.user.id);
    setCurrentUser(payload.user);
    setAuthDisplayName(payload.user.displayName);
    setAuthEmail(payload.user.email ?? "");
    setAccountTier(storedAccountTier(payload.user));
    window.localStorage.setItem(accountTierStorageKey, storedAccountTier(payload.user));
    setAuthPassword("");
    setSessionInfo(message);
  }

  async function updateAccountTier(nextTier: AccessTier) {
    if (nextTier === "admin") return;
    setAccountTier(nextTier);
    window.localStorage.setItem(accountTierStorageKey, nextTier);
    if (nextTier === "free") {
      setCostMode("free");
      setCostModeInfo("Free tier keeps AI usage to the score and requirement matrix.");
    } else {
      setCostModeInfo("Premium tier unlocked for optional coaching modules in this workspace.");
    }
    if (!workspaceUserId) return;
    try {
      const response = await fetch(`${API_BASE_URL}/auth/users/${workspaceUserId}/subscription-tier`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify({ subscriptionTier: nextTier }),
      });
      if (response.ok) {
        const user = await response.json() as AdminUserRecord;
        setCurrentUser(user);
      }
    } catch {
      // Local tier still controls UI if the backend is offline.
    }
  }

  async function startCheckoutUpgrade() {
    try {
      await ensureLocalUser();
      const params = new URLSearchParams({ userId: workspaceUserId });
      const response = await fetch(`${API_BASE_URL}/billing/checkout?${params.toString()}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error(await readApiError(response, "Checkout unavailable"));
      const checkout = await response.json() as BillingCheckoutResponse;
      if (checkout.configured && checkout.checkoutUrl) {
        window.open(checkout.checkoutUrl, "_blank", "noopener,noreferrer");
        setCostModeInfo(checkout.message);
        return;
      }
      await updateAccountTier("premium");
      setCostModeInfo(`${checkout.message} Local Premium access is enabled for this workspace.`);
    } catch (error) {
      await updateAccountTier("premium");
      setCostModeInfo(error instanceof Error ? `${error.message} Local Premium access is enabled for this workspace.` : "Checkout unavailable. Local Premium access is enabled for this workspace.");
    }
  }

  async function registerWithPassword() {
    if (workspaceUserDraft.trim().length < 2) {
      setSessionInfo("Workspace user id must be at least 2 characters.");
      return;
    }
    if (authPassword.length < 8) {
      setSessionInfo("Password must be at least 8 characters.");
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: workspaceUserDraft.trim(),
          displayName: authDisplayName.trim() || workspaceUserDraft.trim(),
          email: authEmail.trim() || null,
          password: authPassword,
          role: "admin",
          subscriptionTier: accountTier === "premium" ? "premium" : "free",
        }),
      });
      if (!response.ok) {
        setSessionInfo("Password registration failed.");
        return;
      }
      applyAuthenticatedSession(await response.json() as { user: AdminUserRecord; sessionToken: string }, "Password session active.");
    } catch (error) {
      setSessionInfo(error instanceof Error ? error.message : "Password registration failed.");
    }
  }

  async function loginWithPassword() {
    if (workspaceUserDraft.trim().length < 2 || authPassword.length < 8) {
      setSessionInfo("Enter user id/email and password.");
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          userIdOrEmail: workspaceUserDraft.trim(),
          password: authPassword,
        }),
      });
      if (!response.ok) {
        clearStoredSession("Login failed. Check user id/email and password.");
        return;
      }
      applyAuthenticatedSession(await response.json() as { user: AdminUserRecord; sessionToken: string }, "Password login active.");
    } catch (error) {
      clearStoredSession(error instanceof Error ? error.message : "Login failed. Check user id/email and password.");
    }
  }

  async function lookupSavedAnalysis(fingerprint: string): Promise<HistoryAnalysisRecord | null> {
    await ensureLocalUser();
    const response = await fetch(`${API_BASE_URL}/history/analyses/lookup`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: workspaceUserId,
        fingerprint,
      }),
    });
    if (!response.ok) throw new Error("Saved score lookup failed");
    return await response.json() as HistoryAnalysisRecord | null;
  }

  async function saveHistorySnapshot(payload: AnalyzeRequestPayload, analysis: AnalysisResponse, fingerprint: string) {
    await ensureLocalUser();

    const resumeResponse = await fetch(`${API_BASE_URL}/history/resumes`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: workspaceUserId,
        title: `${payload.candidateContext.targetRole} resume snapshot`,
        source: resumeSource,
        rawText: payload.resumeText,
        normalizedText: structuredResume ? formatStructuredResume(structuredResume) : payload.resumeText,
        structuredResume,
      }),
    });
    if (!resumeResponse.ok) throw new Error("Resume history save failed");
    const resumeRecord = await resumeResponse.json() as HistoryResumeRecord;

    const jdResponse = await fetch(`${API_BASE_URL}/history/job-descriptions`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: workspaceUserId,
        title: parsedJd?.roleTitle || payload.candidateContext.targetRole,
        company: null,
        rawText: payload.jobDescriptionText,
        normalizedText: parsedJd ? formatParsedJd(parsedJd) : payload.jobDescriptionText,
        parsedJobDescription: parsedJd,
      }),
    });
    if (!jdResponse.ok) throw new Error("JD history save failed");
    const jdRecord = await jdResponse.json() as HistoryJobDescriptionRecord;

    const analysisResponse = await fetch(`${API_BASE_URL}/history/analyses`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: workspaceUserId,
        title: `${payload.candidateContext.targetRole} - ${analysis.technicalMatchScore}%`,
        resumeId: resumeRecord.id,
        jobDescriptionId: jdRecord.id,
        fingerprint,
        request: payload,
        response: analysis,
      }),
    });
    if (!analysisResponse.ok) throw new Error("Analysis history save failed");
    return await analysisResponse.json() as HistoryAnalysisRecord;
  }

  async function savePreparationSession(preparation: PreparationIntelligence) {
    await ensureLocalUser();
    const response = await fetch(`${API_BASE_URL}/history/preparation-sessions`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: workspaceUserId,
        analysisId: lastSavedAnalysisId,
        title: `${preparation.dailyPlan.length}-day preparation plan`,
        status: "planned",
        plan: preparation,
        progress: createInitialProgress(preparation),
      }),
    });
    if (!response.ok) throw new Error("Preparation history save failed");
    return await response.json() as HistoryPreparationRecord;
  }

  async function loadHistory() {
    setHistoryLoading(true);
    setHistoryInfo("");
    try {
      await ensureLocalUser();
      const getOptions = { headers: authHeaders(false) };
      const [workspaceResponse, analysesResponse, resumesResponse, jdsResponse, preparationsResponse, opportunitiesResponse, opportunityActionsResponse, comparisonsResponse, researchResponse, rewritesResponse, versionsResponse, restoresResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/workspace`, getOptions),
        fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/analyses`, getOptions),
        fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/resumes`, getOptions),
        fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/job-descriptions`, getOptions),
        fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/preparation-sessions`, getOptions),
        fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/job-opportunities`, getOptions),
        fetch(`${API_BASE_URL}/ai/opportunities/next-actions/${workspaceUserId}`, getOptions),
        fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/comparisons`, getOptions),
        fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/research-notes`, getOptions),
        fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/accepted-resume-rewrites`, getOptions),
        fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/resume-versions`, getOptions),
        fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/resume-version-restores`, getOptions),
      ]);

      if (!workspaceResponse.ok || !analysesResponse.ok || !resumesResponse.ok || !jdsResponse.ok || !preparationsResponse.ok || !opportunitiesResponse.ok || !opportunityActionsResponse.ok || !comparisonsResponse.ok || !researchResponse.ok || !rewritesResponse.ok || !versionsResponse.ok || !restoresResponse.ok) {
        throw new Error("History load failed");
      }

      setWorkspaceSummary(await workspaceResponse.json() as WorkspaceSummary);
      setAnalysisHistory(await analysesResponse.json() as HistoryAnalysisRecord[]);
      setResumeHistory(await resumesResponse.json() as HistoryResumeRecord[]);
      setJdHistory(await jdsResponse.json() as HistoryJobDescriptionRecord[]);
      const savedPreparations = await preparationsResponse.json() as HistoryPreparationRecord[];
      setPreparationHistory(savedPreparations);
      if (!activePreparationSession && savedPreparations.length) {
        setActivePreparationSession(savedPreparations[0]);
      }
      setJobOpportunityHistory(await opportunitiesResponse.json() as HistoryJobOpportunityRecord[]);
      setOpportunityActions(await opportunityActionsResponse.json() as OpportunityNextActionsResponse);
      setComparisonHistory(await comparisonsResponse.json() as HistoryComparisonRecord[]);
      setResearchNotes(await researchResponse.json() as ResearchNoteRecord[]);
      setAcceptedResumeRewrites(await rewritesResponse.json() as AcceptedResumeRewriteRecord[]);
      setResumeVersions(await versionsResponse.json() as ResumeVersionRecord[]);
      setResumeVersionRestores(await restoresResponse.json() as ResumeVersionRestoreRecord[]);
      setHistoryInfo("Loaded saved PostgreSQL history.");
      void loadPrepMemory();
    } catch (err) {
      setHistoryInfo(err instanceof Error ? err.message : "History load failed");
    } finally {
      setHistoryLoading(false);
    }
  }

  async function loadWorkspaceSummary() {
    try {
      const response = await fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/workspace`, { headers: authHeaders(false) });
      if (response.ok) {
        setWorkspaceSummary(await response.json() as WorkspaceSummary);
      }
    } catch {
      // Full history loading surfaces detailed errors. Profile counts can quietly stay empty.
    }
  }

  async function loadCommandCenter() {
    setCommandCenterLoading(true);
    setCommandCenterInfo("");
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/ai/command-center/${workspaceUserId}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error(await readApiError(response, "Command Center refresh failed"));
      const payload = await response.json() as CommandCenterResponse;
      setWorkspaceSummary(payload.workspace);
      setPrepMemory(payload.preparationMemory);
      setOpportunityActions(payload.opportunityActions);
      setCommandCenterInfo(payload.summary);
    } catch (err) {
      setCommandCenterInfo(err instanceof Error ? err.message : "Command Center refresh failed");
    } finally {
      setCommandCenterLoading(false);
    }
  }

  async function loadResumeLibrary() {
    try {
      const response = await fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/resumes`, { headers: authHeaders(false) });
      if (response.ok) {
        setResumeHistory(await response.json() as HistoryResumeRecord[]);
      }
    } catch {
      // The upload step can still use pasted resumes if saved resume loading is unavailable.
    }
  }

  async function loadJdLibrary() {
    try {
      const response = await fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/job-descriptions`, { headers: authHeaders(false) });
      if (response.ok) {
        setJdHistory(await response.json() as HistoryJobDescriptionRecord[]);
      }
    } catch {
      // The upload step can still use pasted JDs if saved JD loading is unavailable.
    }
  }

  async function loadComparisonHistory() {
    try {
      const response = await fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/comparisons`, { headers: authHeaders(false) });
      if (response.ok) {
        setComparisonHistory(await response.json() as HistoryComparisonRecord[]);
      }
    } catch {
      // Comparison can still run without saved batches.
    }
  }

  async function loadResearchNotes() {
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/research-notes`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error(await readApiError(response, "Research notes load failed"));
      setResearchNotes(await response.json() as ResearchNoteRecord[]);
      setResearchInfo("Loaded saved research notes.");
    } catch (err) {
      setResearchInfo(err instanceof Error ? err.message : "Research notes load failed");
    }
  }

  async function loadAcceptedResumeRewrites() {
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/accepted-resume-rewrites`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error(await readApiError(response, "Accepted rewrite history load failed"));
      setAcceptedResumeRewrites(await response.json() as AcceptedResumeRewriteRecord[]);
    } catch (err) {
      setRewriteInfo(err instanceof Error ? err.message : "Accepted rewrite history load failed");
    }
  }

  async function loadResumeVersions() {
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/resume-versions`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error(await readApiError(response, "Resume version history load failed"));
      setResumeVersions(await response.json() as ResumeVersionRecord[]);
    } catch (err) {
      setRewriteInfo(err instanceof Error ? err.message : "Resume version history load failed");
    }
  }

  async function loadResumeVersionRestores() {
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/resume-version-restores`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error(await readApiError(response, "Resume restore history load failed"));
      setResumeVersionRestores(await response.json() as ResumeVersionRestoreRecord[]);
    } catch (err) {
      setRewriteInfo(err instanceof Error ? err.message : "Resume restore history load failed");
    }
  }

  async function saveResearchNote() {
    const title = researchTitle.trim();
    const summary = researchSummary.trim();
    if (title.length < 2 || summary.length < 10) {
      setResearchInfo("Add a title and a summary of at least 10 characters.");
      return;
    }
    setResearchSaving(true);
    setResearchInfo("");
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/history/research-notes`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: workspaceUserId,
          title,
          company: researchCompany.trim() || null,
          roleTitle: researchRoleTitle.trim() || null,
          researchType,
          summary,
          keySignals: splitLines(researchKeySignals),
          preparationTopics: splitLines(researchPreparationTopics),
          sources: parseResearchSources(researchSourcesDraft),
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Research note save failed"));
      const saved = await response.json() as ResearchNoteRecord;
      setResearchNotes((items) => [saved, ...items.filter((item) => item.id !== saved.id)]);
      setResearchInfo("Research note saved to workspace memory.");
      setResearchSummary("");
      setResearchKeySignals("");
      setResearchPreparationTopics("");
      setResearchSourcesDraft("");
      setResearchDraftProvider("");
      setResearchDraftWarnings([]);
      setResearchDraftMarketSignals([]);
      setResearchDraftSynthesis([]);
      void loadWorkspaceSummary();
    } catch (err) {
      setResearchInfo(err instanceof Error ? err.message : "Research note save failed");
    } finally {
      setResearchSaving(false);
    }
  }

  async function generateResearchDraft() {
    if (!result || !lastAnalysisRequest) {
      setResearchInfo("Run resume matching before generating a research draft.");
      return;
    }
    if (!canUsePremium) {
      setResearchInfo("Premium access is required for generated research notes. Manual notes can still be saved.");
      return;
    }
    setResearchGenerating(true);
    setResearchInfo("");
    try {
      const response = await fetch(`${API_BASE_URL}/ai/research/note-draft`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          sourceRequest: lastAnalysisRequest,
          analysis: result,
          company: researchCompany.trim() || null,
          roleTitle: researchRoleTitle.trim() || targetRole,
          researchType,
          manualContext: researchManualContext.trim() || null,
          sourceUrls: splitLines(researchSourcesDraft)
            .map((line) => line.split("|")[1]?.trim() || line.trim())
            .filter((value) => value.startsWith("http")),
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Research draft generation failed"));
      applyResearchDraft(await response.json() as ResearchNoteDraft);
      void loadCurrentQuota();
    } catch (err) {
      setResearchInfo(err instanceof Error ? err.message : "Research draft generation failed");
    } finally {
      setResearchGenerating(false);
    }
  }

  function applyResearchDraft(draft: ResearchNoteDraft) {
    setResearchTitle(draft.title);
    setResearchCompany(draft.company ?? "");
    setResearchRoleTitle(draft.roleTitle ?? "");
    setResearchType((["company", "role", "market", "interview", "manual"].includes(draft.researchType) ? draft.researchType : "role") as ResearchType);
    setResearchSummary(draft.summary);
    setResearchKeySignals(draft.keySignals.join("\n"));
    setResearchPreparationTopics(draft.preparationTopics.join("\n"));
    setResearchSourcesDraft(formatResearchSources(draft.sources));
    setResearchDraftProvider(draft.researchProvider ?? "local");
    setResearchDraftWarnings(draft.providerWarnings ?? []);
    setResearchDraftMarketSignals(draft.marketOpportunitySignals ?? []);
    setResearchDraftSynthesis(draft.roleCompanySynthesis ?? []);
    const citedCount = draft.sources.filter((source) => source.citationQuality === "verified_url").length;
    const providerLabel = formatCategory(draft.researchProvider ?? "local");
    setResearchInfo(`Generated a ${providerLabel} research draft with ${citedCount} verified citation(s). Review it before saving.`);
  }

  function currentGeneratedArtifacts(currentResult: AnalysisResponse | null): string[] {
    if (!currentResult) return [];
    return [
      currentResult.resumeImprovements.length > 0 ? "resume_improvements" : "",
      currentResult.interviewQuestions.length > 0 ? "interview_questions" : "",
      currentResult.crossQuestions.length > 0 ? "cross_questions" : "",
      currentResult.preparationIntelligence || activePreparationSession ? "preparation_plan" : "",
      applicationDecision ? "application_decision" : "",
      resumeRewrite ? "resume_rewrite" : "",
    ].filter(Boolean);
  }

  async function buildAgentPlan() {
    if (!result || !lastAnalysisRequest) {
      setAgentInfo("Run resume matching before building the career agent plan.");
      return;
    }
    setAgentLoading(true);
    setAgentInfo("");
    try {
      const response = await fetch(`${API_BASE_URL}/ai/agent/plan`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          sourceRequest: lastAnalysisRequest,
          analysis: result,
          researchNotes: researchNotes.map(toResearchContextNote),
          preparation: result.preparationIntelligence ?? activePreparationSession?.plan ?? null,
          generatedArtifacts: currentGeneratedArtifacts(result),
          company: researchCompany.trim() || null,
          roleTitle: researchRoleTitle.trim() || targetRole,
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Career agent planning failed"));
      setAgentPlan(await response.json() as AgentPlanResponse);
      setAgentInfo("Career agent plan updated from the latest score, memory, and artifact state.");
      void loadCurrentQuota();
    } catch (err) {
      setAgentInfo(err instanceof Error ? err.message : "Career agent planning failed");
    } finally {
      setAgentLoading(false);
    }
  }

  function runAgentRecommendation(tool: AgentPlanResponse["recommendations"][number]["tool"]) {
    if (tool === "score") {
      setActiveTask("matching");
      return;
    }
    if (tool === "research_note") {
      setActiveTask("research");
      return;
    }
    if (tool === "preparation_plan") {
      setActiveTask("preparation");
      void buildPreparation();
      return;
    }
    if (tool === "resume_rewrite") {
      setActiveTask("rewrite");
      void buildResumeRewrite();
      return;
    }
    if (tool === "application_decision") {
      setActiveTask("decision");
      void buildApplicationDecision();
      return;
    }
    if (tool === "interview_questions") {
      setActiveTask("report");
      void buildOptionalArtifact(
        "Interview questions",
        "interview_questions",
        "/ai/interview/questions",
        (current, payload) => ({ ...current, interviewQuestions: payload as AnalysisResponse["interviewQuestions"] }),
      );
      return;
    }
    if (tool === "cross_questions") {
      setActiveTask("report");
      void buildOptionalArtifact(
        "Cross questions",
        "cross_questions",
        "/ai/cross-questions",
        (current, payload) => ({ ...current, crossQuestions: payload as AnalysisResponse["crossQuestions"] }),
      );
      return;
    }
    if (tool === "gap_report") {
      setActiveTask("report");
      return;
    }
    if (tool === "save_progress") {
      setActiveTask("progress");
    }
  }

  async function buildApplicationDecision() {
    if (!result || !lastAnalysisRequest) {
      setDecisionInfo("Run resume matching before building an application decision.");
      return;
    }
    if (!canUsePremium) {
      setDecisionInfo("Premium access is required for application decisioning.");
      return;
    }
    setDecisionLoading(true);
    setDecisionInfo("");
    try {
      const response = await fetch(`${API_BASE_URL}/ai/application-decision`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          sourceRequest: lastAnalysisRequest,
          analysis: result,
          researchNotes: researchNotes.map(toResearchContextNote),
          company: researchCompany.trim() || null,
          roleTitle: researchRoleTitle.trim() || targetRole,
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Application decision failed"));
      setApplicationDecision(await response.json() as ApplicationDecisionResponse);
      setDecisionInfo("Decision built from current score and saved research notes.");
      void loadCurrentQuota();
    } catch (err) {
      setDecisionInfo(err instanceof Error ? err.message : "Application decision failed");
    } finally {
      setDecisionLoading(false);
    }
  }

  async function buildResumeRewrite() {
    if (!result || !lastAnalysisRequest) {
      setRewriteInfo("Run resume matching before building rewrite suggestions.");
      return;
    }
    if (!canUsePremium) {
      setRewriteInfo("Premium access is required for evidence-constrained resume rewrite.");
      return;
    }
    setRewriteLoading(true);
    setRewriteInfo("");
    try {
      const response = await fetch(`${API_BASE_URL}/ai/resume/rewrite`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          sourceRequest: lastAnalysisRequest,
          analysis: result,
          resumeText: structuredResume ? formatStructuredResume(structuredResume) : resumeText,
          limit: 10,
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Resume rewrite failed"));
      setResumeRewrite(await response.json() as ResumeRewriteResponse);
      setAppliedRewriteKeys([]);
      setRewriteInfo("Rewrite suggestions generated with evidence safety labels.");
      void loadCurrentQuota();
    } catch (err) {
      setRewriteInfo(err instanceof Error ? err.message : "Resume rewrite failed");
    } finally {
      setRewriteLoading(false);
    }
  }

  async function saveAcceptedResumeRewrite(item: ResumeRewriteSuggestion, bullet: string, targetSection: AcceptedResumeRewriteRecord["targetSection"], targetLabel: string | null) {
    await ensureLocalUser();
    const response = await fetch(`${API_BASE_URL}/history/accepted-resume-rewrites`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: workspaceUserId,
        analysisId: lastSavedAnalysisId,
        resumeId: lastSavedResumeId,
        jobDescriptionId: lastSavedJobDescriptionId,
        targetRequirement: item.targetRequirement,
        evidenceSource: item.evidenceSource,
        proofSafety: item.proofSafety,
        originalEvidence: item.originalEvidence || null,
        currentIssue: item.currentIssue,
        acceptedBullet: bullet,
        reason: item.reason,
        targetSection,
        targetLabel,
      }),
    });
    if (!response.ok) throw new Error(await readApiError(response, "Accepted rewrite audit save failed"));
    const saved = await response.json() as AcceptedResumeRewriteRecord;
    setAcceptedResumeRewrites((records) => [saved, ...records.filter((record) => record.id !== saved.id)].slice(0, 100));
    return saved;
  }

  async function saveResumeVersionSnapshot(
    item: ResumeRewriteSuggestion,
    nextResume: StructuredResume,
    acceptedRewrite: AcceptedResumeRewriteRecord | null,
    targetLabel: string,
  ) {
    if (!lastSavedResumeId) {
      throw new Error("No saved resume snapshot is linked to this score yet.");
    }
    const normalizedText = formatStructuredResume(nextResume);
    const response = await fetch(`${API_BASE_URL}/history/resume-versions`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: workspaceUserId,
        resumeId: lastSavedResumeId,
        analysisId: lastSavedAnalysisId,
        acceptedRewriteId: acceptedRewrite?.id ?? null,
        title: `Rewrite version - ${item.targetRequirement}`.slice(0, 180),
        changeSummary: `Applied ${formatCategory(item.proofSafety)} rewrite to ${targetLabel}.`,
        normalizedText,
        structuredResume: nextResume,
      }),
    });
    if (!response.ok) throw new Error(await readApiError(response, "Resume version save failed"));
    const saved = await response.json() as ResumeVersionRecord;
    setResumeVersions((records) => [saved, ...records.filter((record) => record.id !== saved.id)].slice(0, 100));
    return saved;
  }

  async function applyRewriteSuggestion(item: ResumeRewriteSuggestion, index: number) {
    const rewriteKey = rewriteSuggestionKey(item, index);
    if (item.proofSafety === "gap_do_not_claim") {
      setRewriteInfo("Gap-only suggestions are not applied to the resume because there is no existing proof to support the claim.");
      return;
    }
    if (appliedRewriteKeys.includes(rewriteKey)) {
      setRewriteInfo("This rewrite suggestion is already applied to the resume draft.");
      return;
    }
    if (!structuredResume) {
      setRewriteInfo("Parse and review the resume first, then apply rewrite suggestions to the structured draft.");
      setScoreStep("review");
      setReviewPane("resume");
      return;
    }

    const bullet = cleanResumeBullet(item.rewrittenBullet);
    if (!bullet) {
      setRewriteInfo("This rewrite suggestion has no bullet text to apply.");
      return;
    }

    const nextResume: StructuredResume = {
      ...structuredResume,
      profile: { ...structuredResume.profile },
      experience: structuredResume.experience.map((entry) => ({ ...entry, highlights: [...entry.highlights] })),
      projects: structuredResume.projects.map((project) => ({ ...project, techStack: [...project.techStack], highlights: [...project.highlights] })),
      skills: [...structuredResume.skills],
      education: [...structuredResume.education],
      achievements: [...structuredResume.achievements],
      certifications: [...structuredResume.certifications],
    };
    const source = item.evidenceSource.toLowerCase();
    let targetLabel = "achievements";
    let targetSection: AcceptedResumeRewriteRecord["targetSection"] = "achievements";

    if (source.includes("project") && nextResume.projects.length > 0) {
      addUniqueLine(nextResume.projects[0].highlights, bullet);
      targetLabel = `project: ${nextResume.projects[0].name}`;
      targetSection = "project";
    } else if (source.includes("experience") && nextResume.experience.length > 0) {
      addUniqueLine(nextResume.experience[0].highlights, bullet);
      targetLabel = `experience: ${nextResume.experience[0].title || nextResume.experience[0].company || "latest role"}`;
      targetSection = "experience";
    } else if (source.includes("certification")) {
      addUniqueLine(nextResume.certifications, bullet);
      targetLabel = "certifications";
      targetSection = "certifications";
    } else if (source.includes("skill")) {
      addUniqueLine(nextResume.skills, bullet);
      targetLabel = "skills";
      targetSection = "skills";
    } else if (nextResume.projects.length > 0) {
      addUniqueLine(nextResume.projects[0].highlights, bullet);
      targetLabel = `project: ${nextResume.projects[0].name}`;
      targetSection = "project";
    } else if (nextResume.experience.length > 0) {
      addUniqueLine(nextResume.experience[0].highlights, bullet);
      targetLabel = `experience: ${nextResume.experience[0].title || nextResume.experience[0].company || "latest role"}`;
      targetSection = "experience";
    } else {
      addUniqueLine(nextResume.achievements, bullet);
    }

    setStructuredResume(nextResume);
    setResumeText(formatStructuredResume(nextResume));
    setAppliedRewriteKeys((keys) => [...keys, rewriteKey]);
    setReviewPane("resume");
    setScoreStep("review");
    setActiveTask("matching");
    try {
      const acceptedRewrite = await saveAcceptedResumeRewrite(item, bullet, targetSection, targetLabel);
      await saveResumeVersionSnapshot(item, nextResume, acceptedRewrite, targetLabel);
      setRewriteInfo(`Applied rewrite suggestion to ${targetLabel}, saved the audit, and captured a resume version snapshot. Review before scoring again.`);
    } catch (err) {
      setRewriteInfo(`Applied rewrite suggestion to ${targetLabel}, but history save was incomplete: ${err instanceof Error ? err.message : "unknown error"}`);
    }
  }

  function compareResumeVersion(version: ResumeVersionRecord) {
    if (!structuredResume) {
      setRewriteInfo("Parse or load a structured resume before comparing a saved version.");
      setScoreStep("review");
      setReviewPane("resume");
      return;
    }
    const comparison = buildResumeVersionComparison(structuredResume, version);
    setSelectedResumeVersionComparison(comparison);
    setRewriteInfo(`Compared current draft with ${version.title}.`);
  }

  function restoreResumeVersion(version: ResumeVersionRecord) {
    const restoredResume = cloneStructuredResume(version.structuredResume);
    setStructuredResume(restoredResume);
    setResumeText(formatStructuredResume(restoredResume));
    setReviewPane("resume");
    setScoreStep("review");
    setActiveTask("matching");
    setSelectedResumeVersionComparison(buildResumeVersionComparison(restoredResume, version));
    void saveResumeVersionRestoreAudit(version);
    setRewriteInfo(`Restored ${version.title} into the resume review editor. Re-score after reviewing the draft.`);
  }

  async function saveResumeVersionRestoreAudit(version: ResumeVersionRecord) {
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/history/resume-version-restores`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: workspaceUserId,
          resumeVersionId: version.id,
          resumeId: version.resumeId,
          analysisId: lastSavedAnalysisId || version.analysisId || null,
          reason: `Restored ${version.title} into the structured resume editor.`,
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Resume restore audit save failed"));
      const saved = await response.json() as ResumeVersionRestoreRecord;
      setResumeVersionRestores((records) => [saved, ...records.filter((record) => record.id !== saved.id)].slice(0, 100));
      setRewriteInfo(`Restored ${version.title} and saved a restore audit event.`);
    } catch (err) {
      setRewriteInfo(`Restored ${version.title}, but restore audit save failed: ${err instanceof Error ? err.message : "unknown error"}`);
    }
  }

  function useSavedResume(resume: HistoryResumeRecord) {
    const nextText = resume.normalizedText || resume.rawText;
    setResumeText(nextText);
    setResumeParseSourceText(resume.rawText);
    setStructuredResume(resume.structuredResume ?? null);
    setResumeParserDebug(null);
    setNormalizeInfo(
      resume.structuredResume
        ? `Loaded saved resume "${resume.title}" with ${resume.structuredResume.projects.length} project(s), ${resume.structuredResume.experience.length} experience item(s), and ${resume.structuredResume.skills.length} skill(s).`
        : `Loaded saved resume "${resume.title}". Parse it before review if structured sections are needed.`
    );
    setResult(null);
    setLastSavedAnalysisId(null);
    setLastSavedResumeId(null);
    setLastSavedJobDescriptionId(null);
    setScoreStep("upload");
  }

  function useSavedJd(jobDescription: HistoryJobDescriptionRecord) {
    const nextText = jobDescription.normalizedText || jobDescription.rawText;
    setJobDescriptionText(nextText);
    setParsedJd(jobDescription.parsedJobDescription ?? null);
    setJdParseInfo(
      jobDescription.parsedJobDescription
        ? `Loaded saved JD "${jobDescription.title}" with ${jobDescription.parsedJobDescription.requiredSkills.length} required skill(s) and ${jobDescription.parsedJobDescription.emphasizedRequirements.length} emphasized requirement(s).`
        : `Loaded saved JD "${jobDescription.title}". Parse it before review if structured requirements are needed.`
    );
    setResult(null);
    setLastSavedAnalysisId(null);
    setLastSavedResumeId(null);
    setLastSavedJobDescriptionId(null);
    setScoreStep("upload");
  }

  function toggleComparisonResume(resumeId: string) {
    setComparisonResumeIds((current) => current.includes(resumeId) ? current.filter((id) => id !== resumeId) : [...current, resumeId]);
  }

  function toggleComparisonJd(jobDescriptionId: string) {
    setComparisonJdIds((current) => current.includes(jobDescriptionId) ? current.filter((id) => id !== jobDescriptionId) : [...current, jobDescriptionId]);
  }

  async function runComparison() {
    const selectedResumes = resumeHistory.filter((resume) => comparisonResumeIds.includes(resume.id));
    const selectedJds = jdHistory.filter((jd) => comparisonJdIds.includes(jd.id));
    const totalRuns = selectedResumes.length * selectedJds.length;
    if (!selectedResumes.length || !selectedJds.length) {
      setComparisonInfo("Select at least one saved resume and one saved JD.");
      return;
    }
    if (totalRuns > 9) {
      setComparisonInfo("Comparison is capped at 9 score runs. Select fewer resumes or JDs.");
      return;
    }

    setComparisonLoading(true);
    setComparisonInfo(`Running ${totalRuns} score-only comparison(s).`);
    setComparisonResults([]);
    try {
      const nextResults: ComparisonResult[] = [];
      for (const resume of selectedResumes) {
        for (const jd of selectedJds) {
          const resumeTextForRun = resume.normalizedText || resume.rawText;
          const jdTextForRun = jd.normalizedText || jd.rawText;
          const parsed = jd.parsedJobDescription;
          const basePayload = buildAnalyzeRequest();
          const payload: AnalyzeRequestPayload = {
            ...basePayload,
            resumeText: resumeTextForRun,
            jobDescriptionText: jdTextForRun,
            candidateContext: {
              ...basePayload.candidateContext,
              targetRole: parsed?.roleTitle || jd.title || targetRole,
            },
            scoringCalibrationUserId: workspaceUserId,
            roleFamily: inferRoleFamily(`${parsed?.roleTitle ?? jd.title} ${jdTextForRun}`),
          };
          const response = await fetch(`${API_BASE_URL}/ai/match/score`, {
            method: "POST",
            headers: authHeaders(),
            body: JSON.stringify(payload),
          });
          if (!response.ok) {
            throw new Error(await readApiError(response, `Comparison failed for ${resume.title} and ${jd.title}`));
          }
          const analysis = await response.json() as AnalysisResponse;
          nextResults.push({
            id: `${resume.id}-${jd.id}`,
            resumeId: resume.id,
            resumeTitle: resume.title,
            jobDescriptionId: jd.id,
            jobTitle: jd.title,
            company: jd.company,
            score: analysis.technicalMatchScore,
            fitCategory: analysis.fitCategory,
            recommendedAction: analysis.recommendedAction,
          });
          setComparisonResults([...nextResults].sort((a, b) => b.score - a.score));
        }
      }
      const rankedResults = [...nextResults].sort((a, b) => b.score - a.score);
      setComparisonResults(rankedResults);
      const savedRun = await saveComparisonRun(
        selectedResumes.map((resume) => resume.id),
        selectedJds.map((jd) => jd.id),
        rankedResults,
      );
      setComparisonHistory((items) => [savedRun, ...items.filter((item) => item.id !== savedRun.id)]);
      setActiveComparisonId(savedRun.id);
      setComparisonInfo(`Completed and saved ${rankedResults.length} score-only comparison(s).`);
      void loadCurrentQuota();
    } catch (err) {
      setComparisonInfo(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setComparisonLoading(false);
    }
  }

  async function saveComparisonRun(resumeIds: string[], jobDescriptionIds: string[], results: ComparisonResult[]) {
    const top = results[0];
    const title = top
      ? `${top.resumeTitle} vs ${top.jobTitle}${results.length > 1 ? ` + ${results.length - 1} more` : ""}`
      : "Saved comparison";
    const response = await fetch(`${API_BASE_URL}/history/comparisons`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: workspaceUserId,
        title,
        resumeIds,
        jobDescriptionIds,
        results,
      }),
    });
    if (!response.ok) throw new Error("Comparison completed, but saving the comparison history failed.");
    return await response.json() as HistoryComparisonRecord;
  }

  function loadComparisonRun(record: HistoryComparisonRecord) {
    setComparisonResumeIds(record.resumeIds);
    setComparisonJdIds(record.jobDescriptionIds);
    setComparisonResults([...record.results].sort((a, b) => b.score - a.score));
    setActiveComparisonId(record.id);
    setComparisonInfo(`Loaded saved comparison "${record.title}" from ${formatDate(record.createdAt)}.`);
  }

  async function renameComparisonRun(record: HistoryComparisonRecord) {
    const nextTitle = window.prompt("Rename comparison", record.title)?.trim();
    if (!nextTitle || nextTitle === record.title) return;
    setComparisonInfo("");
    try {
      const response = await fetch(`${API_BASE_URL}/history/comparisons/${record.id}`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify({ userId: workspaceUserId, title: nextTitle }),
      });
      if (!response.ok) throw new Error("Comparison rename failed");
      const updated = await response.json() as HistoryComparisonRecord;
      setComparisonHistory((items) => items.map((item) => item.id === updated.id ? updated : item));
      setComparisonInfo(`Renamed comparison to "${updated.title}".`);
    } catch (err) {
      setComparisonInfo(err instanceof Error ? err.message : "Comparison rename failed");
    }
  }

  async function deleteComparisonRun(record: HistoryComparisonRecord) {
    if (!window.confirm(`Delete saved comparison "${record.title}"?`)) return;
    setComparisonInfo("");
    try {
      const response = await fetch(`${API_BASE_URL}/history/comparisons/${record.id}`, {
        method: "DELETE",
        headers: authHeaders(),
        body: JSON.stringify({ userId: workspaceUserId }),
      });
      if (!response.ok) throw new Error("Comparison delete failed");
      setComparisonHistory((items) => items.filter((item) => item.id !== record.id));
      if (activeComparisonId === record.id) {
        setActiveComparisonId(null);
        setComparisonResults([]);
      }
      setComparisonInfo(`Deleted comparison "${record.title}".`);
    } catch (err) {
      setComparisonInfo(err instanceof Error ? err.message : "Comparison delete failed");
    }
  }

  async function loadPrepMemory() {
    try {
      const response = await fetch(`${API_BASE_URL}/ai/preparation/memory/${workspaceUserId}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("Preparation memory load failed");
      setPrepMemory(await response.json() as PrepMemoryResponse);
    } catch {
      setPrepMemory(null);
    }
  }

  async function loadOpportunityActions() {
    try {
      const response = await fetch(`${API_BASE_URL}/ai/opportunities/next-actions/${workspaceUserId}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("Opportunity actions unavailable");
      setOpportunityActions(await response.json() as OpportunityNextActionsResponse);
    } catch {
      setOpportunityActions(null);
    }
  }

  async function openPrepMemoryAction(action: NonNullable<PrepMemoryResponse["nextAction"]>) {
    if (action.sessionId) {
      let session = preparationHistory.find((item) => item.id === action.sessionId) ?? null;
      if (!session) {
        try {
          const response = await fetch(`${API_BASE_URL}/history/users/${workspaceUserId}/preparation-sessions/${action.sessionId}`, { headers: authHeaders(false) });
          if (response.ok) {
            session = await response.json() as HistoryPreparationRecord;
            setPreparationHistory((items) => items.some((item) => item.id === session?.id) ? items : session ? [session, ...items] : items);
          }
        } catch {
          session = null;
        }
      }
      if (session) {
        setActivePreparationSession(session);
        setProgressInfo(action.task ? `Next: Day ${action.day ?? ""} - ${action.task}` : action.reason);
      } else {
        setProgressInfo("Could not load the recommended preparation session.");
      }
      setActiveTask("progress");
      return;
    }
    if (action.kind === "prepare_repeated_gap") {
      setPreparationInfo(action.reason);
      setActiveTask("preparation");
      return;
    }
    setProgressInfo(action.reason);
    setActiveTask("progress");
  }

  async function updateJobOpportunityStatus(jobOpportunityId: string, status: JobOpportunityStatus) {
    setHistoryInfo("");
    try {
      const response = await fetch(`${API_BASE_URL}/history/job-opportunities/${jobOpportunityId}/status`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify({ userId: workspaceUserId, status }),
      });
      if (!response.ok) throw new Error("Opportunity status update failed");
      const updated = await response.json() as HistoryJobOpportunityRecord;
      setJobOpportunityHistory((items) => items.map((item) => item.id === updated.id ? updated : item));
      setHistoryInfo(`Updated ${updated.title} to ${updated.status}.`);
      void loadOpportunityActions();
    } catch (err) {
      setHistoryInfo(err instanceof Error ? err.message : "Opportunity status update failed");
    }
  }

  async function persistAnalysisArtifact(analysisId: string, artifactKey: string, response: AnalysisResponse) {
    const updateResponse = await fetch(`${API_BASE_URL}/history/analyses/${analysisId}/optional-artifacts`, {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: workspaceUserId,
        artifactKey,
        response,
      }),
    });
    if (!updateResponse.ok) throw new Error("Optional artifact usage save failed");
    const updated = await updateResponse.json() as HistoryAnalysisRecord;
    setAnalysisHistory((items) => items.map((item) => item.id === updated.id ? updated : item));
    return updated;
  }

  async function persistOpportunityArtifact(opportunityId: string, artifactKey: string, response: AnalysisResponse) {
    const updateResponse = await fetch(`${API_BASE_URL}/history/job-opportunities/${opportunityId}/optional-artifacts`, {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: workspaceUserId,
        artifactKey,
        response,
      }),
    });
    if (!updateResponse.ok) throw new Error("Opportunity artifact usage save failed");
    const updated = await updateResponse.json() as HistoryJobOpportunityRecord;
    setJobOpportunityHistory((items) => items.map((item) => item.id === updated.id ? updated : item));
    return updated;
  }

  async function checkExtensionSetup() {
    setExtensionChecking(true);
    setExtensionSetupInfo("");
    try {
      const healthResponse = await fetch(`${API_BASE_URL}/ready`);
      if (!healthResponse.ok) throw new Error("Backend health check failed");
      await ensureLocalUser();
      const diagnosticsResponse = await fetch(`${API_BASE_URL}/extension/diagnostics`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: workspaceUserId,
          anonymousSessionId: null,
        }),
      });
      if (!diagnosticsResponse.ok) throw new Error("Extension diagnostics check failed");
      const diagnostics = await diagnosticsResponse.json() as ExtensionDiagnostics;
      setExtensionDiagnostics(diagnostics);
      setExtensionResumeCount(diagnostics.resumeCount);
      setExtensionSetupInfo(
        diagnostics.canMatchSavedResume
          ? `Backend is ready. ${diagnostics.resumeCount} saved resume(s) are available for extension matching.`
          : "Backend is ready, but no saved resumes are available. Run a score once or save a resume first.",
      );
    } catch (err) {
      setExtensionDiagnostics(null);
      setExtensionResumeCount(null);
      setExtensionSetupInfo(err instanceof Error ? err.message : "Extension setup check failed");
    } finally {
      setExtensionChecking(false);
    }
  }

  async function loadExtensionValidations() {
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/extension/users/${workspaceUserId}/validation-results`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("Extension validation history unavailable");
      setExtensionValidations(await response.json() as ExtensionValidationRecord[]);
    } catch (err) {
      setExtensionValidationInfo(err instanceof Error ? err.message : "Extension validation history unavailable");
    }
  }

  async function saveExtensionValidation(payload: {
    site: string;
    url: string;
    parserRating: "pass" | "partial" | "fail";
    autoParsed: boolean;
    manualPasteUsed: boolean;
    titleFound: boolean;
    companyFound: boolean;
    descriptionFound: boolean;
    notes: string;
  }) {
    setExtensionValidationInfo("");
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/extension/validation-results`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: workspaceUserId,
          ...payload,
          url: payload.url.trim() || null,
          notes: payload.notes.trim() || null,
        }),
      });
      if (!response.ok) throw new Error("Extension validation save failed");
      const saved = await response.json() as ExtensionValidationRecord;
      setExtensionValidations((items) => [saved, ...items].slice(0, 25));
      setExtensionValidationInfo(`Saved ${saved.site} validation as ${saved.parserRating}.`);
    } catch (err) {
      setExtensionValidationInfo(err instanceof Error ? err.message : "Extension validation save failed");
    }
  }

  async function loadEvaluationSummary() {
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/evaluation/users/${workspaceUserId}/summary`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("Evaluation summary unavailable");
      setEvaluationSummary(await response.json() as MatchFeedbackSummary);
    } catch (err) {
      setEvaluationInfo(err instanceof Error ? err.message : "Evaluation summary unavailable");
    }
  }

  async function saveMatchFeedback(payload: {
    roleFamily: string;
    expectedFit: "strong" | "good" | "partial" | "weak";
    scoreAccuracy: "accurate" | "too_high" | "too_low";
    outcome: "not_applied" | "applied" | "shortlisted" | "interview" | "rejected" | "offer" | "no_response";
    notes: string;
  }) {
    setEvaluationInfo("");
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/evaluation/match-feedback`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: workspaceUserId,
          analysisId: lastSavedAnalysisId,
          roleFamily: payload.roleFamily.trim() || null,
          expectedFit: payload.expectedFit,
          scoreAccuracy: payload.scoreAccuracy,
          outcome: payload.outcome,
          notes: payload.notes.trim() || null,
        }),
      });
      if (!response.ok) throw new Error("Match feedback save failed");
      setEvaluationInfo("Saved feedback for the latest analysis.");
      await loadEvaluationSummary();
    } catch (err) {
      setEvaluationInfo(err instanceof Error ? err.message : "Match feedback save failed");
    }
  }

  async function exportEvaluationDataset() {
    setEvaluationInfo("");
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/evaluation/users/${workspaceUserId}/dataset`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("Evaluation export failed");
      const dataset = await response.json() as MatchFeedbackDataset;
      const blob = new Blob([JSON.stringify(dataset, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `career-agent-evaluation-${workspaceUserId}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      setEvaluationInfo(`Exported ${dataset.records.length} feedback record(s).`);
    } catch (err) {
      setEvaluationInfo(err instanceof Error ? err.message : "Evaluation export failed");
    }
  }

  async function importEvaluationDataset(file: File | null) {
    if (!file) return;
    setEvaluationInfo("");
    try {
      await ensureLocalUser();
      const text = await file.text();
      const dataset = JSON.parse(text) as MatchFeedbackDataset;
      const response = await fetch(`${API_BASE_URL}/evaluation/dataset/import`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: workspaceUserId,
          records: dataset.records.map((record) => ({
            analysisId: record.analysisId ?? null,
            jobOpportunityId: record.jobOpportunityId ?? null,
            roleFamily: record.roleFamily ?? null,
            algorithmScore: record.algorithmScore ?? null,
            fitCategory: record.fitCategory ?? null,
            expectedFit: record.expectedFit,
            scoreAccuracy: record.scoreAccuracy,
            outcome: record.outcome,
            notes: record.notes ?? null,
          })),
        }),
      });
      if (!response.ok) throw new Error("Evaluation import failed");
      const imported = await response.json() as MatchFeedbackDataset;
      setEvaluationInfo(`Imported ${imported.records.length} feedback record(s).`);
      await loadEvaluationSummary();
    } catch (err) {
      setEvaluationInfo(err instanceof Error ? err.message : "Evaluation import failed");
    }
  }

  async function loadScoringConfigs() {
    setSettingsInfo("");
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/settings/users/${workspaceUserId}/scoring-calibration`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("Scoring calibration settings unavailable");
      const payload = await response.json() as { configs: ScoringCalibrationConfig[] };
      setScoringConfigs(payload.configs);
      await loadScoringAudit();
    } catch (err) {
      setSettingsInfo(err instanceof Error ? err.message : "Scoring calibration settings unavailable");
    }
  }

  async function loadScoringAudit(roleFamily?: string) {
    try {
      await ensureLocalUser();
      const suffix = roleFamily ? `?roleFamily=${encodeURIComponent(roleFamily)}` : "";
      const response = await fetch(`${API_BASE_URL}/settings/users/${workspaceUserId}/scoring-calibration-audit${suffix}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("Scoring calibration audit unavailable");
      setScoringAudit(await response.json() as ScoringCalibrationAuditRecord[]);
    } catch (err) {
      setSettingsInfo(err instanceof Error ? err.message : "Scoring calibration audit unavailable");
    }
  }

  async function loadSystemDiagnostics() {
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/diagnostics/system?userId=${encodeURIComponent(workspaceUserId)}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("System diagnostics unavailable");
      setSystemDiagnostics(await response.json() as SystemDiagnostics);
    } catch (err) {
      setSettingsInfo(err instanceof Error ? err.message : "System diagnostics unavailable");
    }
  }

  async function loadProductionReadiness() {
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/diagnostics/production-readiness?userId=${encodeURIComponent(workspaceUserId)}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("Production readiness unavailable");
      setProductionReadiness(await response.json() as ProductionReadiness);
    } catch (err) {
      setSettingsInfo(err instanceof Error ? err.message : "Production readiness unavailable");
    }
  }

  async function loadAdminUsers() {
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/admin/users`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("User list unavailable");
      setAdminUsers(await response.json() as AdminUserRecord[]);
    } catch (err) {
      setSettingsInfo(err instanceof Error ? err.message : "User list unavailable");
    }
  }

  async function loadAdminAnalyses(query = "", targetUserId = "") {
    try {
      await ensureLocalUser();
      const params = new URLSearchParams({ limit: "25" });
      if (query.trim()) params.set("query", query.trim());
      if (targetUserId.trim()) params.set("userId", targetUserId.trim());
      const response = await fetch(`${API_BASE_URL}/admin/analyses?${params.toString()}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("Admin analysis search unavailable");
      setAdminAnalyses(await response.json() as HistoryAnalysisRecord[]);
    } catch (err) {
      setSettingsInfo(err instanceof Error ? err.message : "Admin analysis search unavailable");
    }
  }

  async function loadUsageSummary(targetUserId = "") {
    try {
      await ensureLocalUser();
      const params = new URLSearchParams({ limit: "25" });
      if (targetUserId.trim()) params.set("userId", targetUserId.trim());
      const response = await fetch(`${API_BASE_URL}/admin/usage?${params.toString()}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("Usage summary unavailable");
      setUsageSummary(await response.json() as UsageSummary);
    } catch (err) {
      setSettingsInfo(err instanceof Error ? err.message : "Usage summary unavailable");
    }
  }

  async function seedDemoWorkspace() {
    setSettingsInfo("");
    setDemoSeedResult(null);
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/admin/demo/seed`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: "demo-aditya",
          displayName: "Aditya Demo",
          email: "demo.aditya@example.com",
          password: "DemoPass123!",
          subscriptionTier: "premium",
          reset: true,
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response, "Demo seed failed. Admin access is required."));
      const seeded = await response.json() as DemoSeedResponse;
      setDemoSeedResult(seeded);
      applyAuthenticatedSession(
        {
          user: {
            id: seeded.userId,
            displayName: seeded.displayName,
            email: seeded.email,
            role: "member",
            subscriptionTier: seeded.subscriptionTier,
            subscriptionStatus: "inactive",
            createdAt: new Date().toISOString(),
          },
          sessionToken: seeded.sessionToken,
        },
        "Demo workspace session active.",
      );
      setSettingsInfo(`Seeded ${seeded.resumeCount} resume(s), ${seeded.jobDescriptionCount} JD(s), ${seeded.analysisCount} analysis, ${seeded.jobOpportunityCount} opportunity, and ${seeded.researchNoteCount} research note(s).`);
      updateLaunchChecklist("demo_seed", true);
      setActiveTask("history");
    } catch (err) {
      setSettingsInfo(err instanceof Error ? err.message : "Demo seed failed");
    }
  }

  function updateLaunchChecklist(itemId: string, checked: boolean) {
    setLaunchChecklist((current) => {
      const next = { ...current, [itemId]: checked };
      window.localStorage.setItem(launchChecklistStorageKey, JSON.stringify(next));
      return next;
    });
  }

  function resetLaunchChecklist() {
    window.localStorage.removeItem(launchChecklistStorageKey);
    setLaunchChecklist({});
    setSettingsInfo("Launch checklist reset for this browser.");
  }

  async function loadCurrentQuota() {
    try {
      await ensureLocalUser();
      const params = new URLSearchParams({ userId: workspaceUserId });
      const response = await fetch(`${API_BASE_URL}/usage/quota?${params.toString()}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error(await readApiError(response, "Usage quota unavailable"));
      setUsageQuota(await response.json() as UsageQuotaStatus);
    } catch {
      setUsageQuota(null);
    }
  }

  function startBillingEdit(user: AdminUserRecord) {
    setBillingDraft({
      userId: user.id,
      subscriptionTier: user.subscriptionTier === "premium" ? "premium" : "free",
      subscriptionStatus: (["trialing", "active", "past_due", "canceled"].includes(user.subscriptionStatus ?? "") ? user.subscriptionStatus : "inactive") as BillingDraft["subscriptionStatus"],
      subscriptionPlanId: user.subscriptionPlanId ?? "",
      billingProviderCustomerId: user.billingProviderCustomerId ?? "",
      billingProviderSubscriptionId: user.billingProviderSubscriptionId ?? "",
      billingPeriodEnd: user.billingPeriodEnd ?? "",
    });
    setSettingsInfo("");
  }

  async function saveBillingMetadata(draft: BillingDraft) {
    setSettingsInfo("");
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/admin/users/${encodeURIComponent(draft.userId)}/billing`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify({
          subscriptionTier: draft.subscriptionTier,
          subscriptionStatus: draft.subscriptionStatus,
          subscriptionPlanId: draft.subscriptionPlanId.trim() || null,
          billingProviderCustomerId: draft.billingProviderCustomerId.trim() || null,
          billingProviderSubscriptionId: draft.billingProviderSubscriptionId.trim() || null,
          billingPeriodEnd: draft.billingPeriodEnd.trim() || null,
        }),
      });
      if (!response.ok) throw new Error("Billing metadata save failed. Admin access is required.");
      const saved = await response.json() as AdminUserRecord;
      setAdminUsers((items) => items.map((item) => item.id === saved.id ? saved : item));
      if (currentUser?.id === saved.id) {
        setCurrentUser(saved);
        const nextTier = storedAccountTier(saved);
        setAccountTier(nextTier);
        window.localStorage.setItem(accountTierStorageKey, nextTier);
      }
      setBillingDraft(null);
      setSettingsInfo(`Saved billing metadata for ${saved.displayName}.`);
    } catch (err) {
      setSettingsInfo(err instanceof Error ? err.message : "Billing metadata save failed");
    }
  }

  async function saveScoringConfig(config: ScoringCalibrationConfig) {
    setSettingsInfo("");
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/settings/scoring-calibration`, {
        method: "PUT",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: workspaceUserId,
          roleFamily: config.roleFamily,
          categoryWeights: config.categoryWeights,
        }),
      });
      if (!response.ok) throw new Error("Scoring calibration save failed. Check that weights total 100.");
      const saved = await response.json() as ScoringCalibrationConfig;
      setScoringConfigs((items) => items.map((item) => item.roleFamily === saved.roleFamily ? saved : item));
      setSettingsInfo(`Saved scoring weights for ${saved.roleFamily}. New scores will use this calibration.`);
      await loadScoringAudit(saved.roleFamily);
    } catch (err) {
      setSettingsInfo(err instanceof Error ? err.message : "Scoring calibration save failed");
    }
  }

  async function restoreScoringConfig(auditId: string) {
    setSettingsInfo("");
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/settings/scoring-calibration/restore`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ userId: workspaceUserId, auditId }),
      });
      if (!response.ok) throw new Error("Scoring calibration restore failed");
      const restored = await response.json() as ScoringCalibrationConfig;
      setScoringConfigs((items) => items.map((item) => item.roleFamily === restored.roleFamily ? restored : item));
      setSettingsInfo(`Restored previous weights for ${restored.roleFamily}.`);
      await loadScoringAudit(restored.roleFamily);
    } catch (err) {
      setSettingsInfo(err instanceof Error ? err.message : "Scoring calibration restore failed");
    }
  }

  async function loadScoringRecommendation(roleFamily: string) {
    setSettingsInfo("");
    try {
      await ensureLocalUser();
      const response = await fetch(`${API_BASE_URL}/settings/users/${workspaceUserId}/scoring-calibration-recommendation?roleFamily=${encodeURIComponent(roleFamily)}`, { headers: authHeaders(false) });
      if (!response.ok) throw new Error("Scoring recommendation unavailable");
      const recommendation = await response.json() as ScoringCalibrationRecommendation;
      setScoringRecommendation(recommendation);
      setSettingsInfo(`Loaded ${recommendation.confidence}-confidence recommendation from ${recommendation.sampleSize} label(s).`);
    } catch (err) {
      setScoringRecommendation(null);
      setSettingsInfo(err instanceof Error ? err.message : "Scoring recommendation unavailable");
    }
  }

  async function analyze() {
    setLoading(true);
    setError("");
    setPreparationInfo("");
    setProgressInfo("");
    setCostMode("free");
    setCostModeInfo("Running score-only mode. Optional artifacts stay off until requested.");
    setResult(null);
    setActivePreparationSession(null);
    setLastSavedAnalysisId(null);
    setLastSavedResumeId(null);
    setLastSavedJobDescriptionId(null);
    setAgentPlan(null);
    setAgentInfo("");

    try {
      if (!structuredResume || !parsedJd) {
        throw new Error("Parse and review the resume and JD before calculating the score.");
      }
      const payload = buildAnalyzeRequest();
      const fingerprint = await buildAnalysisFingerprint(payload);
      const savedAnalysis = await lookupSavedAnalysis(fingerprint);
      if (savedAnalysis) {
        setLastAnalysisRequest(savedAnalysis.request);
        setLastSavedAnalysisId(savedAnalysis.id);
        setLastSavedResumeId(savedAnalysis.resumeId ?? null);
        setLastSavedJobDescriptionId(savedAnalysis.jobDescriptionId ?? null);
        setLastAnalysisFingerprint(savedAnalysis.fingerprint ?? fingerprint);
        setResult(savedAnalysis.response);
        setHistoryInfo(`Reused saved score from ${formatDate(savedAnalysis.createdAt)}. Edit inputs to calculate a new score.`);
        setActiveTask("report");
        return;
      }
      const response = await fetch(`${API_BASE_URL}/ai/match/score`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "Analysis failed"));
      }

      const analysis = await response.json() as AnalysisResponse;
      void loadCurrentQuota();
      setLastAnalysisRequest(payload);
      setLastAnalysisFingerprint(fingerprint);
      setResult(analysis);
      try {
        const saved = await saveHistorySnapshot(payload, analysis, fingerprint);
        setLastSavedAnalysisId(saved.id);
        setLastSavedResumeId(saved.resumeId ?? null);
        setLastSavedJobDescriptionId(saved.jobDescriptionId ?? null);
        setHistoryInfo("Saved latest resume, JD, and match report to history.");
        if (activeTask === "history") void loadHistory();
      } catch (historyError) {
        setHistoryInfo(historyError instanceof Error ? historyError.message : "History save failed.");
      }
      setActiveTask("report");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function buildPreparation(): Promise<boolean> {
    if (!canUsePremium) {
      setPreparationInfo("Premium access is required for preparation intelligence. Switch the workspace tier to Premium or use an admin session.");
      setCostModeInfo("Premium module locked on the current tier.");
      return false;
    }
    if (!result || !lastAnalysisRequest) {
      setError("Run resume matching before building the preparation plan.");
      return false;
    }

    setPreparing(true);
    setError("");
    setPreparationInfo("");

    try {
      const response = await fetch(`${API_BASE_URL}/ai/preparation/plan`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          sourceRequest: lastAnalysisRequest,
          analysis: result,
          preparationPlanDays,
          researchNotes: researchNotes.map(toResearchContextNote),
        }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "Preparation build failed"));
      }

      const preparation = await response.json() as PreparationIntelligence;
      void loadCurrentQuota();
      const updatedResult = { ...result, preparationIntelligence: preparation };
      setResult(updatedResult);
      if (lastSavedAnalysisId) {
        try {
          await persistAnalysisArtifact(lastSavedAnalysisId, "preparation_plan", updatedResult);
        } catch (artifactError) {
          setCostModeInfo("Preparation plan generated, but usage metadata was not saved.");
        }
      }
      try {
        const savedSession = await savePreparationSession(preparation);
        setActivePreparationSession(savedSession);
        if (activeTask === "history") void loadHistory();
        setPreparationInfo(`Built and saved a ${preparation.dailyPlan.length}-day preparation plan from the latest match result.`);
      } catch (historyError) {
        setPreparationInfo(`Built a ${preparation.dailyPlan.length}-day preparation plan, but history save failed.`);
      }
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preparation build failed");
      return false;
    } finally {
      setPreparing(false);
    }
  }

  async function buildOptionalArtifact(
    label: string,
    artifactKey: string,
    endpoint: string,
    applyResult: (current: AnalysisResponse, payload: unknown) => AnalysisResponse,
  ): Promise<boolean> {
    if (!canUsePremium) {
      setCostModeInfo(`${label} is a premium module. Switch the workspace tier to Premium or use an admin session.`);
      return false;
    }
    if (!result || !lastAnalysisRequest) {
      setError("Run resume matching before generating optional artifacts.");
      return false;
    }

    setArtifactLoading(label);
    setError("");
    setCostModeInfo(`Running ${label} as a separate optional call.`);

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          sourceRequest: lastAnalysisRequest,
          analysis: result,
          limit: 8,
        }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, `${label} generation failed`));
      }

      const payload = await response.json();
      void loadCurrentQuota();
      const updatedResult = applyResult(result, payload);
      setResult(updatedResult);
      if (lastSavedAnalysisId) {
        try {
          await persistAnalysisArtifact(lastSavedAnalysisId, artifactKey, updatedResult);
        } catch (artifactError) {
          setCostModeInfo(`${label} generated, but usage metadata was not saved.`);
        }
      }
      setCostModeInfo(`Completed ${label}.`);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} generation failed`);
      return false;
    } finally {
      setArtifactLoading("");
    }
  }

  async function runCostModeBundle(mode: Exclude<CostMode, "free">) {
    if (!canUsePremium) {
      setCostMode("free");
      setCostModeInfo("Premium access is required for optional artifact bundles.");
      return;
    }
    if (!result || !lastAnalysisRequest) {
      setError("Run score-only matching before generating paid artifacts.");
      return;
    }
    setCostMode(mode);
    setCostModeInfo(mode === "standard" ? "Standard runs two small optional calls one at a time." : "Premium runs optional calls one at a time, including preparation.");

    const standardSteps = [
      () => buildOptionalArtifact(
        "Resume improvements",
        "resume_improvements",
        "/ai/resume-improvements",
        (current, payload) => ({ ...current, resumeImprovements: payload as AnalysisResponse["resumeImprovements"] }),
      ),
      () => buildOptionalArtifact(
        "Interview questions",
        "interview_questions",
        "/ai/interview/questions",
        (current, payload) => ({ ...current, interviewQuestions: payload as AnalysisResponse["interviewQuestions"] }),
      ),
    ];
    const premiumSteps = [
      ...standardSteps,
      () => buildOptionalArtifact(
        "Cross questions",
        "cross_questions",
        "/ai/cross-questions",
        (current, payload) => ({ ...current, crossQuestions: payload as AnalysisResponse["crossQuestions"] }),
      ),
    ];
    const steps = mode === "standard" ? standardSteps : premiumSteps;

    for (const step of steps) {
      const ok = await step();
      if (!ok) {
        setCostModeInfo("Stopped because one optional call failed.");
        return;
      }
    }
    if (mode === "premium") {
      const ok = await buildPreparation();
      if (!ok) {
        setCostModeInfo("Optional artifacts completed, but preparation plan failed.");
        return;
      }
    }
    setCostModeInfo(mode === "standard" ? "Standard artifacts completed with separate calls." : "Premium artifacts completed with separate calls.");
  }

  async function buildOpportunityArtifact(
    opportunity: HistoryJobOpportunityRecord,
    artifactKey: "resume_improvements" | "interview_questions" | "cross_questions",
  ) {
    const linkedAnalysis = analysisHistory.find((analysis) => analysis.id === opportunity.analysisId);
    const sourceRequest = linkedAnalysis?.request;
    const baseAnalysis = opportunity.analysisResponse ?? linkedAnalysis?.response;
    if (!sourceRequest || !baseAnalysis) {
      setHistoryInfo("This saved job does not have a linked analysis request yet. Re-run it from the extension after connecting a user.");
      return;
    }

    const config = {
      resume_improvements: {
        label: "Resume improvements",
        endpoint: "/ai/resume-improvements",
        apply: (current: AnalysisResponse, payload: unknown) => ({ ...current, resumeImprovements: payload as AnalysisResponse["resumeImprovements"] }),
      },
      interview_questions: {
        label: "Interview questions",
        endpoint: "/ai/interview/questions",
        apply: (current: AnalysisResponse, payload: unknown) => ({ ...current, interviewQuestions: payload as AnalysisResponse["interviewQuestions"] }),
      },
      cross_questions: {
        label: "Cross questions",
        endpoint: "/ai/cross-questions",
        apply: (current: AnalysisResponse, payload: unknown) => ({ ...current, crossQuestions: payload as AnalysisResponse["crossQuestions"] }),
      },
    }[artifactKey];

    setArtifactLoading(`Opportunity ${config.label}`);
    setHistoryInfo(`Generating ${config.label} for ${opportunity.title}.`);
    try {
      const response = await fetch(`${API_BASE_URL}${config.endpoint}`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          sourceRequest,
          analysis: baseAnalysis,
          limit: 8,
        }),
      });
      if (!response.ok) {
        throw new Error(await readApiError(response, `${config.label} generation failed`));
      }
      const payload = await response.json();
      void loadCurrentQuota();
      const updatedAnalysis = config.apply(baseAnalysis, payload);
      await persistOpportunityArtifact(opportunity.id, artifactKey, updatedAnalysis);
      if (linkedAnalysis) {
        await persistAnalysisArtifact(linkedAnalysis.id, artifactKey, updatedAnalysis);
      }
      setHistoryInfo(`${config.label} saved for ${opportunity.title}.`);
      void loadOpportunityActions();
    } catch (err) {
      setHistoryInfo(err instanceof Error ? err.message : `${config.label} generation failed`);
    } finally {
      setArtifactLoading("");
    }
  }

  async function updatePreparationProgress(nextProgress: PreparationProgress, nextStatus?: HistoryPreparationRecord["status"]) {
    if (!activePreparationSession) {
      setProgressInfo("Build or load a preparation session before tracking progress.");
      return;
    }
    setProgressSaving(true);
    setProgressInfo("");
    try {
      const response = await fetch(`${API_BASE_URL}/history/preparation-sessions/${activePreparationSession.id}/progress`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: workspaceUserId,
          status: nextStatus ?? inferPreparationStatus(nextProgress, activePreparationSession.plan),
          progress: nextProgress,
        }),
      });
      if (!response.ok) throw new Error("Progress save failed");
      const updated = await response.json() as HistoryPreparationRecord;
      setActivePreparationSession(updated);
      setPreparationHistory((items) => items.map((item) => item.id === updated.id ? updated : item));
      setProgressInfo("Progress saved.");
      void loadPrepMemory();
    } catch (err) {
      setProgressInfo(err instanceof Error ? err.message : "Progress save failed.");
    } finally {
      setProgressSaving(false);
    }
  }

  async function uploadResume(file: File | null) {
    if (!file) return;
    setUploading(true);
    setError("");
    setUploadInfo("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE_URL}/ai/resume/extract`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "Resume extraction failed"));
      }

      const extracted = await response.json() as {
        fileName: string;
        extractedText: string;
        characterCount: number;
        detectedEmails: string[];
        detectedPhones: string[];
        detectedSections: string[];
      };

      setResumeText(extracted.extractedText);
      setResumeParseSourceText(extracted.extractedText);
      setStructuredResume(null);
      setResumeParserDebug(null);
      setNormalizeInfo("");
      setResult(null);
      setUploadInfo(
        `${extracted.fileName}: ${extracted.characterCount} chars, sections: ${
          extracted.detectedSections.length ? extracted.detectedSections.join(", ") : "not detected"
        }`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume extraction failed");
    } finally {
      setUploading(false);
    }
  }

  async function uploadJobDescription(file: File | null) {
    if (!file) return;
    setJdUploading(true);
    setError("");
    setJdUploadInfo("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE_URL}/ai/resume/extract`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "JD extraction failed"));
      }

      const extracted = await response.json() as {
        fileName: string;
        extractedText: string;
        characterCount: number;
        detectedEmails: string[];
        detectedPhones: string[];
        detectedSections: string[];
      };

      setJobDescriptionText(extracted.extractedText);
      setParsedJd(null);
      setJdParseInfo("");
      setResult(null);
      setJdUploadInfo(`${extracted.fileName}: ${extracted.characterCount} chars extracted`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "JD extraction failed");
    } finally {
      setJdUploading(false);
    }
  }

  async function normalizeCurrentResume() {
    setNormalizing(true);
    setError("");
    setNormalizeInfo("");

    try {
      const response = await fetch(`${API_BASE_URL}/ai/resume/normalize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rawResumeText: resumeText }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "Resume normalization failed"));
      }

      const normalized = await response.json() as {
        normalizedResumeText: string;
        warnings: string[];
        structuredResume: StructuredResume;
        parserDebug?: ResumeParserDebug | null;
      };

      setResumeParseSourceText(resumeText);
      setResumeText(normalized.normalizedResumeText);
      setStructuredResume(normalized.structuredResume);
      setResumeParserDebug(normalized.parserDebug ?? null);
      const warnings = normalized.warnings.length ? ` Warnings: ${normalized.warnings.join(" ")}` : "";
      setNormalizeInfo(
        `Normalized ${normalized.structuredResume.experience.length} experience item(s), ${normalized.structuredResume.projects.length} project(s), ${normalized.structuredResume.skills.length} skill(s).${warnings}`
      );
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume normalization failed");
      return false;
    } finally {
      setNormalizing(false);
    }
  }

  async function parseCurrentJd() {
    setParsingJd(true);
    setError("");
    setJdParseInfo("");
    setParsedJd(null);

    try {
      const response = await fetch(`${API_BASE_URL}/ai/jd/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rawJobDescriptionText: jobDescriptionText }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response, "JD parsing failed"));
      }

      const parsed = await response.json() as JdParseResponse;
      setJobDescriptionText(parsed.normalizedJobDescriptionText);
      setParsedJd(parsed.parsedJobDescription);
      const warnings = parsed.warnings.length ? ` Warnings: ${parsed.warnings.join(" ")}` : "";
      const requiredCount = parsed.parsedJobDescription.requiredSkills.length;
      const preferredCount = parsed.parsedJobDescription.preferredSkills.length;
      const certificationCount = parsed.parsedJobDescription.requiredCertifications.length;
      const emphasisCount = (parsed.parsedJobDescription.emphasizedRequirements ?? []).length;
      setJdParseInfo(`Parsed ${requiredCount} required skill(s), ${preferredCount} preferred skill(s), ${certificationCount} certification requirement(s), ${emphasisCount} emphasized requirement(s).${warnings}`);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "JD parsing failed");
      return false;
    } finally {
      setParsingJd(false);
    }
  }

  async function parseInputsForReview() {
    const resumeOk = await normalizeCurrentResume();
    const jdOk = await parseCurrentJd();
    if (resumeOk && jdOk) {
      setReviewPane("resume");
      setScoreStep("review");
    }
  }

  const preparation = result?.preparationIntelligence ?? null;
  const canCalculateScore = Boolean(structuredResume && parsedJd && resumeText.trim().length >= 20 && jobDescriptionText.trim().length >= 20);
  const effectiveAccessTier: AccessTier = currentUser?.role === "admin" ? "admin" : accountTier;
  const canUsePremium = effectiveAccessTier === "premium" || effectiveAccessTier === "admin";

  return (
    <main className="shell appShell">
      <section className="header appHeader">
        <div>
          <div className="brandLockup">
            <span className="brandMark">CA</span>
            <p className="eyebrow">Career Agent OS</p>
          </div>
          <h1>Career Agent OS</h1>
          <p className="subtitle">A premium career intelligence workspace for resume fit scoring, interview preparation, and progress tracking.</p>
          <div className="headerBadges">
            <span>Free match score</span>
            <span>Premium insight modules</span>
            <span>PostgreSQL history</span>
          </div>
        </div>
        <div className="scorePreview">
          <span>Free score</span>
          <strong>{result ? `${result.technicalMatchScore}%` : "No run"}</strong>
        </div>
      </section>

      <section className="workspace">
        <TaskNav
          activeTask={activeTask}
          onChange={setActiveTask}
          hasResult={Boolean(result)}
          hasPreparation={Boolean(preparation)}
          resumeReady={resumeText.trim().length >= 20}
          jdReady={jobDescriptionText.trim().length >= 20}
        />

        <section className="taskSurface">
          <SessionStatusPanel
            userId={workspaceUserId}
            draftUserId={workspaceUserDraft}
            sessionInfo={sessionInfo}
            currentUser={currentUser}
            currentRole={currentUser?.role ?? "unknown"}
            authPassword={authPassword}
            authDisplayName={authDisplayName}
            authEmail={authEmail}
            accountTier={accountTier}
            effectiveAccessTier={effectiveAccessTier}
            workspaceSummary={workspaceSummary}
            onDraftUserChange={setWorkspaceUserDraft}
            onPasswordChange={setAuthPassword}
            onDisplayNameChange={setAuthDisplayName}
            onEmailChange={setAuthEmail}
            onAccountTierChange={updateAccountTier}
            onApplyUser={applyWorkspaceUser}
            onLogin={loginWithPassword}
            onRegister={registerWithPassword}
            onReconnect={reconnectSession}
            onClear={() => clearStoredSession()}
          />

          {activeTask === "command" && (
            <TaskPanel
              eyebrow="Workspace"
              title="Command Center"
              description="One operational view for the latest score, career-agent recommendation, preparation memory, and application pipeline."
            >
              <CommandCenterPanel
                result={result}
                agentPlan={agentPlan}
                prepMemory={prepMemory}
                opportunityActions={opportunityActions}
                workspaceSummary={workspaceSummary}
                info={commandCenterInfo}
                loading={commandCenterLoading}
                onOpenTask={setActiveTask}
                onRefresh={loadCommandCenter}
                onBuildAgentPlan={buildAgentPlan}
                onRunAgentRecommendation={runAgentRecommendation}
                onOpenPrepAction={openPrepMemoryAction}
                onRunOpportunityAction={(action) => {
                  const opportunity = jobOpportunityHistory.find((item) => item.id === action.opportunityId);
                  if (!opportunity) return;
                  if (action.artifactKey) {
                    void buildOpportunityArtifact(opportunity, action.artifactKey);
                    return;
                  }
                  if (action.recommendedStatus) {
                    void updateJobOpportunityStatus(opportunity.id, action.recommendedStatus);
                  }
                }}
              />
            </TaskPanel>
          )}

          {activeTask === "matching" && (
            <TaskPanel
              eyebrow="Task 1"
              title="Resume Matching"
              description="Prepare the resume, JD, candidate context, and model selection. This call now returns the match report only; preparation is generated separately."
            >
              <form className="taskForm" onSubmit={(event) => { event.preventDefault(); analyze(); }}>
                <AISpendPanel
                  llmMode={llmMode}
                  llmProvider={llmProvider}
                  llmModel={llmModel}
                  onModeChange={setLlmMode}
                  onProviderChange={(provider) => {
                    setLlmProvider(provider);
                    setLlmModel(modelOptions[provider][0]);
                  }}
                  onModelChange={setLlmModel}
                />

                <ScoreStepper currentStep={scoreStep} onChange={goToScoreStep} />

                {scoreStep === "upload" && (
                  <>
                    <div className="formSection">
                      <div className="sectionHeading">
                        <h3>Upload Inputs</h3>
                        <span>Resume + JD</span>
                      </div>
                      <div className="uploadGrid">
                        <div className="uploadCard">
                          <div className="uploadHeader">
                            <strong>Resume</strong>
                            <span>{uploading ? "Extracting..." : uploadInfo || "PDF, DOCX, or TXT"}</span>
                          </div>
                          <input type="file" accept=".txt,.pdf,.docx" onChange={(event) => uploadResume(event.target.files?.[0] ?? null)} />
                          <button type="button" className="tinyButton" onClick={() => setResumeSource(resumeSource === "file" ? "text" : "file")}>
                            {resumeSource === "file" ? "Use text editor" : "Show text editor"}
                          </button>
                        </div>
                        <div className="uploadCard">
                          <div className="uploadHeader">
                            <strong>Job Description</strong>
                            <span>{jdUploading ? "Extracting..." : jdUploadInfo || "PDF, DOCX, or TXT"}</span>
                          </div>
                          <input type="file" accept=".txt,.pdf,.docx" onChange={(event) => uploadJobDescription(event.target.files?.[0] ?? null)} />
                        </div>
                      </div>
                      <SavedResumeLibraryPanel
                        resumes={resumeHistory}
                        loading={historyLoading}
                        onRefresh={loadResumeLibrary}
                        onUse={useSavedResume}
                      />
                      <SavedJdLibraryPanel
                        jobDescriptions={jdHistory}
                        loading={historyLoading}
                        onRefresh={loadJdLibrary}
                        onUse={useSavedJd}
                      />
                      <div className="editorSplit">
                        <label>
                          Resume text
                          <textarea value={resumeText} onChange={(event) => updateResumeDraft(event.target.value)} rows={10} />
                        </label>
                        <label>
                          Job description text
                          <textarea value={jobDescriptionText} onChange={(event) => updateJdDraft(event.target.value)} rows={10} />
                        </label>
                      </div>
                    </div>

                    <div className="formSection">
                      <div className="sectionHeading">
                        <h3>Candidate Context</h3>
                        <span>Used by scorer</span>
                      </div>
                      <div className="gridTwo">
                        <label>
                          Target role
                          <input value={targetRole} onChange={(event) => setTargetRole(event.target.value)} />
                        </label>
                        <label>
                          Experience years
                          <input type="number" min={0} max={50} step="0.1" value={experienceYears} onChange={(event) => setExperienceYears(Number(event.target.value))} />
                        </label>
                      </div>
                      <label>
                        Current stack
                        <input value={currentStack} onChange={(event) => setCurrentStack(event.target.value)} />
                      </label>
                      <label>
                        Target market
                        <input value={targetMarket} onChange={(event) => setTargetMarket(event.target.value)} />
                      </label>
                      <div className="gridTwo">
                        <label>
                          Current location
                          <input value={currentLocation} onChange={(event) => setCurrentLocation(event.target.value)} />
                        </label>
                        <label>
                          Notice days
                          <input type="number" min={0} max={365} value={noticePeriodDays} onChange={(event) => setNoticePeriodDays(Number(event.target.value))} />
                        </label>
                      </div>
                      <label>
                        Preferred locations
                        <input value={preferredLocations} onChange={(event) => setPreferredLocations(event.target.value)} />
                      </label>
                      <div className="gridTwo">
                        <label>
                          Current CTC LPA
                          <input type="number" min={0} step="0.1" value={currentCtcLpa} onChange={(event) => setCurrentCtcLpa(event.target.value)} />
                        </label>
                        <label>
                          Expected CTC LPA
                          <input type="number" min={0} step="0.1" value={expectedCtcLpa} onChange={(event) => setExpectedCtcLpa(event.target.value)} />
                        </label>
                      </div>
                      <label>
                        Work mode preference
                        <input value={workModePreference} onChange={(event) => setWorkModePreference(event.target.value)} />
                      </label>
                      <label className="checkRow">
                        <input type="checkbox" checked={relocationOpen} onChange={(event) => setRelocationOpen(event.target.checked)} />
                        Open to relocation
                      </label>
                    </div>

                    <div className="actionBar">
                      <button type="button" className="secondaryButton" disabled={normalizing || resumeText.trim().length < 20} onClick={normalizeCurrentResume}>
                        {normalizing ? "Parsing..." : "Parse Resume"}
                      </button>
                      <button type="button" className="secondaryButton" disabled={parsingJd || jobDescriptionText.trim().length < 20} onClick={parseCurrentJd}>
                        {parsingJd ? "Parsing JD..." : "Parse JD"}
                      </button>
                      <button type="button" disabled={normalizing || parsingJd || resumeText.trim().length < 20 || jobDescriptionText.trim().length < 20} onClick={parseInputsForReview}>
                        {normalizing || parsingJd ? "Parsing..." : "Parse & Review"}
                      </button>
                    </div>
                  </>
                )}

                {scoreStep === "review" && (
                  <div className="reviewWorkspace compactReview">
                    <ReviewWorkspaceSummary resume={structuredResume} jd={parsedJd} resumeText={resumeText} jdText={jobDescriptionText} />
                    <ResumeParserDebugPanel
                      rawText={resumeParseSourceText}
                      normalizedText={resumeText}
                      resume={structuredResume}
                      parserDebug={resumeParserDebug}
                    />
                    <div className="reviewToggle">
                      <button type="button" className={reviewPane === "resume" ? "active" : ""} onClick={() => setReviewPane("resume")}>Resume Review</button>
                      <button type="button" className={reviewPane === "jd" ? "active" : ""} onClick={() => setReviewPane("jd")}>JD Review</button>
                    </div>
                    {reviewPane === "resume" && (structuredResume ? (
                      <StructuredResumeEditor
                        resume={structuredResume}
                        finalText={resumeText}
                        onChange={(nextResume) => {
                          setStructuredResume(nextResume);
                          setResumeText(formatStructuredResume(nextResume));
                        }}
                      />
                    ) : (
                      <EmptyState title="Resume needs parsing" body="Parse the resume to edit profile, education, projects, certifications, and skills before scoring." />
                    ))}
                    {reviewPane === "jd" && (parsedJd ? (
                      <ParsedJdEditor
                        parsedJd={parsedJd}
                        finalText={jobDescriptionText}
                        onChange={(nextJd) => {
                          setParsedJd(nextJd);
                          setJobDescriptionText(formatParsedJd(nextJd));
                        }}
                      />
                    ) : (
                      <EmptyState title="JD needs parsing" body="Parse the JD to review required, preferred, certification, and emphasized requirements before scoring." />
                    ))}
                    <div className="actionBar">
                      <button type="button" className="secondaryButton" onClick={() => setScoreStep("upload")}>Back</button>
                      <button type="button" className="secondaryButton" disabled={normalizing || resumeText.trim().length < 20} onClick={normalizeCurrentResume}>
                        {normalizing ? "Parsing..." : "Parse Resume"}
                      </button>
                      <button type="button" className="secondaryButton" disabled={parsingJd || jobDescriptionText.trim().length < 20} onClick={parseCurrentJd}>
                        {parsingJd ? "Parsing JD..." : "Parse JD"}
                      </button>
                      <button type="button" onClick={() => goToScoreStep("score")}>Next: Calculate Score</button>
                    </div>
                  </div>
                )}

                {scoreStep === "score" && (
                  <div className="formSection">
                    <div className="sectionHeading">
                      <h3>Score Calculator</h3>
                      <span>Free mandatory output</span>
                    </div>
                    <QuotaStatusPanel quota={usageQuota} onRefresh={loadCurrentQuota} onUpgrade={startCheckoutUpgrade} />
                    <div className="readyGrid">
                      <div><span>Resume status</span><strong>{structuredResume ? "Reviewed structure" : "Raw text"}</strong></div>
                      <div><span>JD status</span><strong>{parsedJd ? "Parsed requirements" : "Raw text"}</strong></div>
                      <div><span>Plan days</span><strong>{preparationPlanDays}</strong></div>
                      <div><span>Model mode</span><strong>{llmMode === "live" ? llmProvider : "mock"}</strong></div>
                    </div>
                    <PreScoreChecklist resume={structuredResume} jd={parsedJd} resumeText={resumeText} jdText={jobDescriptionText} />
                    <div className="actionBar">
                      <button type="button" className="secondaryButton" onClick={() => setScoreStep("review")}>Back to Review</button>
                      <button disabled={loading || !canCalculateScore}>
                        {loading ? "Matching..." : "Run Resume Match"}
                      </button>
                    </div>
                  </div>
                )}
                {normalizeInfo && <p className="hint">{normalizeInfo}</p>}
                {jdParseInfo && <p className="hint">{jdParseInfo}</p>}
                {historyInfo && <p className="hint">{historyInfo}</p>}
                {error && <p className="error">{error}</p>}
              </form>
            </TaskPanel>
          )}

          {activeTask === "review" && (
            <TaskPanel
              eyebrow="Input quality"
              title="Resume and JD Review"
              description="Fix parsed projects, certifications, profile data, and JD requirements before running or re-running the matcher."
            >
              <div className="reviewWorkspace">
                <ReviewWorkspaceSummary resume={structuredResume} jd={parsedJd} resumeText={resumeText} jdText={jobDescriptionText} />
                <ResumeParserDebugPanel
                  rawText={resumeParseSourceText}
                  normalizedText={resumeText}
                  resume={structuredResume}
                  parserDebug={resumeParserDebug}
                />
                <div className="actionBar">
                  <button type="button" className="secondaryButton" disabled={normalizing || resumeText.trim().length < 20} onClick={normalizeCurrentResume}>
                    {normalizing ? "Normalizing..." : "Normalize Resume"}
                  </button>
                  <button type="button" className="secondaryButton" disabled={parsingJd || jobDescriptionText.trim().length < 20} onClick={parseCurrentJd}>
                    {parsingJd ? "Parsing JD..." : "Parse JD"}
                  </button>
                  <button type="button" onClick={() => setActiveTask("matching")}>Back to Matching</button>
                </div>
                {normalizeInfo && <p className="hint">{normalizeInfo}</p>}
                {jdParseInfo && <p className="hint">{jdParseInfo}</p>}
                <div className="editorSplit">
                  <label>
                    Resume text
                    <textarea value={resumeText} onChange={(event) => updateResumeDraft(event.target.value)} rows={12} />
                  </label>
                  <label>
                    Job description text
                    <textarea value={jobDescriptionText} onChange={(event) => updateJdDraft(event.target.value)} rows={12} />
                  </label>
                </div>
                {structuredResume ? (
                  <StructuredResumeEditor
                    resume={structuredResume}
                    finalText={resumeText}
                    onChange={(nextResume) => {
                      setStructuredResume(nextResume);
                      setResumeText(formatStructuredResume(nextResume));
                    }}
                  />
                ) : (
                  <EmptyState title="Resume is not normalized yet" body="Normalize the resume to open the structured editor for profile, projects, certifications, and skills." />
                )}
                {parsedJd ? (
                  <ParsedJdEditor
                    parsedJd={parsedJd}
                    finalText={jobDescriptionText}
                    onChange={(nextJd) => {
                      setParsedJd(nextJd);
                      setJobDescriptionText(formatParsedJd(nextJd));
                    }}
                  />
                ) : (
                  <EmptyState title="JD is not parsed yet" body="Parse the JD to review required skills, certifications, seniority signals, and responsibilities." />
                )}
              </div>
            </TaskPanel>
          )}

          {activeTask === "report" && (
            <TaskPanel
              eyebrow="Task 1 output"
              title="Analysis Report"
              description="Mandatory match output only. Generate coaching artifacts separately when needed."
            >
              <ProductAccessPanel active="free" accessTier={effectiveAccessTier} onTierChange={updateAccountTier} />
              {historyInfo && <p className="hint">{historyInfo}</p>}
              {result && (
                <div className="costModePanel">
                  <div className="panelHeader">
                    <div>
                      <p className="eyebrow">AI Usage Mode</p>
                      <h3>Score-only by default</h3>
                      <p className="hint">The score is already generated. Run extra artifacts only when needed.</p>
                    </div>
                    <span className="costModeBadge">{costMode}</span>
                  </div>
                  <div className="costModeGrid">
                    <button
                      type="button"
                      className={costMode === "free" ? "costModeCard active" : "costModeCard"}
                      onClick={() => {
                        setCostMode("free");
                        setCostModeInfo("Free mode uses only the saved score and requirement matrix.");
                      }}
                    >
                      <strong>Free</strong>
                      <span>0 extra calls</span>
                      <small>Score, breakdown, requirement matrix, shortlisting factors.</small>
                    </button>
                    <button
                      type="button"
                      className={costMode === "standard" ? "costModeCard active" : "costModeCard"}
                      disabled={!canUsePremium || Boolean(artifactLoading) || preparing}
                      onClick={() => runCostModeBundle("standard")}
                    >
                      <strong>Standard</strong>
                      <span>2 extra calls</span>
                      <small>Resume improvements, then interview questions.</small>
                    </button>
                    <button
                      type="button"
                      className={costMode === "premium" ? "costModeCard active" : "costModeCard"}
                      disabled={!canUsePremium || Boolean(artifactLoading) || preparing}
                      onClick={() => runCostModeBundle("premium")}
                    >
                      <strong>Premium</strong>
                      <span>4 extra calls</span>
                      <small>Standard plus cross questions and preparation plan.</small>
                    </button>
                  </div>
                  {costModeInfo && <p className="hint">{costModeInfo}</p>}
                </div>
              )}
              {result && (
                <div className="actionBar">
                  <button
                    type="button"
                    className="secondaryButton premiumButton"
                    disabled={!canUsePremium || Boolean(artifactLoading) || preparing}
                    onClick={() => buildOptionalArtifact(
                      "Resume improvements",
                      "resume_improvements",
                      "/ai/resume-improvements",
                      (current, payload) => ({ ...current, resumeImprovements: payload as AnalysisResponse["resumeImprovements"] }),
                    )}
                  >
                    <span>Pro</span>
                    {artifactLoading === "Resume improvements" ? "Generating..." : "Generate Resume Improvements"}
                  </button>
                  <button
                    type="button"
                    className="secondaryButton premiumButton"
                    disabled={!canUsePremium || Boolean(artifactLoading) || preparing}
                    onClick={() => buildOptionalArtifact(
                      "Interview questions",
                      "interview_questions",
                      "/ai/interview/questions",
                      (current, payload) => ({ ...current, interviewQuestions: payload as AnalysisResponse["interviewQuestions"] }),
                    )}
                  >
                    <span>Pro</span>
                    {artifactLoading === "Interview questions" ? "Generating..." : "Generate Interview Questions"}
                  </button>
                  <button
                    type="button"
                    className="secondaryButton premiumButton"
                    disabled={!canUsePremium || Boolean(artifactLoading) || preparing}
                    onClick={() => buildOptionalArtifact(
                      "Cross questions",
                      "cross_questions",
                      "/ai/cross-questions",
                      (current, payload) => ({ ...current, crossQuestions: payload as AnalysisResponse["crossQuestions"] }),
                    )}
                  >
                    <span>Pro</span>
                    {artifactLoading === "Cross questions" ? "Generating..." : "Generate Cross Questions"}
                  </button>
                </div>
              )}
              {error && <p className="error">{error}</p>}
              {!result ? <EmptyState /> : <Results result={result} />}
            </TaskPanel>
          )}

          {activeTask === "preparation" && (
            <TaskPanel
              eyebrow="Task 2"
              title="Preparation Intelligence"
              description="This consumes the latest match result instead of reparsing the resume or JD, which keeps AI usage scoped."
            >
              <ProductAccessPanel active="premium" accessTier={effectiveAccessTier} onTierChange={updateAccountTier} compact />
              <div className="prepControls">
                <label>
                  Preparation plan days
                  <input type="number" min={1} max={30} value={preparationPlanDays} onChange={(event) => setPreparationPlanDays(Math.max(1, Math.min(30, Number(event.target.value) || 7)))} />
                </label>
                <button type="button" className="premiumButton" disabled={!canUsePremium || !result || preparing || Boolean(artifactLoading)} onClick={buildPreparation}>
                  <span>Pro</span>
                  {preparing ? "Building Plan..." : preparation ? "Rebuild Preparation Plan" : "Build Preparation Plan"}
                </button>
              </div>
              {preparationInfo && <p className="hint">{preparationInfo}</p>}
              {error && <p className="error">{error}</p>}
              {preparation ? <PreparationIntelligencePanel preparation={preparation} /> : <PreparationEmpty />}
            </TaskPanel>
          )}

          {activeTask === "progress" && (
            <TaskPanel
              eyebrow="Task 3"
              title="Preparation Progress"
              description="Track daily preparation tasks, notes, confidence, and completion from saved preparation sessions."
            >
              <ProductAccessPanel active="premium" accessTier={effectiveAccessTier} onTierChange={updateAccountTier} compact />
              <PreparationProgressTracker
                currentSession={activePreparationSession}
                sessions={preparationHistory}
                currentResult={result}
                saving={progressSaving}
                info={progressInfo}
                onSelectSession={setActivePreparationSession}
                onUpdate={updatePreparationProgress}
              />
              <PrepMemoryPanel memory={prepMemory} onRefresh={loadPrepMemory} onOpenAction={openPrepMemoryAction} />
            </TaskPanel>
          )}

          {activeTask === "history" && (
            <TaskPanel
              eyebrow="Task 4"
              title="User History"
              description="Saved resume versions, JD records, match reports, and preparation sessions from PostgreSQL."
            >
              <div className="actionBar">
                <button type="button" className="secondaryButton" disabled={historyLoading} onClick={loadHistory}>
                  {historyLoading ? "Loading History..." : "Refresh History"}
                </button>
                {historyInfo && <p className="hint">{historyInfo}</p>}
              </div>
              <HistoryPanel
                summary={workspaceSummary}
                analyses={analysisHistory}
                resumes={resumeHistory}
                jobDescriptions={jdHistory}
                preparations={preparationHistory}
                opportunities={jobOpportunityHistory}
                opportunityActions={opportunityActions}
                comparisons={comparisonHistory}
                currentResult={result}
                onOpportunityStatusChange={updateJobOpportunityStatus}
                onOpportunityArtifactBuild={buildOpportunityArtifact}
                artifactLoading={artifactLoading}
              />
            </TaskPanel>
          )}

          {activeTask === "compare" && (
            <TaskPanel
              eyebrow="Task 5"
              title="Saved Comparison"
              description="Run score-only comparisons across saved resumes and saved JDs without generating premium artifacts."
            >
              <ComparisonPanel
                resumes={resumeHistory}
                jobDescriptions={jdHistory}
                selectedResumeIds={comparisonResumeIds}
                selectedJobDescriptionIds={comparisonJdIds}
                results={comparisonResults}
                history={comparisonHistory}
                accessTier={effectiveAccessTier}
                loading={comparisonLoading}
                info={comparisonInfo}
                onToggleResume={toggleComparisonResume}
                onToggleJobDescription={toggleComparisonJd}
                onRefresh={() => {
                  void loadResumeLibrary();
                  void loadJdLibrary();
                  void loadComparisonHistory();
                }}
                onLoadHistory={loadComparisonRun}
                onRenameHistory={renameComparisonRun}
                onDeleteHistory={deleteComparisonRun}
                onRun={runComparison}
                onTierChange={updateAccountTier}
              />
            </TaskPanel>
          )}

          {activeTask === "research" && (
            <TaskPanel
              eyebrow="Phase 7"
              title="Research Notes"
              description="Save company, role, market, and interview signals as reusable workspace memory before live research agents are added."
            >
              <ResearchNotesPanel
                notes={researchNotes}
                title={researchTitle}
                company={researchCompany}
                roleTitle={researchRoleTitle}
                researchType={researchType}
                summary={researchSummary}
                keySignals={researchKeySignals}
                preparationTopics={researchPreparationTopics}
                manualContext={researchManualContext}
                sourcesDraft={researchSourcesDraft}
                draftProvider={researchDraftProvider}
                draftWarnings={researchDraftWarnings}
                draftMarketSignals={researchDraftMarketSignals}
                draftSynthesis={researchDraftSynthesis}
                saving={researchSaving}
                generating={researchGenerating}
                info={researchInfo}
                onTitleChange={setResearchTitle}
                onCompanyChange={setResearchCompany}
                onRoleTitleChange={setResearchRoleTitle}
                onResearchTypeChange={setResearchType}
                onSummaryChange={setResearchSummary}
                onKeySignalsChange={setResearchKeySignals}
                onPreparationTopicsChange={setResearchPreparationTopics}
                onManualContextChange={setResearchManualContext}
                onSourcesDraftChange={setResearchSourcesDraft}
                onGenerate={generateResearchDraft}
                onSave={saveResearchNote}
                onRefresh={loadResearchNotes}
              />
            </TaskPanel>
          )}

          {activeTask === "decision" && (
            <TaskPanel
              eyebrow="Phase 8"
              title="Apply Decision"
              description="Combine the match score, shortlisting signals, and saved research notes into an apply / prepare / skip decision."
            >
              <ApplicationDecisionPanel
                decision={applicationDecision}
                result={result}
                researchNotes={researchNotes}
                loading={decisionLoading}
                info={decisionInfo}
                accessTier={effectiveAccessTier}
                onBuild={buildApplicationDecision}
                onTierChange={updateAccountTier}
              />
            </TaskPanel>
          )}

          {activeTask === "agent" && (
            <TaskPanel
              eyebrow="Phase 8"
              title="Career Agent Plan"
              description="Choose the next optional module from the saved score, research memory, preparation state, and generated artifacts."
            >
              <AgentPlanPanel
                plan={agentPlan}
                result={result}
                loading={agentLoading}
                info={agentInfo}
                accessTier={effectiveAccessTier}
                researchNotes={researchNotes}
                artifacts={currentGeneratedArtifacts(result)}
                onBuild={buildAgentPlan}
                onRunRecommendation={runAgentRecommendation}
                onTierChange={updateAccountTier}
              />
            </TaskPanel>
          )}

          {activeTask === "rewrite" && (
            <TaskPanel
              eyebrow="Phase 8"
              title="Resume Rewrite"
              description="Generate evidence-constrained resume bullets tied to existing proof, with gap warnings when a claim would be unsafe."
            >
              <ResumeRewritePanel
                rewrite={resumeRewrite}
                result={result}
                loading={rewriteLoading}
                info={rewriteInfo}
                accessTier={effectiveAccessTier}
                appliedKeys={appliedRewriteKeys}
                acceptedRewrites={acceptedResumeRewrites}
                resumeVersions={resumeVersions}
                resumeVersionRestores={resumeVersionRestores}
                versionComparison={selectedResumeVersionComparison}
                onBuild={buildResumeRewrite}
                onApplySuggestion={applyRewriteSuggestion}
                onCompareVersion={compareResumeVersion}
                onRestoreVersion={restoreResumeVersion}
                onTierChange={updateAccountTier}
              />
            </TaskPanel>
          )}

          {activeTask === "extension" && (
            <TaskPanel
              eyebrow="Task 7"
              title="Extension Setup"
              description="Install and connect the browser extension for job-page scoring with saved resumes."
            >
              <ExtensionSetupPanel
                backendUrl={API_BASE_URL}
                workspaceUserId={workspaceUserId}
                checking={extensionChecking}
                setupInfo={extensionSetupInfo}
                resumeCount={extensionResumeCount}
                diagnostics={extensionDiagnostics}
                validations={extensionValidations}
                validationInfo={extensionValidationInfo}
                onCheck={checkExtensionSetup}
                onSaveValidation={saveExtensionValidation}
              />
            </TaskPanel>
          )}

          {activeTask === "evaluation" && (
            <TaskPanel
              eyebrow="Phase 6"
              title="Score Evaluation"
              description="Label real analysis results so the scoring weights can be tuned from evidence instead of assumptions."
            >
              <EvaluationPanel
                result={result}
                lastSavedAnalysisId={lastSavedAnalysisId}
                summary={evaluationSummary}
                info={evaluationInfo}
                onRefresh={loadEvaluationSummary}
                onSaveFeedback={saveMatchFeedback}
                onExportDataset={exportEvaluationDataset}
                onImportDataset={importEvaluationDataset}
              />
            </TaskPanel>
          )}

          {activeTask === "settings" && (
            <TaskPanel
              eyebrow="Admin"
              title="Scoring Settings"
              description="View and safely edit role-family scoring weights. Weights must total 100 before saving."
            >
              <ScoringSettingsPanel
                configs={scoringConfigs}
                recommendation={scoringRecommendation}
                audit={scoringAudit}
                diagnostics={systemDiagnostics}
                productionReadiness={productionReadiness}
                users={adminUsers}
                adminAnalyses={adminAnalyses}
                usageSummary={usageSummary}
                billingDraft={billingDraft}
                demoSeedResult={demoSeedResult}
                launchChecklist={launchChecklist}
                canManageSettings={currentUser?.role === "admin"}
                info={settingsInfo}
                onRefresh={loadScoringConfigs}
                onSave={saveScoringConfig}
                onRecommend={loadScoringRecommendation}
                onLoadAudit={loadScoringAudit}
                onRestore={restoreScoringConfig}
                onRefreshDiagnostics={loadSystemDiagnostics}
                onRefreshReadiness={loadProductionReadiness}
                onRefreshUsers={loadAdminUsers}
                onSearchAnalyses={loadAdminAnalyses}
                onLoadUsage={loadUsageSummary}
                onBillingEdit={startBillingEdit}
                onBillingDraftChange={setBillingDraft}
                onBillingSave={saveBillingMetadata}
                onBillingCancel={() => setBillingDraft(null)}
                onSeedDemo={seedDemoWorkspace}
                onToggleLaunchChecklist={updateLaunchChecklist}
                onResetLaunchChecklist={resetLaunchChecklist}
              />
            </TaskPanel>
          )}
        </section>
      </section>
    </main>
  );
}

function SessionStatusPanel({
  userId,
  draftUserId,
  sessionInfo,
  currentUser,
  currentRole,
  authPassword,
  authDisplayName,
  authEmail,
  accountTier,
  effectiveAccessTier,
  workspaceSummary,
  onDraftUserChange,
  onPasswordChange,
  onDisplayNameChange,
  onEmailChange,
  onAccountTierChange,
  onApplyUser,
  onLogin,
  onRegister,
  onReconnect,
  onClear,
}: {
  userId: string;
  draftUserId: string;
  sessionInfo: string;
  currentUser: AdminUserRecord | null;
  currentRole: string;
  authPassword: string;
  authDisplayName: string;
  authEmail: string;
  accountTier: AccessTier;
  effectiveAccessTier: AccessTier;
  workspaceSummary: WorkspaceSummary | null;
  onDraftUserChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onDisplayNameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onAccountTierChange: (value: AccessTier) => void;
  onApplyUser: () => void;
  onLogin: () => void;
  onRegister: () => void;
  onReconnect: () => void;
  onClear: () => void;
}) {
  return (
    <div className="authProfilePanel">
      <div className="profileIdentity">
        <div>
          <span>Active profile</span>
          <strong>{currentUser?.displayName || userId}</strong>
          <small>{currentUser?.email || "No email saved"} | Role: {currentRole}</small>
        </div>
        <div className="sessionPill">{sessionInfo}</div>
      </div>

      <div className="profileStats">
        <div><span>Resumes</span><strong>{workspaceSummary?.resumeCount ?? 0}</strong></div>
        <div><span>Reports</span><strong>{workspaceSummary?.analysisCount ?? 0}</strong></div>
        <div><span>Plans</span><strong>{workspaceSummary?.preparationSessionCount ?? 0}</strong></div>
        <div><span>Jobs</span><strong>{workspaceSummary?.jobOpportunityCount ?? 0}</strong></div>
        <div><span>Avg score</span><strong>{workspaceSummary?.averageMatchScore ?? "--"}%</strong></div>
        <div><span>Active jobs</span><strong>{workspaceSummary?.activeOpportunityCount ?? 0}</strong></div>
      </div>

      <div className="authFormGrid">
        <label>
          User id or email
          <input value={draftUserId} onChange={(event) => onDraftUserChange(event.target.value)} placeholder="local-aditya or email" />
        </label>
        <label>
          Display name
          <input value={authDisplayName} onChange={(event) => onDisplayNameChange(event.target.value)} placeholder="Your name" />
        </label>
        <label>
          Email
          <input type="email" value={authEmail} onChange={(event) => onEmailChange(event.target.value)} placeholder="you@example.com" />
        </label>
        <label>
          Password
          <input type="password" value={authPassword} onChange={(event) => onPasswordChange(event.target.value)} placeholder="8+ characters" />
        </label>
        <label>
          Access tier
          <select value={accountTier} disabled={effectiveAccessTier === "admin"} onChange={(event) => onAccountTierChange(event.target.value as AccessTier)}>
            <option value="free">Free</option>
            <option value="premium">Premium</option>
          </select>
        </label>
      </div>

      <div className="sessionActions profileActions">
        <span className={`tierBadge ${effectiveAccessTier}`}>{effectiveAccessTier}</span>
        <button type="button" className="secondaryButton" onClick={onApplyUser}>Use User</button>
        <button type="button" className="secondaryButton" onClick={onLogin}>Login</button>
        <button type="button" className="secondaryButton" onClick={onRegister}>Register</button>
        <button type="button" className="secondaryButton" onClick={onReconnect}>Refresh</button>
        <button type="button" className="secondaryButton" onClick={onClear}>Logout</button>
      </div>
    </div>
  );
}

function EmptyState({
  title = "Ready to test the contract",
  body = "Submit the sample data to verify the frontend, API endpoint, and response rendering before we plug in a real LLM.",
}: {
  title?: string;
  body?: string;
}) {
  return (
    <div className="panel empty">
      <h2>{title}</h2>
      <p>{body}</p>
    </div>
  );
}

function SavedResumeLibraryPanel({
  resumes,
  loading,
  onRefresh,
  onUse,
}: {
  resumes: HistoryResumeRecord[];
  loading: boolean;
  onRefresh: () => void;
  onUse: (resume: HistoryResumeRecord) => void;
}) {
  return (
    <div className="savedResumePanel">
      <div className="panelHeader">
        <div>
          <p className="eyebrow">Resume Library</p>
          <h3>Reuse Saved Resume</h3>
          <p className="hint">Pick a saved resume snapshot instead of uploading or pasting again.</p>
        </div>
        <button type="button" className="secondaryButton" disabled={loading} onClick={onRefresh}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>
      {resumes.length ? (
        <div className="savedResumeGrid">
          {resumes.slice(0, 6).map((resume) => {
            const structured = resume.structuredResume;
            return (
              <div className="savedResumeCard" key={resume.id}>
                <div>
                  <strong>{resume.title}</strong>
                  <span>{resume.source} | {formatDate(resume.createdAt)}</span>
                </div>
                <small>
                  {structured
                    ? `${structured.experience.length} exp | ${structured.projects.length} project(s) | ${structured.skills.length} skill(s)`
                    : "Raw resume snapshot"}
                </small>
                <button type="button" className="secondaryButton" onClick={() => onUse(resume)}>Use Resume</button>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="emptyLibraryState">
          <strong>No saved resumes yet</strong>
          <span>Run one match or save a resume snapshot, then it will be reusable here and in the extension.</span>
        </div>
      )}
    </div>
  );
}

function SavedJdLibraryPanel({
  jobDescriptions,
  loading,
  onRefresh,
  onUse,
}: {
  jobDescriptions: HistoryJobDescriptionRecord[];
  loading: boolean;
  onRefresh: () => void;
  onUse: (jobDescription: HistoryJobDescriptionRecord) => void;
}) {
  return (
    <div className="savedResumePanel">
      <div className="panelHeader">
        <div>
          <p className="eyebrow">JD Library</p>
          <h3>Reuse Saved Job Description</h3>
          <p className="hint">Load a previous JD to compare new resume versions or rerun scoring after edits.</p>
        </div>
        <button type="button" className="secondaryButton" disabled={loading} onClick={onRefresh}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>
      {jobDescriptions.length ? (
        <div className="savedResumeGrid">
          {jobDescriptions.slice(0, 6).map((jobDescription) => {
            const parsed = jobDescription.parsedJobDescription;
            return (
              <div className="savedResumeCard" key={jobDescription.id}>
                <div>
                  <strong>{jobDescription.title}</strong>
                  <span>{[jobDescription.company, formatDate(jobDescription.createdAt)].filter(Boolean).join(" | ")}</span>
                </div>
                <small>
                  {parsed
                    ? `${parsed.requiredSkills.length} required | ${parsed.preferredSkills.length} preferred | ${parsed.emphasizedRequirements.length} emphasized`
                    : "Raw JD snapshot"}
                </small>
                <button type="button" className="secondaryButton" onClick={() => onUse(jobDescription)}>Use JD</button>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="emptyLibraryState">
          <strong>No saved JDs yet</strong>
          <span>Run one match or save a JD snapshot, then it will be reusable here for comparison workflows.</span>
        </div>
      )}
    </div>
  );
}

function ProductAccessPanel({
  active,
  accessTier,
  onTierChange,
  compact = false,
}: {
  active: "free" | "premium";
  accessTier: AccessTier;
  onTierChange: (tier: AccessTier) => void;
  compact?: boolean;
}) {
  const premiumUnlocked = accessTier === "premium" || accessTier === "admin";
  return (
    <div className={compact ? "productAccessPanel compact" : "productAccessPanel"}>
      <div className={active === "free" ? "accessTier active" : "accessTier"}>
        <div>
          <span>Free</span>
          <strong>Match Score</strong>
        </div>
        <small>Score, breakdown, requirement matrix, shortlisting factors.</small>
      </div>
      <div className={active === "premium" ? "accessTier premium active" : "accessTier premium"}>
        <div>
          <span>Premium</span>
          <strong>Career Intelligence</strong>
        </div>
        <small>{premiumUnlocked ? "Unlocked for this workspace." : "Locked until the workspace tier is Premium."} Resume rewrite ideas, interview pack, cross-questions, preparation plan, progress tracking.</small>
      </div>
      <div className="accessNote">
        <strong>{accessTier === "admin" ? "Admin access" : premiumUnlocked ? "Premium active" : "Free tier active"}</strong>
        <span>{premiumUnlocked ? "Optional AI modules are available and still run only after explicit clicks." : "Score stays free. Premium actions are disabled to avoid accidental AI spend."}</span>
        {accessTier !== "admin" && (
          <button type="button" className="tinyButton" onClick={() => onTierChange(premiumUnlocked ? "free" : "premium")}>
            {premiumUnlocked ? "Switch to Free" : "Unlock Premium"}
          </button>
        )}
      </div>
    </div>
  );
}

function ComparisonPanel({
  resumes,
  jobDescriptions,
  selectedResumeIds,
  selectedJobDescriptionIds,
  results,
  history,
  accessTier,
  loading,
  info,
  onToggleResume,
  onToggleJobDescription,
  onRefresh,
  onLoadHistory,
  onRenameHistory,
  onDeleteHistory,
  onRun,
  onTierChange,
}: {
  resumes: HistoryResumeRecord[];
  jobDescriptions: HistoryJobDescriptionRecord[];
  selectedResumeIds: string[];
  selectedJobDescriptionIds: string[];
  results: ComparisonResult[];
  history: HistoryComparisonRecord[];
  accessTier: AccessTier;
  loading: boolean;
  info: string;
  onToggleResume: (id: string) => void;
  onToggleJobDescription: (id: string) => void;
  onRefresh: () => void;
  onLoadHistory: (record: HistoryComparisonRecord) => void;
  onRenameHistory: (record: HistoryComparisonRecord) => void;
  onDeleteHistory: (record: HistoryComparisonRecord) => void;
  onRun: () => void;
  onTierChange: (tier: AccessTier) => void;
}) {
  const runCount = selectedResumeIds.length * selectedJobDescriptionIds.length;
  return (
    <div className="comparisonWorkspace">
      <ProductAccessPanel active="free" accessTier={accessTier} onTierChange={onTierChange} compact />
      <div className="comparisonToolbar">
        <div>
          <strong>{runCount} score-only run(s) selected</strong>
          <span>Cap: 9 combinations. Premium artifacts are not generated here.</span>
        </div>
        <div className="actionBar">
          <button type="button" className="secondaryButton" onClick={onRefresh}>Refresh Libraries</button>
          <button type="button" disabled={loading || runCount < 1 || runCount > 9} onClick={onRun}>
            {loading ? "Comparing..." : "Run Comparison"}
          </button>
        </div>
      </div>

      <div className="comparisonGrid">
        <section className="panel">
          <h3>Saved Resumes</h3>
          <div className="selectionList">
            {resumes.length ? resumes.slice(0, 12).map((resume) => (
              <label key={resume.id} className="selectionRow">
                <input type="checkbox" checked={selectedResumeIds.includes(resume.id)} onChange={() => onToggleResume(resume.id)} />
                <span>
                  <strong>{resume.title}</strong>
                  <small>{resume.source} | {formatDate(resume.createdAt)}</small>
                </span>
              </label>
            )) : <p className="hint">No saved resumes yet.</p>}
          </div>
        </section>

        <section className="panel">
          <h3>Saved JDs</h3>
          <div className="selectionList">
            {jobDescriptions.length ? jobDescriptions.slice(0, 12).map((jd) => (
              <label key={jd.id} className="selectionRow">
                <input type="checkbox" checked={selectedJobDescriptionIds.includes(jd.id)} onChange={() => onToggleJobDescription(jd.id)} />
                <span>
                  <strong>{jd.title}</strong>
                  <small>{[jd.company, formatDate(jd.createdAt)].filter(Boolean).join(" | ")}</small>
                </span>
              </label>
            )) : <p className="hint">No saved JDs yet.</p>}
          </div>
        </section>
      </div>

      {info && <p className="hint">{info}</p>}

      <div className="comparisonGrid">
        <section className="panel">
          <div className="panelHeader">
            <div>
              <p className="eyebrow">History</p>
              <h3>Recent Runs</h3>
            </div>
          </div>
          <div className="compactList">
            {history.length ? history.slice(0, 8).map((record) => (
              <div key={record.id}>
                <strong>{record.title}</strong>
                <span>{record.results.length} result(s) | best {record.results[0]?.score ?? 0}% | {formatDate(record.createdAt)}</span>
                <div className="inlineActions">
                  <button type="button" className="tinyButton" onClick={() => onLoadHistory(record)}>Load Results</button>
                  <button type="button" className="tinyButton" onClick={() => onRenameHistory(record)}>Rename</button>
                  <button type="button" className="tinyButton dangerTinyButton" onClick={() => onDeleteHistory(record)}>Delete</button>
                </div>
              </div>
            )) : (
              <div>
                <strong>No saved comparisons</strong>
                <span>Run a comparison to create a reusable ranked snapshot.</span>
              </div>
            )}
          </div>
        </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Results</p>
            <h3>Ranked Comparison</h3>
          </div>
        </div>
        {results.length ? (
          <div className="comparisonResults">
            {results.map((item, index) => (
              <div className="comparisonResult" key={item.id}>
                <span>#{index + 1}</span>
                <div>
                  <strong>{item.score}% - {item.fitCategory}</strong>
                  <small>{item.resumeTitle} against {item.jobTitle}{item.company ? ` at ${item.company}` : ""}</small>
                  {item.recommendedAction && <p>{item.recommendedAction}</p>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="hint">Run a comparison to see ranked score-only results.</p>
        )}
      </section>
      </div>
    </div>
  );
}

function TaskNav({
  activeTask,
  onChange,
  hasResult,
  hasPreparation,
  resumeReady,
  jdReady,
}: {
  activeTask: ActiveTask;
  onChange: (task: ActiveTask) => void;
  hasResult: boolean;
  hasPreparation: boolean;
  resumeReady: boolean;
  jdReady: boolean;
}) {
  const tasks: Array<{
    id: ActiveTask;
    label: string;
    description: string;
    status: string;
  }> = [
    {
      id: "command",
      label: "Command Center",
      description: "Next best actions",
      status: hasResult ? "Active" : "Start here",
    },
    {
      id: "matching",
      label: "Resume Matching",
      description: "Resume + JD fit scoring",
      status: resumeReady && jdReady ? "Ready" : "Needs input",
    },
    {
      id: "review",
      label: "Input Review",
      description: "Fix parsed resume and JD",
      status: resumeReady || jdReady ? "Available" : "Needs input",
    },
    {
      id: "report",
      label: "Analysis Report",
      description: "Matrix, scores, gaps",
      status: hasResult ? "Generated" : "Run matching",
    },
    {
      id: "preparation",
      label: "Preparation Plan",
      description: "Study plan from gaps",
      status: hasPreparation ? "Generated" : "Needs report",
    },
    {
      id: "progress",
      label: "Progress Tracker",
      description: "Daily prep and practice",
      status: "Next backend",
    },
    {
      id: "history",
      label: "User History",
      description: "Saved resumes and reports",
      status: "PostgreSQL",
    },
    {
      id: "compare",
      label: "Saved Comparison",
      description: "Resume/JD score grid",
      status: "Score-only",
    },
    {
      id: "research",
      label: "Research Notes",
      description: "Company and role signals",
      status: "Phase 7",
    },
    {
      id: "agent",
      label: "Career Agent",
      description: "Next best paid module",
      status: hasResult ? "Plan ready" : "Needs score",
    },
    {
      id: "decision",
      label: "Apply Decision",
      description: "Apply, prep, or skip",
      status: hasResult ? "Ready" : "Needs score",
    },
    {
      id: "rewrite",
      label: "Resume Rewrite",
      description: "Evidence-safe bullets",
      status: hasResult ? "Ready" : "Needs score",
    },
    {
      id: "extension",
      label: "Extension Setup",
      description: "Install and connect",
      status: "Ready",
    },
    {
      id: "evaluation",
      label: "Score Evaluation",
      description: "Label score quality",
      status: hasResult ? "Ready" : "Collect data",
    },
    {
      id: "settings",
      label: "Scoring Settings",
      description: "Role-family weights",
      status: "Admin",
    },
  ];

  return (
    <aside className="taskNav" aria-label="Career Agent tasks">
      <div className="taskNavHeader">
        <span>Workspace</span>
        <strong>Purpose first</strong>
      </div>
      {tasks.map((task) => (
        <button
          key={task.id}
          type="button"
          className={activeTask === task.id ? "taskButton active" : "taskButton"}
          onClick={() => onChange(task.id)}
        >
          <span>{task.label}</span>
          <small>{task.description}</small>
          <em>{task.status}</em>
        </button>
      ))}
    </aside>
  );
}

function TaskPanel({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="taskPanel">
      <div className="taskPanelHeader">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function CommandCenterPanel({
  result,
  agentPlan,
  prepMemory,
  opportunityActions,
  workspaceSummary,
  info,
  loading,
  onOpenTask,
  onRefresh,
  onBuildAgentPlan,
  onRunAgentRecommendation,
  onOpenPrepAction,
  onRunOpportunityAction,
}: {
  result: AnalysisResponse | null;
  agentPlan: AgentPlanResponse | null;
  prepMemory: PrepMemoryResponse | null;
  opportunityActions: OpportunityNextActionsResponse | null;
  workspaceSummary: WorkspaceSummary | null;
  info: string;
  loading: boolean;
  onOpenTask: (task: ActiveTask) => void;
  onRefresh: () => void;
  onBuildAgentPlan: () => void;
  onRunAgentRecommendation: (tool: AgentPlanResponse["recommendations"][number]["tool"]) => void;
  onOpenPrepAction: (action: NonNullable<PrepMemoryResponse["nextAction"]>) => void;
  onRunOpportunityAction: (action: OpportunityNextAction) => void;
}) {
  const agentRecommendation = agentPlan?.recommendations.find((item) => !item.alreadySatisfied) ?? null;
  const prepAction = prepMemory?.nextAction ?? null;
  const opportunityAction = opportunityActions?.actions[0] ?? null;

  return (
    <div className="commandCenter">
      <section className="panel commandHero">
        <div>
          <p className="eyebrow">Operating System</p>
          <h3>{result ? `${result.technicalMatchScore}% - ${result.fitCategory}` : "Run the first score"}</h3>
          <p>{result?.overallSummary ?? "Start with resume matching. After that, this view coordinates paid artifacts, prep progress, and job pipeline actions."}</p>
          <div className="inlineActions">
            <button type="button" className="secondaryButton" disabled={loading} onClick={onRefresh}>
              {loading ? "Refreshing..." : "Refresh Command Center"}
            </button>
            {info && <small>{info}</small>}
          </div>
        </div>
        <div className="commandMetrics">
          <div><span>Reports</span><strong>{workspaceSummary?.analysisCount ?? 0}</strong></div>
          <div><span>Jobs</span><strong>{workspaceSummary?.jobOpportunityCount ?? 0}</strong></div>
          <div><span>Plans</span><strong>{workspaceSummary?.preparationSessionCount ?? 0}</strong></div>
        </div>
      </section>

      <div className="commandGrid">
        <CommandActionCard
          label="Career Agent"
          title={agentPlan?.nextBestAction ?? "Build next-step plan"}
          body={agentPlan?.headline ?? "Generate a planner view from the latest score and workspace memory."}
          primaryLabel={agentRecommendation ? "Run Recommendation" : "Build Plan"}
          secondaryLabel="Open Planner"
          onPrimary={() => agentRecommendation ? onRunAgentRecommendation(agentRecommendation.tool) : onBuildAgentPlan()}
          onSecondary={() => onOpenTask("agent")}
          disabledPrimary={!result}
        />
        <CommandActionCard
          label="Preparation"
          title={prepAction?.label ?? "No prep action yet"}
          body={prepAction?.task ? `Day ${prepAction.day ?? ""}: ${prepAction.task}` : prepAction?.reason ?? "Build a preparation plan or load saved prep memory."}
          primaryLabel={prepAction ? "Open Action" : "Open Progress"}
          secondaryLabel="Open Prep"
          onPrimary={() => prepAction ? onOpenPrepAction(prepAction) : onOpenTask("progress")}
          onSecondary={() => onOpenTask("preparation")}
        />
        <CommandActionCard
          label="Pipeline"
          title={opportunityAction?.action ?? "No pipeline action yet"}
          body={opportunityAction?.reason ?? opportunityActions?.summary ?? "Save extension matches or refresh history to build opportunity actions."}
          primaryLabel={opportunityAction?.artifactKey ? "Generate" : opportunityAction?.recommendedStatus ? "Apply" : "Open History"}
          secondaryLabel="Open Pipeline"
          onPrimary={() => opportunityAction ? onRunOpportunityAction(opportunityAction) : onOpenTask("history")}
          onSecondary={() => onOpenTask("history")}
        />
        <CommandActionCard
          label="Score"
          title={result ? "Review latest report" : "Run score-only match"}
          body={result ? "Inspect requirement matrix and generate optional artifacts one at a time." : "Upload, parse, review, then calculate the free score."}
          primaryLabel={result ? "Open Report" : "Open Matching"}
          secondaryLabel="Review Inputs"
          onPrimary={() => onOpenTask(result ? "report" : "matching")}
          onSecondary={() => onOpenTask("review")}
        />
      </div>
    </div>
  );
}

function CommandActionCard({
  label,
  title,
  body,
  primaryLabel,
  secondaryLabel,
  onPrimary,
  onSecondary,
  disabledPrimary = false,
}: {
  label: string;
  title: string;
  body: string;
  primaryLabel: string;
  secondaryLabel: string;
  onPrimary: () => void;
  onSecondary: () => void;
  disabledPrimary?: boolean;
}) {
  return (
    <article className="commandCard">
      <span>{label}</span>
      <h3>{title}</h3>
      <p>{body}</p>
      <div>
        <button type="button" disabled={disabledPrimary} onClick={onPrimary}>{primaryLabel}</button>
        <button type="button" className="secondaryButton" onClick={onSecondary}>{secondaryLabel}</button>
      </div>
    </article>
  );
}

function ExtensionSetupPanel({
  backendUrl,
  workspaceUserId,
  checking,
  setupInfo,
  resumeCount,
  diagnostics,
  validations,
  validationInfo,
  onCheck,
  onSaveValidation,
}: {
  backendUrl: string;
  workspaceUserId: string;
  checking: boolean;
  setupInfo: string;
  resumeCount: number | null;
  diagnostics: ExtensionDiagnostics | null;
  validations: ExtensionValidationRecord[];
  validationInfo: string;
  onCheck: () => void;
  onSaveValidation: (payload: {
    site: string;
    url: string;
    parserRating: "pass" | "partial" | "fail";
    autoParsed: boolean;
    manualPasteUsed: boolean;
    titleFound: boolean;
    companyFound: boolean;
    descriptionFound: boolean;
    notes: string;
  }) => void;
}) {
  const [site, setSite] = useState("LinkedIn");
  const [url, setUrl] = useState("");
  const [parserRating, setParserRating] = useState<"pass" | "partial" | "fail">("partial");
  const [autoParsed, setAutoParsed] = useState(true);
  const [manualPasteUsed, setManualPasteUsed] = useState(false);
  const [titleFound, setTitleFound] = useState(true);
  const [companyFound, setCompanyFound] = useState(true);
  const [descriptionFound, setDescriptionFound] = useState(false);
  const [notes, setNotes] = useState("");

  return (
    <div className="extensionSetupGrid">
      <div className="panel extensionSetupHero">
        <div>
          <p className="eyebrow">Browser Extension</p>
          <h3>Score jobs from LinkedIn, Naukri, Indeed, or pasted JD text</h3>
          <p>The extension uses the same score-first API. It parses the page, lets you review/paste JD text, then matches only when you click the match button.</p>
        </div>
        <div className="extensionStatusGrid">
          <div className="metaBlock">
            <span>Backend</span>
            <strong>{backendUrl}</strong>
          </div>
          <div className="metaBlock">
            <span>Workspace user</span>
            <strong>{workspaceUserId}</strong>
          </div>
          <div className="metaBlock">
            <span>Saved resumes</span>
            <strong>{resumeCount === null ? "Check needed" : resumeCount}</strong>
          </div>
        </div>
        <button type="button" className="secondaryButton" disabled={checking} onClick={onCheck}>
          {checking ? "Checking..." : "Check Extension Readiness"}
        </button>
        {setupInfo && <p className="hint">{setupInfo}</p>}
        {diagnostics && (
          <div className="diagnosticGrid">
            <div>
              <h4>Checks</h4>
              <ul>{diagnostics.checks.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
            <div>
              <h4>Warnings</h4>
              {diagnostics.warnings.length ? (
                <ul>{diagnostics.warnings.map((item) => <li key={item}>{item}</li>)}</ul>
              ) : (
                <p className="hint">No warnings. Extension matching is ready for saved resumes.</p>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="panel">
        <h3>Install Steps</h3>
        <ol className="setupSteps">
          <li>Open Chrome or Edge extensions page.</li>
          <li>Enable Developer mode.</li>
          <li>Choose Load unpacked.</li>
          <li>Select <code>C:\Code\AI\career-agent-os\extension</code>.</li>
          <li>Open a job page, click the extension, then connect with <code>{workspaceUserId}</code>.</li>
        </ol>
      </div>

      <div className="panel">
        <h3>How Connection Works</h3>
        <ul>
          <li>The extension starts with an anonymous session.</li>
          <li>Connect creates a server-issued session token and stores it in browser extension storage.</li>
          <li>Future matches use that token to load saved resumes and save job history under the user.</li>
          <li>Manual JD paste remains available when page parsing is weak.</li>
        </ul>
      </div>

      <div className="panel validationPanel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Real Site Validation</p>
            <h3>Record parser quality</h3>
          </div>
          <span>{validations.length} saved</span>
        </div>
        <div className="gridTwo">
          <label>
            Site
            <select value={site} onChange={(event) => setSite(event.target.value)}>
              <option>LinkedIn</option>
              <option>Naukri</option>
              <option>Indeed</option>
              <option>Company career page</option>
              <option>Other</option>
            </select>
          </label>
          <label>
            Parser result
            <select value={parserRating} onChange={(event) => setParserRating(event.target.value as "pass" | "partial" | "fail")}>
              <option value="pass">Pass</option>
              <option value="partial">Partial</option>
              <option value="fail">Fail</option>
            </select>
          </label>
        </div>
        <label>
          Page URL
          <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://..." />
        </label>
        <div className="checkGrid">
          <label><input type="checkbox" checked={autoParsed} onChange={(event) => setAutoParsed(event.target.checked)} /> Auto parsed</label>
          <label><input type="checkbox" checked={manualPasteUsed} onChange={(event) => setManualPasteUsed(event.target.checked)} /> Manual paste used</label>
          <label><input type="checkbox" checked={titleFound} onChange={(event) => setTitleFound(event.target.checked)} /> Role found</label>
          <label><input type="checkbox" checked={companyFound} onChange={(event) => setCompanyFound(event.target.checked)} /> Company found</label>
          <label><input type="checkbox" checked={descriptionFound} onChange={(event) => setDescriptionFound(event.target.checked)} /> JD found</label>
        </div>
        <label>
          Notes
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={4} placeholder="Example: title and company worked, but JD body needed manual paste." />
        </label>
        <button
          type="button"
          className="secondaryButton"
          onClick={() => onSaveValidation({ site, url, parserRating, autoParsed, manualPasteUsed, titleFound, companyFound, descriptionFound, notes })}
        >
          Save Validation
        </button>
        {validationInfo && <p className="hint">{validationInfo}</p>}
        <div className="compactList">
          {validations.slice(0, 5).map((item) => (
            <div key={item.id}>
              <strong>{item.site}</strong>
              <span>{item.parserRating} | role {item.titleFound ? "yes" : "no"} | company {item.companyFound ? "yes" : "no"} | JD {item.descriptionFound ? "yes" : "no"}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function EvaluationPanel({
  result,
  lastSavedAnalysisId,
  summary,
  info,
  onRefresh,
  onSaveFeedback,
  onExportDataset,
  onImportDataset,
}: {
  result: AnalysisResponse | null;
  lastSavedAnalysisId: string | null;
  summary: MatchFeedbackSummary | null;
  info: string;
  onRefresh: () => void;
  onSaveFeedback: (payload: {
    roleFamily: string;
    expectedFit: "strong" | "good" | "partial" | "weak";
    scoreAccuracy: "accurate" | "too_high" | "too_low";
    outcome: "not_applied" | "applied" | "shortlisted" | "interview" | "rejected" | "offer" | "no_response";
    notes: string;
  }) => void;
  onExportDataset: () => void;
  onImportDataset: (file: File | null) => void;
}) {
  const [roleFamily, setRoleFamily] = useState(".NET");
  const [expectedFit, setExpectedFit] = useState<"strong" | "good" | "partial" | "weak">("good");
  const [scoreAccuracy, setScoreAccuracy] = useState<"accurate" | "too_high" | "too_low">("accurate");
  const [outcome, setOutcome] = useState<"not_applied" | "applied" | "shortlisted" | "interview" | "rejected" | "offer" | "no_response">("not_applied");
  const [notes, setNotes] = useState("");

  return (
    <div className="evaluationGrid">
      <div className="panel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Latest Score</p>
            <h3>{result ? `${result.technicalMatchScore}% ${result.fitCategory}` : "No active score"}</h3>
            <p className="hint">{lastSavedAnalysisId ? `Analysis ${lastSavedAnalysisId}` : "Run and save a match before attaching feedback."}</p>
          </div>
          <button type="button" className="secondaryButton" onClick={onRefresh}>Refresh</button>
        </div>
        <div className="gridTwo">
          <label>
            Role family
            <select value={roleFamily} onChange={(event) => setRoleFamily(event.target.value)}>
              <option>.NET</option>
              <option>Java</option>
              <option>Python</option>
              <option>Frontend</option>
              <option>Data/AI</option>
              <option>Cloud/DevOps</option>
              <option>General Software</option>
            </select>
          </label>
          <label>
            Expected fit
            <select value={expectedFit} onChange={(event) => setExpectedFit(event.target.value as "strong" | "good" | "partial" | "weak")}>
              <option value="strong">Strong</option>
              <option value="good">Good</option>
              <option value="partial">Partial</option>
              <option value="weak">Weak</option>
            </select>
          </label>
          <label>
            Score accuracy
            <select value={scoreAccuracy} onChange={(event) => setScoreAccuracy(event.target.value as "accurate" | "too_high" | "too_low")}>
              <option value="accurate">Accurate</option>
              <option value="too_high">Too high</option>
              <option value="too_low">Too low</option>
            </select>
          </label>
        </div>
        <label>
          Outcome
          <select value={outcome} onChange={(event) => setOutcome(event.target.value as "not_applied" | "applied" | "shortlisted" | "interview" | "rejected" | "offer" | "no_response")}>
            <option value="not_applied">Not applied</option>
            <option value="applied">Applied</option>
            <option value="shortlisted">Shortlisted</option>
            <option value="interview">Interview</option>
            <option value="rejected">Rejected</option>
            <option value="offer">Offer</option>
            <option value="no_response">No response</option>
          </select>
        </label>
        <label>
          Notes
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={5} placeholder="Example: score missed cloud certification relevance, should be slightly higher." />
        </label>
        <button type="button" disabled={!lastSavedAnalysisId} onClick={() => onSaveFeedback({ roleFamily, expectedFit, scoreAccuracy, outcome, notes })}>
          Save Score Feedback
        </button>
        {info && <p className="hint">{info}</p>}
      </div>

      <div className="panel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Dataset</p>
            <h3>Tuning Dataset</h3>
          </div>
          <button type="button" className="secondaryButton" onClick={onExportDataset}>Export JSON</button>
        </div>
        <label className="importControl">
          Import JSON
          <input type="file" accept="application/json,.json" onChange={(event) => onImportDataset(event.target.files?.[0] ?? null)} />
        </label>
        <div className="scoreGrid">
          <div className="scoreTile"><span>Labels</span><strong>{summary?.feedbackCount ?? 0}</strong></div>
          <div className="scoreTile"><span>Accurate</span><strong>{summary?.accurateCount ?? 0}</strong></div>
          <div className="scoreTile"><span>Too high</span><strong>{summary?.tooHighCount ?? 0}</strong></div>
          <div className="scoreTile"><span>Too low</span><strong>{summary?.tooLowCount ?? 0}</strong></div>
        </div>
        <div className="calibrationCallout">
          <strong>{summary?.accuracyRate === null || summary?.accuracyRate === undefined ? "No accuracy rate yet" : `${summary.accuracyRate}% labelled accurate`}</strong>
          <span>{summary?.calibrationRecommendation ?? "Collect labels from real resume/JD matches to start calibration."}</span>
        </div>
        <div className="calibrationGrid">
          <div>
            <span>Average score</span>
            <strong>{summary?.averageAlgorithmScore ?? "No data"}</strong>
          </div>
          <div>
            <span>Accurate avg</span>
            <strong>{summary?.averageScoreByAccuracy?.accurate ?? "n/a"}</strong>
          </div>
          <div>
            <span>Too high avg</span>
            <strong>{summary?.averageScoreByAccuracy?.too_high ?? "n/a"}</strong>
          </div>
          <div>
            <span>Too low avg</span>
            <strong>{summary?.averageScoreByAccuracy?.too_low ?? "n/a"}</strong>
          </div>
        </div>
        {summary && Object.keys(summary.outcomeCounts).length > 0 && (
          <div className="outcomeStrip">
            {Object.entries(summary.outcomeCounts).map(([key, value]) => <span key={key}>{key}: {value}</span>)}
          </div>
        )}
        {summary && Object.keys(summary.roleFamilyBreakdown).length > 0 && (
          <div className="segmentGrid">
            {Object.entries(summary.roleFamilyBreakdown).map(([family, segment]) => (
              <div key={family}>
                <strong>{family}</strong>
                <span>{segment.feedbackCount} labels | {segment.accuracyRate ?? "n/a"}% accurate</span>
                <small>{segment.calibrationRecommendation}</small>
              </div>
            ))}
          </div>
        )}
        <div className="compactList">
          {(summary?.latestFeedback ?? []).map((item) => (
            <div key={item.id}>
              <strong>{item.roleFamily ?? "General Software"} | {item.scoreAccuracy} | {item.expectedFit}</strong>
              <span>{item.algorithmScore ?? "n/a"}% {item.fitCategory ?? ""} | {item.outcome}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ScoringSettingsPanel({
  configs,
  recommendation,
  audit,
  diagnostics,
  productionReadiness,
  users,
  adminAnalyses,
  usageSummary,
  billingDraft,
  demoSeedResult,
  launchChecklist,
  canManageSettings,
  info,
  onRefresh,
  onSave,
  onRecommend,
  onLoadAudit,
  onRestore,
  onRefreshDiagnostics,
  onRefreshReadiness,
  onRefreshUsers,
  onSearchAnalyses,
  onLoadUsage,
  onBillingEdit,
  onBillingDraftChange,
  onBillingSave,
  onBillingCancel,
  onSeedDemo,
  onToggleLaunchChecklist,
  onResetLaunchChecklist,
}: {
  configs: ScoringCalibrationConfig[];
  recommendation: ScoringCalibrationRecommendation | null;
  audit: ScoringCalibrationAuditRecord[];
  diagnostics: SystemDiagnostics | null;
  productionReadiness: ProductionReadiness | null;
  users: AdminUserRecord[];
  adminAnalyses: HistoryAnalysisRecord[];
  usageSummary: UsageSummary | null;
  billingDraft: BillingDraft | null;
  demoSeedResult: DemoSeedResponse | null;
  launchChecklist: LaunchChecklistState;
  canManageSettings: boolean;
  info: string;
  onRefresh: () => void;
  onSave: (config: ScoringCalibrationConfig) => void;
  onRecommend: (roleFamily: string) => void;
  onLoadAudit: (roleFamily?: string) => void;
  onRestore: (auditId: string) => void;
  onRefreshDiagnostics: () => void;
  onRefreshReadiness: () => void;
  onRefreshUsers: () => void;
  onSearchAnalyses: (query?: string, userId?: string) => void;
  onLoadUsage: (userId?: string) => void;
  onBillingEdit: (user: AdminUserRecord) => void;
  onBillingDraftChange: (draft: BillingDraft) => void;
  onBillingSave: (draft: BillingDraft) => void;
  onBillingCancel: () => void;
  onSeedDemo: () => void;
  onToggleLaunchChecklist: (itemId: string, checked: boolean) => void;
  onResetLaunchChecklist: () => void;
}) {
  const [selectedFamily, setSelectedFamily] = useState(".NET");
  const activeConfig = configs.find((config) => config.roleFamily === selectedFamily) ?? configs[0];
  const [draftWeights, setDraftWeights] = useState<Record<string, number>>(activeConfig?.categoryWeights ?? {});
  const [userSearch, setUserSearch] = useState("");
  const [userTierFilter, setUserTierFilter] = useState<"all" | "free" | "premium">("all");
  const [userStatusFilter, setUserStatusFilter] = useState("all");
  const [analysisSearch, setAnalysisSearch] = useState("");
  const [analysisUserFilter, setAnalysisUserFilter] = useState("");
  const [usageUserFilter, setUsageUserFilter] = useState("");

  useEffect(() => {
    setDraftWeights(activeConfig?.categoryWeights ?? {});
    if (activeConfig?.roleFamily) onLoadAudit(activeConfig.roleFamily);
  }, [activeConfig?.roleFamily]);

  const total = Object.values(draftWeights).reduce((sum, value) => sum + Number(value || 0), 0);
  const visibleAudit = audit.filter((item) => item.roleFamily === activeConfig?.roleFamily);
  const billingUser = billingDraft ? users.find((user) => user.id === billingDraft.userId) : null;
  const normalizedUserSearch = userSearch.trim().toLowerCase();
  const visibleUsers = users.filter((user) => {
    const tier = user.subscriptionTier ?? "free";
    const status = user.subscriptionStatus ?? "inactive";
    const searchable = [
      user.id,
      user.displayName,
      user.email ?? "",
      user.role,
      tier,
      status,
      user.subscriptionPlanId ?? "",
      user.billingProviderCustomerId ?? "",
      user.billingProviderSubscriptionId ?? "",
    ].join(" ").toLowerCase();
    return (!normalizedUserSearch || searchable.includes(normalizedUserSearch))
      && (userTierFilter === "all" || tier === userTierFilter)
      && (userStatusFilter === "all" || status === userStatusFilter);
  });
  const premiumUserCount = users.filter((user) => user.subscriptionTier === "premium").length;
  const activeBillingCount = users.filter((user) => ["trialing", "active", "past_due"].includes(user.subscriptionStatus ?? "")).length;
  const adminUserCount = users.filter((user) => user.role === "admin").length;
  const launchDoneCount = launchChecklistItems.filter((item) => launchChecklist[item.id]).length;
  const launchCompletion = Math.round((launchDoneCount / launchChecklistItems.length) * 100);

  if (!configs.length) {
    return (
      <div className="panel empty">
        <h2>No scoring settings loaded</h2>
        <p>Refresh settings to load default role-family calibration weights.</p>
        <button type="button" className="secondaryButton" onClick={onRefresh}>Refresh Settings</button>
        {info && <p className="hint">{info}</p>}
      </div>
    );
  }

  return (
    <div className="settingsGrid">
      <div className="panel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Calibration</p>
            <h3>Role-family weights</h3>
          </div>
          <button type="button" className="secondaryButton" onClick={onRefresh}>Refresh</button>
        </div>
        {!canManageSettings && (
          <p className="hint">Admin role is required to generate recommendations, save weights, restore audit entries, or view known users when auth enforcement is enabled.</p>
        )}
        <label>
          Role family
          <select value={selectedFamily} onChange={(event) => setSelectedFamily(event.target.value)}>
            {configs.map((config) => <option key={config.roleFamily}>{config.roleFamily}</option>)}
          </select>
        </label>
        <div className="settingsMeta">
          <span>{activeConfig?.isDefault ? "Default weights" : "Custom saved weights"}</span>
          <span>Total: {total}</span>
          <span>{activeConfig?.updatedAt ? `Updated ${formatDate(activeConfig.updatedAt)}` : "Not saved yet"}</span>
        </div>
        <div className="weightEditor">
          {Object.entries(draftWeights).map(([category, weight]) => (
            <label key={category}>
              <span>{formatCategory(category)}</span>
              <input
                type="number"
                min={0}
                max={100}
                value={weight}
                onChange={(event) => setDraftWeights((current) => ({
                  ...current,
                  [category]: Math.max(0, Math.min(100, Number(event.target.value) || 0)),
                }))}
              />
            </label>
          ))}
        </div>
        <div className="actionBar">
          <button type="button" className="secondaryButton" disabled={!canManageSettings} onClick={() => activeConfig && onRecommend(activeConfig.roleFamily)}>
            Generate Suggestion
          </button>
          <button
            type="button"
            className="secondaryButton"
            disabled={!canManageSettings || !recommendation || recommendation.roleFamily !== activeConfig?.roleFamily}
            onClick={() => recommendation && setDraftWeights(recommendation.suggestedWeights)}
          >
            Apply Suggestion to Draft
          </button>
        </div>
        {recommendation && recommendation.roleFamily === activeConfig?.roleFamily && (
          <div className="recommendationPanel">
            <div>
              <strong>{recommendation.confidence} confidence</strong>
              <span>{recommendation.sampleSize} labelled match(es)</span>
            </div>
            <p>{recommendation.reason}</p>
            {recommendation.changes.length > 0 ? (
              <ul>{recommendation.changes.map((change) => <li key={change}>{change}</li>)}</ul>
            ) : (
              <p className="hint">No weight movement is recommended yet.</p>
            )}
          </div>
        )}
        <button
          type="button"
          disabled={!canManageSettings || !activeConfig || total !== 100}
          onClick={() => activeConfig && onSave({ ...activeConfig, categoryWeights: draftWeights })}
        >
          Save Weights
        </button>
        {total !== 100 && <p className="error">Weights must total 100 before saving.</p>}
        {info && <p className="hint">{info}</p>}
      </div>

      <div className="panel">
        <h3>How These Weights Affect Scores</h3>
        <div className="compactList">
          {Object.entries(draftWeights).map(([category, weight]) => (
            <div key={category}>
              <strong>{formatCategory(category)}: {weight}%</strong>
              <span>{scoringCategoryHelp(category)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="panel diagnosticsPanel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Deployment</p>
            <h3>Production Readiness</h3>
          </div>
          <button type="button" className="secondaryButton" onClick={onRefreshReadiness}>Refresh Readiness</button>
        </div>
        {productionReadiness ? (
          <>
            <div className="readinessSummary">
              <strong>{productionReadiness.readyForProduction ? "Ready to deploy" : "Needs attention"}</strong>
              <span>{productionReadiness.environment} environment</span>
            </div>
            <LaunchChecklist readiness={productionReadiness} />
            <div className="readinessList">
              {productionReadiness.checks.map((check) => (
                <div key={check.key}>
                  <span className={`statusPill ${check.status}`}>{check.status}</span>
                  <strong>{check.label}</strong>
                  <p>{check.detail}</p>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="hint">Production readiness has not been loaded yet.</p>
        )}
      </div>

      <div className="panel diagnosticsPanel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Launch</p>
            <h3>Manual Launch Tracker</h3>
          </div>
          <button type="button" className="secondaryButton" onClick={onResetLaunchChecklist}>Reset Tracker</button>
        </div>
        <div className="launchTrackerSummary">
          <div>
            <strong>{launchCompletion}% complete</strong>
            <span>{launchDoneCount} of {launchChecklistItems.length} launch checks marked done in this browser.</span>
          </div>
          <div className="progressBar"><span style={{ width: `${launchCompletion}%` }} /></div>
        </div>
        <div className="launchTrackerList">
          {launchChecklistItems.map((item) => (
            <label key={item.id} className={launchChecklist[item.id] ? "done" : ""}>
              <input
                type="checkbox"
                checked={Boolean(launchChecklist[item.id])}
                onChange={(event) => onToggleLaunchChecklist(item.id, event.target.checked)}
              />
              <span>
                <strong>{item.title}</strong>
                <small>{item.detail}</small>
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="panel diagnosticsPanel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Staging</p>
            <h3>Smoke Runbook</h3>
          </div>
          <span className="statusPill warn">manual</span>
        </div>
        <div className="compactList">
          <div>
            <strong>1. Rehearse deployment assets</strong>
            <code>python deployment/production_rehearsal.py --api {API_BASE_URL} --web {window.location.origin}</code>
          </div>
          <div>
            <strong>2. Run backend/frontend smoke checks</strong>
            <code>python deployment/smoke_check.py --api {API_BASE_URL} --frontend {window.location.origin} --user-id {users[0]?.id ?? "staging-admin"} --session-token &lt;session-token&gt; --check-extension-package --strict-production</code>
          </div>
          <div>
            <strong>3. Package staging extension</strong>
            <code>python deployment/package_extension.py --api {API_BASE_URL} --web {window.location.origin} --version 0.1.0-staging</code>
          </div>
        </div>
        <ul className="diagnosticWarnings">
          <li>Create or login as the first admin listed in ADMIN_USER_IDS.</li>
          <li>Confirm Settings readiness has no failed checks before enabling live LLM mode.</li>
          <li>Validate extension parsing on LinkedIn, Naukri, Indeed, and one company careers page.</li>
        </ul>
      </div>

      <div className="panel diagnosticsPanel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Demo</p>
            <h3>Portfolio Workspace</h3>
          </div>
          <button type="button" className="secondaryButton" disabled={!canManageSettings} onClick={onSeedDemo}>Seed Demo Data</button>
        </div>
        <p className="hint">Creates a resettable Premium demo workspace for project reviews, then switches this browser session to the demo user.</p>
        <div className="usageQuotaStrip">
          <div><span>User</span><strong>demo-aditya</strong></div>
          <div><span>Password</span><strong>DemoPass123!</strong></div>
          <div><span>Tier</span><strong>Premium</strong></div>
          <div><span>Reset</span><strong>Yes</strong></div>
        </div>
        {demoSeedResult && (
          <div className="recommendationPanel">
            <div>
              <strong>{demoSeedResult.displayName}</strong>
              <span>{demoSeedResult.resumeCount} resume(s), {demoSeedResult.jobDescriptionCount} JD(s), {demoSeedResult.analysisCount} analysis, {demoSeedResult.jobOpportunityCount} opportunity record(s)</span>
            </div>
            <p>{demoSeedResult.message}</p>
          </div>
        )}
        {!canManageSettings && <p className="hint">Admin role is required to reset and seed demo data.</p>}
      </div>

      <div className="panel diagnosticsPanel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Runtime</p>
            <h3>System Diagnostics</h3>
          </div>
          <button type="button" className="secondaryButton" onClick={onRefreshDiagnostics}>Refresh Diagnostics</button>
        </div>
        {diagnostics ? (
          <>
            <div className="diagnosticTiles">
              <div><span>Status</span><strong>{diagnostics.status}</strong></div>
              <div><span>Database</span><strong>{diagnostics.databaseOk ? "ok" : "failed"}</strong></div>
              <div><span>LLM</span><strong>{diagnostics.llmMode} / {diagnostics.llmProvider}</strong></div>
              <div><span>LLM key</span><strong>{diagnostics.llmKeyConfigured ? "configured" : "missing"}</strong></div>
              <div><span>Embeddings</span><strong>{diagnostics.embeddingProvider}</strong></div>
              <div><span>JD parser</span><strong>{diagnostics.jdParserMode}</strong></div>
            </div>
            {Object.keys(diagnostics.workspaceCounts).length > 0 && (
              <div className="outcomeStrip">
                {Object.entries(diagnostics.workspaceCounts).map(([key, value]) => <span key={key}>{key}: {value}</span>)}
              </div>
            )}
            {diagnostics.warnings.length > 0 && (
              <ul className="diagnosticWarnings">
                {diagnostics.warnings.map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
            )}
          </>
        ) : (
          <p className="hint">Diagnostics have not been loaded yet.</p>
        )}
      </div>

      <div className="panel diagnosticsPanel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Admin</p>
            <h3>User & Subscription Management</h3>
          </div>
          <button type="button" className="secondaryButton" disabled={!canManageSettings} onClick={onRefreshUsers}>Refresh Users</button>
        </div>
        <div className="adminUserSummary">
          <div><span>Total users</span><strong>{users.length}</strong></div>
          <div><span>Premium tier</span><strong>{premiumUserCount}</strong></div>
          <div><span>Billable status</span><strong>{activeBillingCount}</strong></div>
          <div><span>Admins</span><strong>{adminUserCount}</strong></div>
        </div>
        <div className="adminUserToolbar">
          <label>
            Search
            <input value={userSearch} onChange={(event) => setUserSearch(event.target.value)} placeholder="Name, email, user id, plan, provider id" />
          </label>
          <label>
            Tier
            <select value={userTierFilter} onChange={(event) => setUserTierFilter(event.target.value as "all" | "free" | "premium")}>
              <option value="all">All tiers</option>
              <option value="free">Free</option>
              <option value="premium">Premium</option>
            </select>
          </label>
          <label>
            Status
            <select value={userStatusFilter} onChange={(event) => setUserStatusFilter(event.target.value)}>
              <option value="all">All statuses</option>
              <option value="inactive">Inactive</option>
              <option value="trialing">Trialing</option>
              <option value="active">Active</option>
              <option value="past_due">Past due</option>
              <option value="canceled">Canceled</option>
            </select>
          </label>
        </div>
        <div className="adminUserTable" role="table" aria-label="Known users and subscription metadata">
          <div className="adminUserTableHeader" role="row">
            <span>User</span>
            <span>Access</span>
            <span>Billing</span>
            <span>Provider</span>
            <span>Created</span>
            <span>Action</span>
          </div>
          {visibleUsers.length ? visibleUsers.map((user) => (
            <div className={`adminUserTableRow ${billingDraft?.userId === user.id ? "active" : ""}`} role="row" key={user.id}>
              <div>
                <strong>{user.displayName}</strong>
                <span>{user.email ?? "No email"}</span>
                <small>{user.id}</small>
              </div>
              <div>
                <span className={`statusPill ${user.role === "admin" ? "pass" : "warn"}`}>{user.role}</span>
                <span className={`statusPill ${user.subscriptionTier === "premium" ? "pass" : "warn"}`}>{user.subscriptionTier ?? "free"}</span>
              </div>
              <div>
                <strong>{user.subscriptionStatus ?? "inactive"}</strong>
                <span>{user.subscriptionPlanId ?? "No plan"}</span>
                <small>{user.billingPeriodEnd ? `Ends ${formatDate(user.billingPeriodEnd)}` : "No period end"}</small>
              </div>
              <div>
                <span>{user.billingProviderCustomerId ?? "No customer id"}</span>
                <small>{user.billingProviderSubscriptionId ?? "No subscription id"}</small>
              </div>
              <div>
                <span>{formatDate(user.createdAt)}</span>
              </div>
              <div>
                <button type="button" className="tinyButton" disabled={!canManageSettings} onClick={() => onBillingEdit(user)}>Edit Billing</button>
              </div>
            </div>
          )) : (
            <div className="adminUserEmpty">
              <strong>{users.length ? "No users match these filters" : "No users loaded"}</strong>
              <span>{users.length ? "Clear filters or refresh users." : "Create or claim a session to populate users."}</span>
            </div>
          )}
        </div>
        <div className="billingEditor">
          {billingDraft ? (
            <>
              <div>
                <p className="eyebrow">Billing metadata</p>
                <h4>{billingUser?.displayName ?? billingDraft.userId}</h4>
              </div>
              <div className="billingGrid">
                <label>
                  Tier
                  <select
                    value={billingDraft.subscriptionTier}
                    onChange={(event) => onBillingDraftChange({ ...billingDraft, subscriptionTier: event.target.value as BillingDraft["subscriptionTier"] })}
                  >
                    <option value="free">Free</option>
                    <option value="premium">Premium</option>
                  </select>
                </label>
                <label>
                  Status
                  <select
                    value={billingDraft.subscriptionStatus}
                    onChange={(event) => onBillingDraftChange({ ...billingDraft, subscriptionStatus: event.target.value as BillingDraft["subscriptionStatus"] })}
                  >
                    <option value="inactive">Inactive</option>
                    <option value="trialing">Trialing</option>
                    <option value="active">Active</option>
                    <option value="past_due">Past due</option>
                    <option value="canceled">Canceled</option>
                  </select>
                </label>
                <label>
                  Plan id
                  <input value={billingDraft.subscriptionPlanId} onChange={(event) => onBillingDraftChange({ ...billingDraft, subscriptionPlanId: event.target.value })} placeholder="premium_monthly" />
                </label>
                <label>
                  Customer id
                  <input value={billingDraft.billingProviderCustomerId} onChange={(event) => onBillingDraftChange({ ...billingDraft, billingProviderCustomerId: event.target.value })} placeholder="cus_..." />
                </label>
                <label>
                  Subscription id
                  <input value={billingDraft.billingProviderSubscriptionId} onChange={(event) => onBillingDraftChange({ ...billingDraft, billingProviderSubscriptionId: event.target.value })} placeholder="sub_..." />
                </label>
                <label>
                  Period end
                  <input value={billingDraft.billingPeriodEnd} onChange={(event) => onBillingDraftChange({ ...billingDraft, billingPeriodEnd: event.target.value })} placeholder="2026-07-31T23:59:59Z" />
                </label>
              </div>
              <div className="actionBar">
                <button type="button" disabled={!canManageSettings} onClick={() => onBillingSave(billingDraft)}>Save Billing</button>
                <button type="button" className="secondaryButton" onClick={onBillingCancel}>Cancel</button>
              </div>
            </>
          ) : (
            <p className="hint">Select a known user to update billing metadata or manually unlock premium access.</p>
          )}
        </div>
      </div>

      <div className="panel diagnosticsPanel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Support</p>
            <h3>Analysis Search</h3>
          </div>
          <button type="button" className="secondaryButton" disabled={!canManageSettings} onClick={() => onSearchAnalyses(analysisSearch, analysisUserFilter)}>Search Analyses</button>
        </div>
        <div className="adminUserToolbar">
          <label>
            Search
            <input value={analysisSearch} onChange={(event) => setAnalysisSearch(event.target.value)} placeholder="Title, user id, fit category" />
          </label>
          <label>
            User
            <select value={analysisUserFilter} onChange={(event) => setAnalysisUserFilter(event.target.value)}>
              <option value="">All users</option>
              {users.map((user) => <option key={user.id} value={user.id}>{user.displayName}</option>)}
            </select>
          </label>
          <label>
            Limit
            <input value="25 latest" disabled readOnly />
          </label>
        </div>
        <div className="adminAnalysisList">
          {adminAnalyses.length ? adminAnalyses.map((analysis) => (
            <div key={analysis.id} className="adminAnalysisItem">
              <div>
                <strong>{analysis.title}</strong>
                <span>{analysis.userId} | {formatDate(analysis.createdAt)}</span>
              </div>
              <div>
                <strong>{analysis.technicalMatchScore}%</strong>
                <span>{analysis.fitCategory}</span>
              </div>
              <div>
                <span>{analysis.response.recommendedAction ?? analysis.response.overallSummary}</span>
              </div>
            </div>
          )) : (
            <div className="adminUserEmpty">
              <strong>No analyses loaded</strong>
              <span>Search saved analyses across users for support and debugging.</span>
            </div>
          )}
        </div>
      </div>

      <div className="panel diagnosticsPanel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Usage</p>
            <h3>AI Call Tracking</h3>
          </div>
          <button type="button" className="secondaryButton" disabled={!canManageSettings} onClick={() => onLoadUsage(usageUserFilter)}>Refresh Usage</button>
        </div>
        <div className="adminUserToolbar">
          <label>
            User
            <select value={usageUserFilter} onChange={(event) => setUsageUserFilter(event.target.value)}>
              <option value="">All users</option>
              {users.map((user) => <option key={user.id} value={user.id}>{user.displayName}</option>)}
            </select>
          </label>
          <label>
            Events
            <input value={usageSummary?.totalEvents ?? 0} disabled readOnly />
          </label>
          <label>
            Estimated units
            <input value={usageSummary?.totalEstimatedUnits ?? 0} disabled readOnly />
          </label>
        </div>
        {usageSummary ? (
          <>
            {usageSummary.quota ? (
              <div className="usageQuotaStrip">
                <div>
                  <span>Tier</span>
                  <strong>{formatCategory(usageSummary.quota.tier)}</strong>
                </div>
                <div>
                  <span>Monthly units</span>
                  <strong>{usageSummary.quota.usedUnits} / {usageSummary.quota.unlimited ? "Unlimited" : usageSummary.quota.limitUnits}</strong>
                </div>
                <div>
                  <span>Remaining</span>
                  <strong>{usageSummary.quota.unlimited ? "Unlimited" : usageSummary.quota.remainingUnits}</strong>
                </div>
                <div>
                  <span>Window</span>
                  <strong>{formatCategory(usageSummary.quota.window)}</strong>
                </div>
              </div>
            ) : (
              <div className="adminUserEmpty compact">
                <strong>Select a user to inspect quota</strong>
                <span>All-user usage shows aggregate calls. Quotas are evaluated per subscription tier.</span>
              </div>
            )}
            <div className="usageBreakdownGrid">
              <div>
                <strong>By module</strong>
                {Object.entries(usageSummary.byModule).length ? Object.entries(usageSummary.byModule).map(([module, count]) => (
                  <span key={module}>{formatCategory(module)}: {count}</span>
                )) : <span>No module usage yet</span>}
              </div>
              <div>
                <strong>By user</strong>
                {Object.entries(usageSummary.byUser).length ? Object.entries(usageSummary.byUser).slice(0, 8).map(([userId, count]) => (
                  <span key={userId}>{userId}: {count}</span>
                )) : <span>No user usage yet</span>}
              </div>
            </div>
            <div className="adminAnalysisList">
              {usageSummary.latestEvents.length ? usageSummary.latestEvents.map((event) => (
                <div key={event.id} className="adminAnalysisItem">
                  <div>
                    <strong>{formatCategory(event.module)}</strong>
                    <span>{event.userId ?? "anonymous"} | {formatDate(event.createdAt)}</span>
                  </div>
                  <div>
                    <strong>{event.estimatedUnits} unit(s)</strong>
                    <span>{event.mode ?? "mode n/a"} / {event.provider ?? "provider n/a"}</span>
                  </div>
                  <div>
                    <span>{event.model ?? "model n/a"}</span>
                  </div>
                </div>
              )) : (
                <div className="adminUserEmpty">
                  <strong>No usage events yet</strong>
                  <span>Score, preparation, extension match, and premium artifact calls will appear here.</span>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="adminUserEmpty">
            <strong>No usage summary loaded</strong>
            <span>Refresh usage to inspect AI call activity.</span>
          </div>
        )}
      </div>

      <div className="panel auditPanel">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Audit</p>
            <h3>Weight Change History</h3>
          </div>
          <button type="button" className="secondaryButton" onClick={() => activeConfig && onLoadAudit(activeConfig.roleFamily)}>Refresh Audit</button>
        </div>
        <div className="compactList">
          {visibleAudit.length ? visibleAudit.slice(0, 8).map((item) => (
            <div key={item.id}>
              <strong>{formatDate(item.createdAt)} | {item.changeSource}</strong>
              <span>{weightDeltaSummary(item.previousWeights, item.newWeights)}</span>
              <button type="button" className="tinyButton" disabled={!canManageSettings} onClick={() => onRestore(item.id)}>Restore previous weights</button>
            </div>
          )) : (
            <div>
              <strong>No changes yet</strong>
              <span>Saved edits and restores will appear here.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function weightDeltaSummary(previous: Record<string, number>, next: Record<string, number>) {
  const changes = Object.keys({ ...previous, ...next })
    .map((key) => {
      const before = previous[key] ?? 0;
      const after = next[key] ?? 0;
      const delta = after - before;
      return delta === 0 ? null : `${formatCategory(key)} ${delta > 0 ? "+" : ""}${delta}`;
    })
    .filter(Boolean);
  return changes.length ? changes.slice(0, 4).join(", ") : "No numeric change.";
}

function LaunchChecklist({ readiness }: { readiness: ProductionReadiness }) {
  const blockers = readiness.checks.filter((check) => check.status === "fail");
  const warnings = readiness.checks.filter((check) => check.status === "warn");
  const passed = readiness.checks.filter((check) => check.status === "pass");
  const nextItems = [...blockers, ...warnings].slice(0, 5);
  return (
    <div className="launchChecklist">
      <div className="launchMetrics">
        <div><span>Blockers</span><strong>{blockers.length}</strong></div>
        <div><span>Warnings</span><strong>{warnings.length}</strong></div>
        <div><span>Passed</span><strong>{passed.length}</strong></div>
      </div>
      <div className="launchActions">
        <strong>{nextItems.length ? "Next launch fixes" : "Launch checklist clear"}</strong>
        {nextItems.length ? nextItems.map((check) => (
          <span key={check.key}>{check.label}: {check.detail}</span>
        )) : <span>All readiness checks are passing for the current environment.</span>}
      </div>
    </div>
  );
}

function inferRoleFamily(text: string) {
  const lowered = ` ${text.toLowerCase()} `;
  if ([".net", "asp.net", "c#", "entity framework"].some((term) => lowered.includes(term))) return ".NET";
  if ([" java", "spring", "hibernate"].some((term) => lowered.includes(term))) return "Java";
  if ([" python", "django", "fastapi", "flask"].some((term) => lowered.includes(term))) return "Python";
  if (["react", "angular", "vue", "typescript", "javascript"].some((term) => lowered.includes(term))) return "Frontend";
  if ([" ai ", "llm", "machine learning", "data engineer", "etl", "power bi"].some((term) => lowered.includes(term))) return "Data/AI";
  if (["aws", "azure", "gcp", "docker", "kubernetes", "devops"].some((term) => lowered.includes(term))) return "Cloud/DevOps";
  return "General Software";
}

function scoringCategoryHelp(category: string) {
  const descriptions: Record<string, string> = {
    experienceFit: "Candidate years versus JD range.",
    dynamicRequirementFit: "Semantic requirement matrix against JD must-haves.",
    projectRelevance: "Project and experience evidence against the JD.",
    technicalDepth: "Depth of concrete tools, frameworks, and implementation proof.",
    deliveryReadiness: "Production, debugging, release, support, cloud, and certification proof.",
    systemReadiness: "Architecture, scalability, reliability, and design evidence.",
    problemSolving: "Optimization, debugging, algorithms, and analytical problem solving.",
  };
  return descriptions[category] ?? "Scoring category used by the matching engine.";
}

function AISpendPanel({
  llmMode,
  llmProvider,
  llmModel,
  onModeChange,
  onProviderChange,
  onModelChange,
}: {
  llmMode: LlmMode;
  llmProvider: LlmProvider;
  llmModel: string;
  onModeChange: (mode: LlmMode) => void;
  onProviderChange: (provider: LlmProvider) => void;
  onModelChange: (model: string) => void;
}) {
  return (
    <div className="aiSpendPanel">
      <div>
        <p className="eyebrow">AI usage control</p>
        <h3>Call only what this task needs</h3>
        <p>Mock mode is for UI and parser checks. Live mode should be used only when the input is reviewed enough to spend tokens.</p>
      </div>
      <div className="controlBand">
        <div>
          <span className="fieldTitle">Analyzer mode</span>
          <div className="segmented">
            <button type="button" className={llmMode === "mock" ? "active" : ""} onClick={() => onModeChange("mock")}>Mock</button>
            <button type="button" className={llmMode === "live" ? "active" : ""} onClick={() => onModeChange("live")}>Live LLM</button>
          </div>
        </div>
        <label>
          Provider
          <select
            value={llmProvider}
            onChange={(event) => onProviderChange(event.target.value as LlmProvider)}
          >
            <option value="groq">Groq</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Gemini</option>
          </select>
        </label>
        <label>
          Model
          <select value={llmModel} onChange={(event) => onModelChange(event.target.value)}>
            {modelOptions[llmProvider].map((model) => <option key={model} value={model}>{model}</option>)}
          </select>
        </label>
      </div>
    </div>
  );
}

function QuotaStatusPanel({ quota, onRefresh, onUpgrade }: { quota: UsageQuotaStatus | null; onRefresh: () => void; onUpgrade: () => void }) {
  const used = quota?.usedUnits ?? 0;
  const limit = quota?.unlimited ? "Unlimited" : quota?.limitUnits ?? "--";
  const remaining = quota?.unlimited ? "Unlimited" : quota?.remainingUnits ?? "--";
  const resetLabel = quota?.resetAt ? formatDate(quota.resetAt) : "--";
  const exhausted = Boolean(quota && !quota.unlimited && (quota.remainingUnits ?? 0) <= 0);
  const canUpgrade = quota?.tier === "free" || quota?.tier === "anonymous" || exhausted;
  return (
    <div className={`quotaStatusPanel ${exhausted ? "exhausted" : ""}`}>
      <div>
        <p className="eyebrow">Monthly quota</p>
        <h4>{quota ? `${formatCategory(quota.tier)} tier` : "Quota unavailable"}</h4>
        {exhausted && <span className="quotaWarning">Limit reached for this monthly window.</span>}
      </div>
      <div className="quotaStatusGrid">
        <div><span>Used</span><strong>{used}</strong></div>
        <div><span>Limit</span><strong>{limit}</strong></div>
        <div><span>Remaining</span><strong>{remaining}</strong></div>
        <div><span>Resets</span><strong>{resetLabel}</strong></div>
      </div>
      <div className="quotaActions">
        <button type="button" className="tinyButton" onClick={onRefresh}>Refresh</button>
        {canUpgrade && <button type="button" className="tinyButton premiumTinyButton" onClick={onUpgrade}>Unlock Premium</button>}
      </div>
    </div>
  );
}

function PreparationEmpty() {
  return (
    <div className="panel empty">
      <h2>No preparation plan yet</h2>
      <p>Run resume matching first, then build the plan from the latest requirement gaps. This avoids repeating the resume/JD matching call.</p>
    </div>
  );
}

function PreparationProgressTracker({
  currentSession,
  sessions,
  currentResult,
  saving,
  info,
  onSelectSession,
  onUpdate,
}: {
  currentSession: HistoryPreparationRecord | null;
  sessions: HistoryPreparationRecord[];
  currentResult: AnalysisResponse | null;
  saving: boolean;
  info: string;
  onSelectSession: (session: HistoryPreparationRecord) => void;
  onUpdate: (progress: PreparationProgress) => void;
}) {
  const plan = currentSession?.plan ?? currentResult?.preparationIntelligence ?? null;
  const progress = currentSession?.progress ?? (plan ? createInitialProgress(plan) : null);
  const tasks = plan ? flattenPreparationTasks(plan) : [];
  const doneCount = progress ? tasks.filter((task) => progress.tasks[task.id] === "done").length : 0;
  const skippedCount = progress ? tasks.filter((task) => progress.tasks[task.id] === "skipped").length : 0;
  const completion = tasks.length ? Math.round((doneCount / tasks.length) * 100) : 0;
  const nextTask = progress ? tasks.find((task) => !["done", "skipped"].includes(progress.tasks[task.id] ?? "todo")) ?? null : null;

  function updateTask(taskId: string, status: TaskStatus) {
    if (!progress) return;
    onUpdate({
      ...progress,
      tasks: { ...progress.tasks, [taskId]: status },
    });
  }

  function updateNote(dayKey: string, note: string) {
    if (!progress) return;
    onUpdate({
      ...progress,
      notes: { ...progress.notes, [dayKey]: note },
    });
  }

  function updateConfidence(dayKey: string, confidence: ConfidenceLevel) {
    if (!progress) return;
    onUpdate({
      ...progress,
      confidence: { ...progress.confidence, [dayKey]: confidence },
    });
  }

  if (!plan || !progress) {
    return (
      <div className="panel empty">
        <h2>No preparation session yet</h2>
        <p>Build a preparation plan from the latest match result, then return here to track task progress.</p>
      </div>
    );
  }

  return (
    <div className="progressGrid">
      <div className="panel progressSummary">
        <div>
          <p className="eyebrow">Progress</p>
          <h3>{completion}% complete</h3>
          <p>{doneCount} done, {skippedCount} skipped, {tasks.length - doneCount - skippedCount} active.</p>
        </div>
        <div className="progressBar"><span style={{ width: `${completion}%` }} /></div>
        {nextTask ? (
          <div className="nextTaskBox">
            <div>
              <span>Next task</span>
              <strong>Day {nextTask.day}: {nextTask.task}</strong>
            </div>
            <div>
              <button type="button" className="secondaryButton" onClick={() => updateTask(nextTask.id, "in_progress")}>Start</button>
              <button type="button" onClick={() => updateTask(nextTask.id, "done")}>Mark Done</button>
            </div>
          </div>
        ) : (
          <div className="nextTaskBox complete">
            <div>
              <span>Next task</span>
              <strong>All planned tasks are complete or skipped.</strong>
            </div>
          </div>
        )}
        <div className="gridTwo">
          <label>
            Preparation session
            <select
              value={currentSession?.id ?? ""}
              onChange={(event) => {
                const selected = sessions.find((session) => session.id === event.target.value);
                if (selected) onSelectSession(selected);
              }}
            >
              {currentSession && !sessions.some((session) => session.id === currentSession.id) && <option value={currentSession.id}>{currentSession.title}</option>}
              {sessions.map((session) => (
                <option key={session.id} value={session.id}>{session.title} - {formatDate(session.createdAt)}</option>
              ))}
            </select>
          </label>
          <label>
            Status
            <input value={currentSession?.status ?? inferPreparationStatus(progress, plan)} readOnly />
          </label>
        </div>
        {saving && <p className="hint">Saving progress...</p>}
        {info && <p className="hint">{info}</p>}
      </div>

      <div className="progressDayList">
        {plan.dailyPlan.map((day) => {
          const dayKey = `day-${day.day}`;
          return (
            <div className="panel progressDay" key={dayKey}>
              <div className="prepDayTop">
                <strong>Day {day.day}</strong>
                <span>{day.focus}</span>
              </div>
              <p>{day.goal}</p>
              <div className="taskList">
                {day.tasks.map((task, index) => {
                  const taskId = `${dayKey}-task-${index}`;
                  return (
                    <div className="taskRow" key={taskId}>
                      <span>{task}</span>
                      <select value={progress.tasks[taskId] ?? "todo"} onChange={(event) => updateTask(taskId, event.target.value as TaskStatus)}>
                        <option value="todo">Todo</option>
                        <option value="in_progress">In progress</option>
                        <option value="done">Done</option>
                        <option value="skipped">Skipped</option>
                      </select>
                    </div>
                  );
                })}
              </div>
              <div className="gridTwo">
                <label>
                  Confidence
                  <select value={progress.confidence[dayKey] ?? "low"} onChange={(event) => updateConfidence(dayKey, event.target.value as ConfidenceLevel)}>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </label>
                <label>
                  Notes
                  <input value={progress.notes[dayKey] ?? ""} onChange={(event) => updateNote(dayKey, event.target.value)} placeholder="What did you practice?" />
                </label>
              </div>
              <small>Output: {day.output}</small>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PrepMemoryPanel({
  memory,
  onRefresh,
  onOpenAction,
}: {
  memory: PrepMemoryResponse | null;
  onRefresh: () => void;
  onOpenAction: (action: NonNullable<PrepMemoryResponse["nextAction"]>) => void;
}) {
  return (
    <div className="panel prepMemoryPanel">
      <div className="panelHeader">
        <div>
          <p className="eyebrow">Memory</p>
          <h3>Preparation Memory Intelligence</h3>
        </div>
        <button type="button" className="secondaryButton" onClick={onRefresh}>Refresh Memory</button>
      </div>
      {!memory ? (
        <p className="hint">Load history or save progress to build preparation memory.</p>
      ) : (
        <>
          <p className="recommendation">{memory.summary}</p>
          {memory.nextAction && (
            <div className="prepNextAction">
              <div>
                <span>Next best action</span>
                <strong>{memory.nextAction.label}</strong>
                <p>{memory.nextAction.task ? `Day ${memory.nextAction.day ?? ""}: ${memory.nextAction.task}` : memory.nextAction.reason}</p>
              </div>
              <button type="button" onClick={() => onOpenAction(memory.nextAction!)}>
                Open Action
              </button>
            </div>
          )}
          {memory.nextRecommendedActions.length > 0 && (
            <div className="prepSection">
              <h4>Next Actions</h4>
              <ul>
                {memory.nextRecommendedActions.map((action) => <li key={action}>{action}</li>)}
              </ul>
            </div>
          )}
          {memory.repeatedWeakTopics.length > 0 && (
            <div className="prepTopicList">
              {memory.repeatedWeakTopics.map((topic) => (
                <div className="prepTopic" key={topic.topic}>
                  <div className="prepTopicTop">
                    <strong>{topic.topic}</strong>
                    <span>{topic.occurrences}x | avg {topic.averageScore}%</span>
                  </div>
                  <p>{topic.recommendation}</p>
                  {topic.latestEvidence && <small>{topic.latestEvidence}</small>}
                </div>
              ))}
            </div>
          )}
          {memory.unfinishedPreparation.length > 0 && (
            <div className="prepSection">
              <h4>Unfinished Preparation</h4>
              <div className="historyList">
                {memory.unfinishedPreparation.map((item) => (
                  <div className="historyItem" key={item.sessionId}>
                    <div>
                      <strong>{item.title}</strong>
                      <small>{item.unfinishedTaskCount} task(s) left, {item.lowConfidenceDays} low-confidence day(s)</small>
                    </div>
                    <span>{item.completionPercent}%</span>
                    <em>{item.status}</em>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ResearchNotesPanel({
  notes,
  title,
  company,
  roleTitle,
  researchType,
  summary,
  keySignals,
  preparationTopics,
  manualContext,
  sourcesDraft,
  draftProvider,
  draftWarnings,
  draftMarketSignals,
  draftSynthesis,
  saving,
  generating,
  info,
  onTitleChange,
  onCompanyChange,
  onRoleTitleChange,
  onResearchTypeChange,
  onSummaryChange,
  onKeySignalsChange,
  onPreparationTopicsChange,
  onManualContextChange,
  onSourcesDraftChange,
  onGenerate,
  onSave,
  onRefresh,
}: {
  notes: ResearchNoteRecord[];
  title: string;
  company: string;
  roleTitle: string;
  researchType: ResearchType;
  summary: string;
  keySignals: string;
  preparationTopics: string;
  manualContext: string;
  sourcesDraft: string;
  draftProvider: string;
  draftWarnings: string[];
  draftMarketSignals: string[];
  draftSynthesis: string[];
  saving: boolean;
  generating: boolean;
  info: string;
  onTitleChange: (value: string) => void;
  onCompanyChange: (value: string) => void;
  onRoleTitleChange: (value: string) => void;
  onResearchTypeChange: (value: ResearchType) => void;
  onSummaryChange: (value: string) => void;
  onKeySignalsChange: (value: string) => void;
  onPreparationTopicsChange: (value: string) => void;
  onManualContextChange: (value: string) => void;
  onSourcesDraftChange: (value: string) => void;
  onGenerate: () => void;
  onSave: () => void;
  onRefresh: () => void;
}) {
  return (
    <div className="researchWorkspace">
      <section className="panel researchEditorPanel">
        <div className="panelHeader">
          <div>
            <h3>Manual Research Capture</h3>
            <p className="hint">Generate a draft from the latest score, then edit it with company interview signals, similar job patterns, role expectations, and market notes.</p>
          </div>
          <button type="button" className="secondaryButton" disabled={saving} onClick={onRefresh}>Refresh</button>
        </div>
        <div className="researchGeneratorBox">
          <label>
            Research context for draft generation
            <textarea value={manualContext} onChange={(event) => onManualContextChange(event.target.value)} rows={4} placeholder={"Optional context, one point per line\nCompany asks agent guardrail questions\nRecent role posts emphasize ETL reliability"} />
          </label>
          <button type="button" className="premiumButton" disabled={generating} onClick={onGenerate}>
            <span>Pro</span>
            {generating ? "Generating Draft..." : "Generate From Latest Score"}
          </button>
        </div>
        {(draftProvider || draftWarnings.length > 0 || draftMarketSignals.length > 0 || draftSynthesis.length > 0) && (
          <div className="researchProviderStatus">
            <div>
              <span>Research provider</span>
              <strong>{formatCategory(draftProvider || "local")}</strong>
            </div>
            <div>
              <span>Status</span>
              <strong>{draftWarnings.length ? `${draftWarnings.length} warning(s)` : "Ready"}</strong>
            </div>
            {draftWarnings.length > 0 && (
              <ul>
                {draftWarnings.slice(0, 4).map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
            )}
            {(draftMarketSignals.length > 0 || draftSynthesis.length > 0) && (
              <ul>
                {draftMarketSignals.slice(0, 3).map((signal) => <li key={`market-${signal}`}>Market: {signal}</li>)}
                {draftSynthesis.slice(0, 3).map((signal) => <li key={`synthesis-${signal}`}>Synthesis: {signal}</li>)}
              </ul>
            )}
          </div>
        )}
        <div className="gridTwo">
          <label>
            Title
            <input value={title} onChange={(event) => onTitleChange(event.target.value)} />
          </label>
          <label>
            Research type
            <select value={researchType} onChange={(event) => onResearchTypeChange(event.target.value as ResearchType)}>
              <option value="manual">Manual note</option>
              <option value="company">Company</option>
              <option value="role">Role</option>
              <option value="interview">Interview</option>
              <option value="market">Market</option>
            </select>
          </label>
        </div>
        <div className="gridTwo">
          <label>
            Company
            <input value={company} onChange={(event) => onCompanyChange(event.target.value)} placeholder="Example: DemoFin Analytics" />
          </label>
          <label>
            Role title
            <input value={roleTitle} onChange={(event) => onRoleTitleChange(event.target.value)} placeholder="Example: Python AI Full Stack Engineer" />
          </label>
        </div>
        <label>
          Research summary
          <textarea value={summary} onChange={(event) => onSummaryChange(event.target.value)} rows={5} placeholder="Summarize what you learned and why it matters for applying or preparing." />
        </label>
        <div className="gridTwo">
          <label>
            Key signals
            <textarea value={keySignals} onChange={(event) => onKeySignalsChange(event.target.value)} rows={5} placeholder={"One signal per line\nAI-agent guardrails are emphasized\nETL reliability is repeatedly mentioned"} />
          </label>
          <label>
            Preparation topics
            <textarea value={preparationTopics} onChange={(event) => onPreparationTopicsChange(event.target.value)} rows={5} placeholder={"One topic per line\nTool permission design\nRetry and rollback handling"} />
          </label>
        </div>
        <label>
          Sources
          <textarea value={sourcesDraft} onChange={(event) => onSourcesDraftChange(event.target.value)} rows={4} placeholder={"Citation quality is checked for each source.\nOne source per line: title | url | type | note\nManual interview note | | manual | Asked in mock review"} />
        </label>
        <div className="actionBar">
          <button type="button" disabled={saving} onClick={onSave}>{saving ? "Saving..." : "Save Research Note"}</button>
          {info && <p className="hint">{info}</p>}
        </div>
      </section>

      <section className="panel researchListPanel">
        <div className="panelHeader">
          <div>
            <h3>Saved Research Memory</h3>
            <p className="hint">{notes.length} note(s) available for future research and preparation agents.</p>
          </div>
        </div>
        {notes.length ? (
          <div className="researchNoteList">
            {notes.map((note) => (
              <article className="researchNoteCard" key={note.id}>
                <div className="researchNoteHeader">
                  <div>
                    <strong>{note.title}</strong>
                    <small>{[note.company, note.roleTitle, formatDate(note.createdAt)].filter(Boolean).join(" - ")}</small>
                  </div>
                  <span>{formatCategory(note.researchType)}</span>
                </div>
                <p>{note.summary}</p>
                {note.keySignals.length > 0 && (
                  <div>
                    <h4>Signals</h4>
                    <div className="tags">{note.keySignals.slice(0, 8).map((item) => <span key={item}>{item}</span>)}</div>
                  </div>
                )}
                {note.preparationTopics.length > 0 && (
                  <div>
                    <h4>Preparation Topics</h4>
                    <div className="tags">{note.preparationTopics.slice(0, 8).map((item) => <span key={item}>{item}</span>)}</div>
                  </div>
                )}
                {note.sources.length > 0 && (
                  <div className="sourceList">
                    <h4>Sources and Citation Quality</h4>
                    {note.sources.slice(0, 4).map((source, index) => (
                      <div className="sourceItem" key={`${note.id}-${index}`}>
                        {source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a> : <strong>{source.title}</strong>}
                        <small>{[formatCategory(source.sourceType), formatCategory(source.citationQuality || "uncited"), source.note].filter(Boolean).join(" - ")}</small>
                        {(source.validationIssues ?? []).length > 0 && <small>{source.validationIssues?.join(" ")}</small>}
                      </div>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="No research notes yet" body="Save manual research now. Later, company and web-research agents will write cited notes into this same workspace memory." />
        )}
      </section>
    </div>
  );
}

function ApplicationDecisionPanel({
  decision,
  result,
  researchNotes,
  loading,
  info,
  accessTier,
  onBuild,
  onTierChange,
}: {
  decision: ApplicationDecisionResponse | null;
  result: AnalysisResponse | null;
  researchNotes: ResearchNoteRecord[];
  loading: boolean;
  info: string;
  accessTier: AccessTier;
  onBuild: () => void;
  onTierChange: (tier: AccessTier) => void;
}) {
  return (
    <div className="decisionWorkspace">
      <ProductAccessPanel active="premium" accessTier={accessTier} onTierChange={onTierChange} compact />
      <section className="panel decisionControlPanel">
        <div className="panelHeader">
          <div>
            <h3>Decision Inputs</h3>
            <p className="hint">Uses the latest score report plus {researchNotes.length} saved research note(s).</p>
          </div>
          <button type="button" className="premiumButton" disabled={loading || !result} onClick={onBuild}>
            <span>Pro</span>
            {loading ? "Building Decision..." : "Build Apply Decision"}
          </button>
        </div>
        {result ? (
          <div className="scoreGrid">
            <div className="scoreTile"><span>Technical</span><strong>{result.technicalMatchScore}%</strong></div>
            <div className="scoreTile"><span>Shortlisting</span><strong>{result.shortlistingScore ?? "--"}%</strong></div>
            <div className="scoreTile"><span>Readiness</span><strong>{result.interviewReadinessScore ?? "--"}%</strong></div>
            <div className="scoreTile"><span>Opportunity</span><strong>{result.overallOpportunityScore ?? "--"}%</strong></div>
          </div>
        ) : (
          <EmptyState title="No score yet" body="Run resume matching first. Decisioning depends on the score, requirement matrix, and research notes." />
        )}
        {info && <p className="hint">{info}</p>}
      </section>

      {decision ? (
        <section className={`panel decisionResultPanel decision-${decision.decision}`}>
          <div className="decisionHeader">
            <div>
              <p className="eyebrow">Decision</p>
              <h3>{decision.headline}</h3>
              <small>{formatCategory(decision.decision)} confidence: {decision.confidence}</small>
            </div>
            <span>{formatCategory(decision.decision)}</span>
          </div>
          <div className="decisionColumns">
            <div>
              <h4>Reasoning</h4>
              <ul>{decision.reasoning.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
            <div>
              <h4>Blockers</h4>
              {decision.blockers.length ? <ul>{decision.blockers.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="hint">No major blocker detected.</p>}
            </div>
            <div>
              <h4>Next Actions</h4>
              <ul>{decision.nextActions.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
          {decision.researchSignalsUsed.length > 0 && (
            <div className="prepSection">
              <h4>Research Signals Used</h4>
              <div className="tags">{decision.researchSignalsUsed.map((item) => <span key={item}>{item}</span>)}</div>
            </div>
          )}
        </section>
      ) : (
        <section className="panel">
          <h3>Decision Output</h3>
          <p className="hint">Build the decision after scoring and adding at least one research note for better confidence.</p>
        </section>
      )}
    </div>
  );
}

function AgentPlanPanel({
  plan,
  result,
  loading,
  info,
  accessTier,
  researchNotes,
  artifacts,
  onBuild,
  onRunRecommendation,
  onTierChange,
}: {
  plan: AgentPlanResponse | null;
  result: AnalysisResponse | null;
  loading: boolean;
  info: string;
  accessTier: AccessTier;
  researchNotes: ResearchNoteRecord[];
  artifacts: string[];
  onBuild: () => void;
  onRunRecommendation: (tool: AgentPlanResponse["recommendations"][number]["tool"]) => void;
  onTierChange: (tier: AccessTier) => void;
}) {
  return (
    <div className="decisionWorkspace">
      <ProductAccessPanel active="premium" accessTier={accessTier} onTierChange={onTierChange} compact />
      <section className="panel decisionControlPanel">
        <div className="panelHeader">
          <div>
            <h3>Agent Inputs</h3>
            <p className="hint">Uses the latest score, {researchNotes.length} research note(s), and {artifacts.length} generated artifact marker(s).</p>
          </div>
          <button type="button" className="premiumButton" disabled={loading || !result} onClick={onBuild}>
            <span>Pro</span>
            {loading ? "Planning..." : "Build Next-Step Plan"}
          </button>
        </div>
        {result ? (
          <div className="scoreGrid">
            <div className="scoreTile"><span>Technical</span><strong>{result.technicalMatchScore}%</strong></div>
            <div className="scoreTile"><span>Weak reqs</span><strong>{result.requirementMatches.filter((item) => item.score < 60).length}</strong></div>
            <div className="scoreTile"><span>Research</span><strong>{researchNotes.length}</strong></div>
            <div className="scoreTile"><span>Artifacts</span><strong>{artifacts.length}</strong></div>
          </div>
        ) : (
          <EmptyState title="No score yet" body="Run resume matching first. The career agent planner depends on the saved requirement matrix." />
        )}
        {info && <p className="hint">{info}</p>}
      </section>

      {plan ? (
        <section className="panel decisionResultPanel">
          <div className="decisionHeader">
            <div>
              <p className="eyebrow">{plan.phase}</p>
              <h3>{plan.headline}</h3>
              <small>Next action: {plan.nextBestAction}</small>
            </div>
            <span>Planner</span>
          </div>
          <div className="decisionColumns">
            <div>
              <h4>Reasoning</h4>
              <ul>{plan.reasoning.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
            <div>
              <h4>Memory</h4>
              <ul>{plan.memorySignals.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
            <div>
              <h4>Guardrails</h4>
              <ul>{plan.guardrails.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
          <div className="prepSection">
            <h4>Recommended Tool Order</h4>
            <div className="recommendationList">
              {plan.recommendations.map((item) => (
                <article className={`recommendationItem priority-${item.priority}`} key={`${item.tool}-${item.priority}-${item.reason}`}>
                  <div>
                    <strong>{formatCategory(item.tool)}</strong>
                    <small>{item.endpoint ?? "No API call"} - {item.estimatedUnits} unit(s)</small>
                  </div>
                  <p>{item.reason}</p>
                  <div className="recommendationActions">
                    <div className="tags">
                      <span>{formatCategory(item.priority)}</span>
                      {item.requiresPremium && <span>Premium</span>}
                      {item.alreadySatisfied && <span>Already satisfied</span>}
                    </div>
                    <button type="button" className="secondaryButton" onClick={() => onRunRecommendation(item.tool)}>
                      {item.alreadySatisfied ? "Open Module" : "Run / Open"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>
      ) : (
        <section className="panel">
          <h3>Planner Output</h3>
          <p className="hint">Build this after scoring. It recommends the next paid/optional module without generating every artifact at once.</p>
        </section>
      )}
    </div>
  );
}

function ResumeRewritePanel({
  rewrite,
  result,
  loading,
  info,
  accessTier,
  appliedKeys,
  acceptedRewrites,
  resumeVersions,
  resumeVersionRestores,
  versionComparison,
  onBuild,
  onApplySuggestion,
  onCompareVersion,
  onRestoreVersion,
  onTierChange,
}: {
  rewrite: ResumeRewriteResponse | null;
  result: AnalysisResponse | null;
  loading: boolean;
  info: string;
  accessTier: AccessTier;
  appliedKeys: string[];
  acceptedRewrites: AcceptedResumeRewriteRecord[];
  resumeVersions: ResumeVersionRecord[];
  resumeVersionRestores: ResumeVersionRestoreRecord[];
  versionComparison: ResumeVersionComparison | null;
  onBuild: () => void;
  onApplySuggestion: (item: ResumeRewriteSuggestion, index: number) => void | Promise<void>;
  onCompareVersion: (version: ResumeVersionRecord) => void;
  onRestoreVersion: (version: ResumeVersionRecord) => void;
  onTierChange: (tier: AccessTier) => void;
}) {
  return (
    <div className="rewriteWorkspace">
      <ProductAccessPanel active="premium" accessTier={accessTier} onTierChange={onTierChange} compact />
      <section className="panel rewriteControlPanel">
        <div className="panelHeader">
          <div>
            <h3>Evidence-Constrained Rewrite</h3>
            <p className="hint">Suggestions are labelled as safe, needs verification, or gap-only so you do not accidentally invent experience.</p>
          </div>
          <button type="button" className="premiumButton" disabled={loading || !result} onClick={onBuild}>
            <span>Pro</span>
            {loading ? "Building Rewrite..." : "Build Rewrite Suggestions"}
          </button>
        </div>
        {info && <p className="hint">{info}</p>}
        {!result && <EmptyState title="No score yet" body="Run resume matching first. Rewrite suggestions depend on the requirement match matrix." />}
      </section>

      {rewrite ? (
        <section className="panel rewriteResultPanel">
          <h3>Rewrite Suggestions</h3>
          <p className="hint">{rewrite.summary}</p>
          {rewrite.warnings.length > 0 && (
            <div className="rewriteWarningBox">
              {rewrite.warnings.map((warning) => <span key={warning}>{warning}</span>)}
            </div>
          )}
          <div className="rewriteList">
            {rewrite.suggestions.map((item, index) => {
              const suggestionKey = rewriteSuggestionKey(item, index);
              const applied = appliedKeys.includes(suggestionKey);
              const gapOnly = item.proofSafety === "gap_do_not_claim";
              return (
                <article className={`rewriteItem rewrite-${item.proofSafety}`} key={suggestionKey}>
                  <div className="rewriteItemHeader">
                    <div>
                      <strong>{item.targetRequirement}</strong>
                      <small>{formatCategory(item.evidenceSource)} - {formatCategory(item.proofSafety)}</small>
                    </div>
                    <span>{formatCategory(item.proofSafety)}</span>
                  </div>
                  {item.originalEvidence && (
                    <div className="rewriteEvidence">
                      <b>Original evidence</b>
                      <p>{item.originalEvidence}</p>
                    </div>
                  )}
                  <div>
                    <b>Issue</b>
                    <p>{item.currentIssue}</p>
                  </div>
                  <div>
                    <b>Suggested bullet</b>
                    <p>{item.rewrittenBullet}</p>
                  </div>
                  <small>{item.reason}</small>
                  <div className="rewriteActions">
                    <button
                      type="button"
                      className="secondaryButton"
                      disabled={gapOnly || applied}
                      onClick={() => onApplySuggestion(item, index)}
                    >
                      {gapOnly ? "Gap Only" : applied ? "Applied" : "Apply to Resume Draft"}
                    </button>
                    <small>{gapOnly ? "Preparation gap, not a resume claim." : applied ? "Added to the structured resume review step." : "Requires your approval before it changes the resume."}</small>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ) : (
        <section className="panel">
          <h3>Rewrite Output</h3>
          <p className="hint">Build suggestions after scoring. Gap-only items are preparation warnings, not paste-ready resume claims.</p>
        </section>
      )}

      <section className="panel rewriteHistoryPanel">
        <h3>Accepted Rewrite History</h3>
        <p className="hint">Every applied bullet is kept as an audit record with its safety label and target resume section.</p>
        {acceptedRewrites.length ? (
          <div className="rewriteHistoryList">
            {acceptedRewrites.slice(0, 8).map((record) => (
              <article className="rewriteHistoryItem" key={record.id}>
                <div className="rewriteItemHeader">
                  <div>
                    <strong>{record.targetRequirement}</strong>
                    <small>{formatCategory(record.targetSection)}{record.targetLabel ? ` - ${record.targetLabel}` : ""}</small>
                  </div>
                  <span>{formatCategory(record.proofSafety)}</span>
                </div>
                <p>{record.acceptedBullet}</p>
                <small>{formatDate(record.createdAt)} - {record.reason}</small>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="No accepted rewrites yet" body="Apply a safe suggestion to create a resume rewrite audit trail." />
        )}
      </section>

      <section className="panel rewriteHistoryPanel">
        <h3>Resume Version Snapshots</h3>
        <p className="hint">Snapshots preserve the full structured resume after accepted rewrites so future version compare and rollback can be added cleanly.</p>
        {resumeVersions.length ? (
          <div className="rewriteHistoryList">
            {resumeVersions.slice(0, 8).map((version) => (
              <article className="rewriteHistoryItem" key={version.id}>
                <div className="rewriteItemHeader">
                  <div>
                    <strong>{version.title}</strong>
                    <small>{version.changeSummary}</small>
                  </div>
                  <span>{formatDate(version.createdAt)}</span>
                </div>
                <p>{version.structuredResume.projects.length} project(s), {version.structuredResume.experience.length} experience item(s), {version.structuredResume.skills.length} skill(s)</p>
                <div className="rewriteActions">
                  <button type="button" className="secondaryButton" onClick={() => onCompareVersion(version)}>Compare</button>
                  <button type="button" className="secondaryButton" onClick={() => onRestoreVersion(version)}>Restore to Editor</button>
                  <small>Compare is local and restore only updates the review draft until you score/save again.</small>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="No resume versions yet" body="Apply a rewrite after a saved score to capture the resulting structured resume snapshot." />
        )}
      </section>

      {versionComparison && (
        <section className="panel rewriteComparePanel">
          <h3>Version Compare</h3>
          <p className="hint">{versionComparison.title}: {versionComparison.summary}</p>
          <div className="scoreGrid">
            <div className="scoreTile"><span>Current projects</span><strong>{versionComparison.currentCounts.projects}</strong></div>
            <div className="scoreTile"><span>Version projects</span><strong>{versionComparison.versionCounts.projects}</strong></div>
            <div className="scoreTile"><span>Current bullets</span><strong>{versionComparison.currentCounts.bullets}</strong></div>
            <div className="scoreTile"><span>Version bullets</span><strong>{versionComparison.versionCounts.bullets}</strong></div>
            <div className="scoreTile"><span>Current skills</span><strong>{versionComparison.currentCounts.skills}</strong></div>
            <div className="scoreTile"><span>Version skills</span><strong>{versionComparison.versionCounts.skills}</strong></div>
          </div>
          <div className="rewriteCompareGrid">
            <div>
              <h4>Only in version</h4>
              {versionComparison.addedInVersion.length ? (
                <ul>{versionComparison.addedInVersion.map((item) => <li key={item}>{item}</li>)}</ul>
              ) : (
                <p className="hint">No unique version lines.</p>
              )}
            </div>
            <div>
              <h4>Only in current draft</h4>
              {versionComparison.missingFromVersion.length ? (
                <ul>{versionComparison.missingFromVersion.map((item) => <li key={item}>{item}</li>)}</ul>
              ) : (
                <p className="hint">No unique current draft lines.</p>
              )}
            </div>
          </div>
        </section>
      )}

      <section className="panel rewriteHistoryPanel">
        <h3>Restore Audit History</h3>
        <p className="hint">Every restore action is saved so resume rollback decisions remain traceable.</p>
        {resumeVersionRestores.length ? (
          <div className="rewriteHistoryList">
            {resumeVersionRestores.slice(0, 8).map((restore) => (
              <article className="rewriteHistoryItem" key={restore.id}>
                <div className="rewriteItemHeader">
                  <div>
                    <strong>{restore.reason}</strong>
                    <small>Version {restore.resumeVersionId}</small>
                  </div>
                  <span>{formatDate(restore.createdAt)}</span>
                </div>
                <p>Resume {restore.resumeId}{restore.analysisId ? ` - Analysis ${restore.analysisId}` : ""}</p>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="No restore audit yet" body="Restore a saved version to record the rollback decision." />
        )}
      </section>
    </div>
  );
}

function HistoryPanel({
  summary,
  analyses,
  resumes,
  jobDescriptions,
  preparations,
  opportunities,
  opportunityActions,
  comparisons,
  currentResult,
  onOpportunityStatusChange,
  onOpportunityArtifactBuild,
  artifactLoading,
}: {
  summary: WorkspaceSummary | null;
  analyses: HistoryAnalysisRecord[];
  resumes: HistoryResumeRecord[];
  jobDescriptions: HistoryJobDescriptionRecord[];
  preparations: HistoryPreparationRecord[];
  opportunities: HistoryJobOpportunityRecord[];
  opportunityActions: OpportunityNextActionsResponse | null;
  comparisons: HistoryComparisonRecord[];
  currentResult: AnalysisResponse | null;
  onOpportunityStatusChange: (jobOpportunityId: string, status: JobOpportunityStatus) => void;
  onOpportunityArtifactBuild: (opportunity: HistoryJobOpportunityRecord, artifactKey: "resume_improvements" | "interview_questions" | "cross_questions") => void;
  artifactLoading: string;
}) {
  const [selectedOpportunityId, setSelectedOpportunityId] = useState<string | null>(opportunities[0]?.id ?? null);
  const selectedOpportunity = opportunities.find((item) => item.id === selectedOpportunityId) ?? opportunities[0] ?? null;
  const actionByOpportunity = new Map((opportunityActions?.actions ?? []).map((action) => [action.opportunityId, action]));
  const selectedOpportunityAction = selectedOpportunity ? actionByOpportunity.get(selectedOpportunity.id) ?? null : null;

  function runOpportunityAction(action: OpportunityNextAction) {
    const opportunity = opportunities.find((item) => item.id === action.opportunityId);
    if (!opportunity) return;
    if (action.artifactKey) {
      onOpportunityArtifactBuild(opportunity, action.artifactKey);
      return;
    }
    if (action.recommendedStatus) {
      onOpportunityStatusChange(opportunity.id, action.recommendedStatus);
    }
  }

  return (
    <div className="historyGrid">
      <div className="panel">
        <h3>Workspace Summary</h3>
        <div className="scoreGrid">
          <div className="scoreTile"><span>Resumes</span><strong>{summary?.resumeCount ?? 0}</strong></div>
          <div className="scoreTile"><span>JDs</span><strong>{summary?.jobDescriptionCount ?? 0}</strong></div>
          <div className="scoreTile"><span>Reports</span><strong>{summary?.analysisCount ?? 0}</strong></div>
          <div className="scoreTile"><span>Plans</span><strong>{summary?.preparationSessionCount ?? 0}</strong></div>
          <div className="scoreTile"><span>Jobs</span><strong>{summary?.jobOpportunityCount ?? 0}</strong></div>
          <div className="scoreTile"><span>Research</span><strong>{summary?.researchNoteCount ?? 0}</strong></div>
          <div className="scoreTile"><span>Comparisons</span><strong>{comparisons.length}</strong></div>
          <div className="scoreTile"><span>Average score</span><strong>{summary?.averageMatchScore ?? "--"}%</strong></div>
          <div className="scoreTile"><span>Best score</span><strong>{summary?.bestMatchScore ?? "--"}%</strong></div>
          <div className="scoreTile"><span>Active jobs</span><strong>{summary?.activeOpportunityCount ?? 0}</strong></div>
          <div className="scoreTile"><span>Interviews</span><strong>{summary?.interviewOpportunityCount ?? 0}</strong></div>
          <div className="scoreTile"><span>Offers</span><strong>{summary?.offerOpportunityCount ?? 0}</strong></div>
          <div className="scoreTile"><span>Completed prep</span><strong>{summary?.completedPreparationCount ?? 0}</strong></div>
        </div>
      </div>

      <div className="panel historyWide">
        <h3>Application Pipeline</h3>
        <div className="pipelineGrid">
          {jobOpportunityStatuses.map((status) => (
            <div key={status}>
              <span>{formatCategory(status)}</span>
              <strong>{summary?.pipelineStatusCounts?.[status] ?? 0}</strong>
            </div>
          ))}
        </div>
        <div className="pipelineRates">
          <span>Positive: <strong>{summary?.positiveOutcomeRate ?? "--"}%</strong></span>
          <span>Applied to interview: <strong>{summary?.applicationToInterviewRate ?? "--"}%</strong></span>
          <span>Interview to offer: <strong>{summary?.interviewToOfferRate ?? "--"}%</strong></span>
        </div>
        {opportunityActions && (
          <div className="pipelineNextActions">
            <div>
              <span>Next actions</span>
              <strong>{opportunityActions.summary}</strong>
            </div>
            {opportunityActions.actions.slice(0, 3).map((action) => (
              <button key={action.opportunityId} type="button" className="secondaryButton" onClick={() => runOpportunityAction(action)}>
                {action.action}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="panel">
        <h3>Latest Local Report</h3>
        {currentResult ? (
          <div className="historyPreview">
            <strong>{currentResult.technicalMatchScore}% - {currentResult.fitCategory}</strong>
            <p>{currentResult.overallSummary}</p>
          </div>
        ) : (
          <p className="hint">No local report generated in this session yet.</p>
        )}
      </div>

      <div className="panel historyWide">
        <h3>Saved Match Reports</h3>
        {analyses.length ? (
          <div className="historyList">
            {analyses.slice(0, 8).map((analysis) => (
              <div className="historyItem" key={analysis.id}>
                <div>
                  <strong>{analysis.title}</strong>
                  <small>{formatDate(analysis.createdAt)}</small>
                </div>
                <span>{analysis.technicalMatchScore}%</span>
                <em>{analysis.fitCategory}</em>
              </div>
            ))}
          </div>
        ) : (
          <p className="hint">No saved match reports yet.</p>
        )}
      </div>

      <div className="panel historyWide">
        <div className="panelHeader">
          <div>
            <h3>Job Opportunities</h3>
            <p className="hint">Extension matches and saved job decisions.</p>
          </div>
        </div>
        {opportunities.length ? (
          <div className="historyList">
            {opportunities.slice(0, 10).map((opportunity) => (
              <div
                role="button"
                tabIndex={0}
                className={`historyItem opportunityHistoryItem selectableHistoryItem ${selectedOpportunity?.id === opportunity.id ? "active" : ""}`}
                key={opportunity.id}
                onClick={() => setSelectedOpportunityId(opportunity.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") setSelectedOpportunityId(opportunity.id);
                }}
              >
                <div>
                  <strong>{opportunity.title}</strong>
                  <small>
                    {[opportunity.company, opportunity.location, formatDate(opportunity.createdAt)].filter(Boolean).join(" - ")}
                  </small>
                  <p>{opportunity.description.slice(0, 180)}{opportunity.description.length > 180 ? "..." : ""}</p>
                  {actionByOpportunity.get(opportunity.id) && (
                    <small className="opportunityNextHint">{actionByOpportunity.get(opportunity.id)?.action}</small>
                  )}
                </div>
                <span>{opportunity.technicalMatchScore ?? "--"}%</span>
                <em>{opportunity.fitCategory ?? "Not scored"}</em>
                <select
                  aria-label={`Status for ${opportunity.title}`}
                  value={opportunity.status}
                  onClick={(event) => event.stopPropagation()}
                  onChange={(event) => onOpportunityStatusChange(opportunity.id, event.target.value as JobOpportunityStatus)}
                >
                  {jobOpportunityStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
                </select>
              </div>
            ))}
          </div>
        ) : (
          <p className="hint">No saved job opportunities yet. Extension matches will appear here.</p>
        )}
      </div>

      {selectedOpportunity && (
        <JobOpportunityDetail
          opportunity={selectedOpportunity}
          nextAction={selectedOpportunityAction}
          onStatusChange={onOpportunityStatusChange}
          onArtifactBuild={onOpportunityArtifactBuild}
          onRunAction={runOpportunityAction}
          artifactLoading={artifactLoading}
        />
      )}

      <div className="panel">
        <h3>Resume Versions</h3>
        {resumes.length ? <CompactHistoryList items={resumes.map((item) => ({ id: item.id, title: item.title, meta: formatDate(item.createdAt) }))} /> : <p className="hint">No resumes saved yet.</p>}
      </div>

      <div className="panel">
        <h3>JD Library</h3>
        {jobDescriptions.length ? <CompactHistoryList items={jobDescriptions.map((item) => ({ id: item.id, title: item.title, meta: item.company ? `${item.company} - ${formatDate(item.createdAt)}` : formatDate(item.createdAt) }))} /> : <p className="hint">No JDs saved yet.</p>}
      </div>

      <div className="panel historyWide">
        <h3>Saved Comparisons</h3>
        {comparisons.length ? (
          <div className="historyList">
            {comparisons.slice(0, 8).map((comparison) => (
              <div className="historyItem" key={comparison.id}>
                <div>
                  <strong>{comparison.title}</strong>
                  <small>{formatDate(comparison.createdAt)}</small>
                </div>
                <span>{comparison.results[0]?.score ?? "--"}%</span>
                <em>{comparison.results.length} result(s)</em>
              </div>
            ))}
          </div>
        ) : (
          <p className="hint">No saved comparisons yet.</p>
        )}
      </div>

      <div className="panel historyWide">
        <h3>Preparation Sessions</h3>
        {preparations.length ? (
          <div className="historyList">
            {preparations.slice(0, 8).map((session) => (
              <div className="historyItem" key={session.id}>
                <div>
                  <strong>{session.title}</strong>
                  <small>{formatDate(session.createdAt)}</small>
                </div>
                <span>{session.plan.dailyPlan?.length ?? 0} day(s)</span>
                <em>{session.status}</em>
              </div>
            ))}
          </div>
        ) : (
          <p className="hint">No saved preparation sessions yet.</p>
        )}
      </div>
    </div>
  );
}

function JobOpportunityDetail({
  opportunity,
  nextAction,
  onStatusChange,
  onArtifactBuild,
  onRunAction,
  artifactLoading,
}: {
  opportunity: HistoryJobOpportunityRecord;
  nextAction: OpportunityNextAction | null;
  onStatusChange: (jobOpportunityId: string, status: JobOpportunityStatus) => void;
  onArtifactBuild: (opportunity: HistoryJobOpportunityRecord, artifactKey: "resume_improvements" | "interview_questions" | "cross_questions") => void;
  onRunAction: (action: OpportunityNextAction) => void;
  artifactLoading: string;
}) {
  const analysis = opportunity.analysisResponse;
  const score = opportunity.technicalMatchScore ?? analysis?.technicalMatchScore ?? null;
  const fitCategory = opportunity.fitCategory ?? analysis?.fitCategory ?? "Not scored";
  const requirements = analysis?.requirementMatches ?? [];
  const breakdown = analysis?.scoreBreakdown ?? [];
  const weakRequirements = requirements.filter((item) => item.score < 60).slice(0, 5);
  const canBuildArtifacts = Boolean(opportunity.analysisId && analysis);
  const generatedArtifacts = Object.keys(opportunity.optionalArtifacts ?? {});

  return (
    <div className="panel historyWide opportunityDetailPanel">
      <div className="opportunityDetailHeader">
        <div>
          <p className="eyebrow">Opportunity Detail</p>
          <h3>{opportunity.title}</h3>
          <small>{[opportunity.company, opportunity.location, formatDate(opportunity.createdAt)].filter(Boolean).join(" - ")}</small>
        </div>
        <div className="opportunityScoreBadge">
          <strong>{score ?? "--"}%</strong>
          <span>{fitCategory}</span>
        </div>
      </div>

      <div className="opportunityMetaGrid">
        <label>
          Status
          <select
            value={opportunity.status}
            onChange={(event) => onStatusChange(opportunity.id, event.target.value as JobOpportunityStatus)}
          >
            {jobOpportunityStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </label>
        <div className="metaBlock">
          <span>Resume</span>
          <strong>{opportunity.resumeId ? "Saved resume selected" : "Manual resume text"}</strong>
        </div>
        <div className="metaBlock">
          <span>Source</span>
          {opportunity.url ? <a href={opportunity.url} target="_blank" rel="noreferrer">Open job</a> : <strong>No URL saved</strong>}
        </div>
      </div>

      {analysis?.overallSummary && (
        <p className="recommendation">{analysis.overallSummary}</p>
      )}

      {analysis?.recommendedAction && (
        <div className="opportunityCallout">
          <strong>Recommended action</strong>
          <p>{analysis.recommendedAction}</p>
        </div>
      )}

      {nextAction && (
        <div className={`opportunityNextAction priority-${nextAction.priority}`}>
          <div>
            <span>{formatCategory(nextAction.priority)}</span>
            <strong>{nextAction.action}</strong>
            <p>{nextAction.reason}</p>
          </div>
          <button type="button" onClick={() => onRunAction(nextAction)}>
            {nextAction.artifactKey ? "Generate" : "Apply"}
          </button>
        </div>
      )}

      <div className="opportunityDetailGrid">
        <section>
          <h4>JD Snapshot</h4>
          <p className="textSnippet">{opportunity.description}</p>
        </section>

        <section>
          <h4>Free Score Evidence</h4>
          {breakdown.length ? (
            <div className="miniBreakdownList">
              {breakdown.slice(0, 4).map((item) => (
                <div className="miniBreakdownItem" key={item.category}>
                  <span>{formatCategory(item.category)}</span>
                  <strong>{item.score}%</strong>
                </div>
              ))}
            </div>
          ) : (
            <p className="hint">No saved score breakdown is attached yet.</p>
          )}
        </section>
      </div>

      <section>
        <h4>Requirement Match Preview</h4>
        {requirements.length ? (
          <div className="detailRequirementList">
            {requirements.slice(0, 6).map((item, index) => (
              <div className="detailRequirementItem" key={`${item.requirement}-${index}`}>
                <div>
                  <strong>{item.requirement}</strong>
                  <small>{item.bestEvidence || item.reason}</small>
                </div>
                <span className={`importance ${item.importance}`}>{item.importance}</span>
                <b>{item.score}%</b>
              </div>
            ))}
          </div>
        ) : (
          <p className="hint">Run this opportunity through matching to save requirement-level evidence.</p>
        )}
      </section>

      {weakRequirements.length > 0 && (
        <section>
          <h4>Top Gaps To Fix</h4>
          <div className="tags">
            {weakRequirements.map((item) => <span key={item.requirement}>{item.requirement}</span>)}
          </div>
        </section>
      )}

      {generatedArtifacts.length > 0 && (
        <section>
          <h4>Generated Artifacts</h4>
          <div className="tags">
            {generatedArtifacts.map((item) => <span key={item}>{formatCategory(item)}</span>)}
          </div>
        </section>
      )}

      <div className="premiumActionGrid">
        <button
          type="button"
          className="secondaryButton premiumButton"
          disabled={!canBuildArtifacts || Boolean(artifactLoading)}
          onClick={() => onArtifactBuild(opportunity, "resume_improvements")}
        >
          <span>Paid</span>
          {artifactLoading === "Opportunity Resume improvements" ? "Generating..." : "Build resume fixes"}
        </button>
        <button
          type="button"
          className="secondaryButton premiumButton"
          disabled={!canBuildArtifacts || Boolean(artifactLoading)}
          onClick={() => onArtifactBuild(opportunity, "interview_questions")}
        >
          <span>Paid</span>
          {artifactLoading === "Opportunity Interview questions" ? "Generating..." : "Create interview questions"}
        </button>
        <button
          type="button"
          className="secondaryButton premiumButton"
          disabled={!canBuildArtifacts || Boolean(artifactLoading)}
          onClick={() => onArtifactBuild(opportunity, "cross_questions")}
        >
          <span>Paid</span>
          {artifactLoading === "Opportunity Cross questions" ? "Generating..." : "Generate cross questions"}
        </button>
      </div>
      {!canBuildArtifacts && <p className="hint">Paid actions need a linked analysis request. Re-run this job from the connected extension to enable them.</p>}
    </div>
  );
}

function CompactHistoryList({ items }: { items: Array<{ id: string; title: string; meta: string }> }) {
  return (
    <div className="compactHistoryList">
      {items.slice(0, 8).map((item) => (
        <div className="compactHistoryItem" key={item.id}>
          <strong>{item.title}</strong>
          <small>{item.meta}</small>
        </div>
      ))}
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function splitLines(value: string) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseResearchSources(value: string): ResearchSource[] {
  const allowedTypes: ResearchSource["sourceType"][] = ["manual", "job_post", "interview_experience", "company_page", "market_signal", "other"];
  return splitLines(value).slice(0, 20).map((line) => {
    const [titlePart, urlPart, typePart, notePart] = line.split("|").map((item) => item.trim());
    const sourceType = allowedTypes.includes(typePart as ResearchSource["sourceType"]) ? typePart as ResearchSource["sourceType"] : "manual";
    return assessResearchSource({
      title: titlePart || "Manual source",
      url: urlPart || null,
      sourceType,
      note: notePart || null,
    });
  });
}

function formatResearchSources(sources: ResearchSource[]) {
  return sources
    .map((source) => [source.title, source.url ?? "", source.sourceType, source.note ?? ""].join(" | "))
    .join("\n");
}

function assessResearchSource(source: ResearchSource): ResearchSource {
  const issues: string[] = [];
  let citationQuality: ResearchSource["citationQuality"] = "uncited";
  if (source.url) {
    try {
      const parsed = new URL(source.url);
      if (parsed.protocol === "http:" || parsed.protocol === "https:") {
        citationQuality = "verified_url";
      } else {
        citationQuality = "weak";
        issues.push("URL must use http(s).");
      }
    } catch {
      citationQuality = "weak";
      issues.push("URL is not valid.");
    }
  } else if (source.sourceType === "manual") {
    citationQuality = "manual_note";
    if (!source.note) issues.push("Manual source should include a provenance note.");
  } else {
    citationQuality = "weak";
    issues.push("Non-manual source is missing a URL citation.");
  }
  return {
    ...source,
    citationQuality: source.citationQuality ?? citationQuality,
    validationIssues: source.validationIssues?.length ? source.validationIssues : issues,
  };
}

function toResearchContextNote(note: ResearchNoteRecord) {
  return {
    title: note.title,
    company: note.company ?? null,
    roleTitle: note.roleTitle ?? null,
    researchType: note.researchType,
    summary: note.summary,
    keySignals: note.keySignals,
    preparationTopics: note.preparationTopics,
    sources: note.sources,
  };
}

function decodeResearchHandoff(encoded: string): {
  title?: string;
  company?: string;
  description?: string;
  location?: string;
  url?: string;
  source?: string;
} {
  const base64 = encoded.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64.padEnd(base64.length + ((4 - base64.length % 4) % 4), "=");
  const binary = window.atob(padded);
  const json = decodeURIComponent(Array.from(binary).map((character) => `%${character.charCodeAt(0).toString(16).padStart(2, "0")}`).join(""));
  const parsed = JSON.parse(json) as Record<string, unknown>;
  return {
    title: typeof parsed.title === "string" ? parsed.title : undefined,
    company: typeof parsed.company === "string" ? parsed.company : undefined,
    description: typeof parsed.description === "string" ? parsed.description : undefined,
    location: typeof parsed.location === "string" ? parsed.location : undefined,
    url: typeof parsed.url === "string" ? parsed.url : undefined,
    source: typeof parsed.source === "string" ? parsed.source : undefined,
  };
}

async function readApiError(response: Response, fallback: string) {
  const text = await response.text();
  if (!text) return fallback;
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail)) {
      const message = parsed.detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item) return String((item as { msg: unknown }).msg);
          return "";
        })
        .filter(Boolean)
        .join("; ");
      return message || fallback;
    }
  } catch {
    return text;
  }
  return fallback;
}

async function buildAnalysisFingerprint(payload: AnalyzeRequestPayload) {
  const stablePayload = {
    version: "score-v2",
    resumeText: normalizeFingerprintText(payload.resumeText),
    jobDescriptionText: normalizeFingerprintText(payload.jobDescriptionText),
    candidateContext: normalizeForFingerprint(payload.candidateContext),
    llmOptions: normalizeForFingerprint(payload.llmOptions),
  };
  const source = stableStringify(stablePayload);
  if (crypto?.subtle) {
    const data = new TextEncoder().encode(source);
    const digest = await crypto.subtle.digest("SHA-256", data);
    return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
  }
  let hash = 0;
  for (let index = 0; index < source.length; index += 1) {
    hash = ((hash << 5) - hash + source.charCodeAt(index)) | 0;
  }
  return `fallback-${Math.abs(hash).toString(16).padStart(16, "0")}`;
}

function normalizeFingerprintText(value: string) {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}

function normalizeForFingerprint(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(normalizeForFingerprint);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, normalizeForFingerprint(item)]),
    );
  }
  if (typeof value === "string") {
    return value.trim();
  }
  return value;
}

function stableStringify(value: unknown): string {
  return JSON.stringify(normalizeForFingerprint(value));
}

function createInitialProgress(plan: PreparationIntelligence): PreparationProgress {
  const tasks: Record<string, TaskStatus> = {};
  const notes: Record<string, string> = {};
  const confidence: Record<string, ConfidenceLevel> = {};
  for (const day of plan.dailyPlan) {
    const dayKey = `day-${day.day}`;
    notes[dayKey] = "";
    confidence[dayKey] = "low";
    day.tasks.forEach((_task, index) => {
      tasks[`${dayKey}-task-${index}`] = "todo";
    });
  }
  return { tasks, notes, confidence };
}

function flattenPreparationTasks(plan: PreparationIntelligence) {
  return plan.dailyPlan.flatMap((day) =>
    day.tasks.map((task, index) => ({
      id: `day-${day.day}-task-${index}`,
      day: day.day,
      task,
    })),
  );
}

function inferPreparationStatus(progress: PreparationProgress, plan: PreparationIntelligence): HistoryPreparationRecord["status"] {
  const tasks = flattenPreparationTasks(plan);
  if (!tasks.length) return "planned";
  const statuses = tasks.map((task) => progress.tasks[task.id] ?? "todo");
  if (statuses.every((status) => status === "done" || status === "skipped")) return "completed";
  if (statuses.some((status) => status === "done" || status === "in_progress" || status === "skipped")) return "in_progress";
  return "planned";
}

function Results({ result }: { result: AnalysisResponse }) {
  return (
    <>
      <div className="panel heroResult">
        <div>
          <p className="eyebrow">Technical match</p>
          <h2>{result.technicalMatchScore}% - {result.fitCategory}</h2>
          <p>{result.overallSummary}</p>
        </div>
      </div>
      <OpportunityPanel result={result} />
      {result.scoreBreakdown?.length > 0 && <ScoreBreakdown items={result.scoreBreakdown} />}
      {result.requirementMatches?.length > 0 && <RequirementMatrix items={result.requirementMatches} />}
      {result.shortlistingFactors?.length > 0 && <ShortlistingFactors items={result.shortlistingFactors} />}
      <Card title="Matching Skills" items={result.matchingSkills.map((item) => `${item.skill}: ${item.evidenceFromResume}`)} />
      <Card title="Weakly Evidenced Skills" items={result.weaklyEvidencedSkills.map((item) => `${item.skill}: ${item.whyWeak}`)} />
      <Card title="Missing Skills" items={result.missingSkills.map((item) => `${item.skill} (${item.importance}): ${item.howToPrepare}`)} />
      {result.resumeImprovements.length > 0 && <Card title="Resume Improvements" items={result.resumeImprovements.map((item) => `${item.suggestedBullet} Reason: ${item.reason}`)} />}
      {result.interviewQuestions.length > 0 && <Card title="Interview Questions" items={result.interviewQuestions.map((item) => `${item.topic}: ${item.question}`)} />}
      {result.crossQuestions.length > 0 && <Card title="Cross-Questions" items={result.crossQuestions.map((item) => `${item.question} Hint: ${item.expectedAnswerHint}`)} />}
      {result.debug && <DebugPanel debug={result.debug} />}
      <div className="panel">
        <h3>System Design Readiness: {result.systemDesignReadiness.level}</h3>
        <p>{result.systemDesignReadiness.reason}</p>
        <div className="tags">{result.systemDesignReadiness.topicsToPrepare.map((topic) => <span key={topic}>{topic}</span>)}</div>
      </div>
      {result.sevenDayPlan.length > 0 && <Card title={`${result.sevenDayPlan.length}-Day Plan`} items={result.sevenDayPlan.map((item) => `Day ${item.day} - ${item.focus}: ${item.tasks.join(" ")}`)} />}
    </>
  );
}

function ReviewWorkspaceSummary({
  resume,
  jd,
  resumeText,
  jdText,
}: {
  resume: StructuredResume | null;
  jd: ParsedJobDescription | null;
  resumeText: string;
  jdText: string;
}) {
  return (
    <div className="reviewStatus">
      <div>
        <span>Resume review</span>
        <strong>{resume ? `${resume.experience.length} exp, ${resume.projects.length} projects, ${resume.certifications.length} certs` : "Not parsed"}</strong>
      </div>
      <div>
        <span>JD review</span>
        <strong>{jd ? `${jd.requiredSkills.length} required, ${jd.requiredCertifications.length} certs` : "Not parsed"}</strong>
      </div>
      <div>
        <span>Analysis input</span>
        <strong>{resumeText.length.toLocaleString()} resume chars / {jdText.length.toLocaleString()} JD chars</strong>
      </div>
    </div>
  );
}

function ResumeParserDebugPanel({
  rawText,
  normalizedText,
  resume,
  parserDebug,
}: {
  rawText: string;
  normalizedText: string;
  resume: StructuredResume | null;
  parserDebug: ResumeParserDebug | null;
}) {
  if (!resume && rawText.trim().length < 20) return null;

  return (
    <details className="parserDebugPanel">
      <summary>Parser preview</summary>
      <div className="parserDebugStats">
        <span>{resume ? `${resume.experience.length} experience` : "No experience parsed"}</span>
        <span>{resume ? `${resume.projects.length} projects` : "No projects parsed"}</span>
        <span>{resume ? `${resume.certifications.length} certifications` : "No certifications parsed"}</span>
        <span>{rawText.length.toLocaleString()} raw chars</span>
        {parserDebug && <span>{parserDebug.rawLineCount} parsed lines</span>}
      </div>
      {parserDebug && (
        <div className="parserDebugStats">
          {Object.entries(parserDebug.detectedSections).map(([section, count]) => (
            <span key={section}>{section}: {count}</span>
          ))}
        </div>
      )}
      {parserDebug?.parserNotes.length ? (
        <ul className="parserDebugNotes">
          {parserDebug.parserNotes.map((note) => <li key={note}>{note}</li>)}
        </ul>
      ) : null}
      <div className="debugGrid">
        <div>
          <h4>Raw extracted text</h4>
          <pre>{rawText}</pre>
        </div>
        <div>
          <h4>Normalized parser output</h4>
          <pre>{normalizedText}</pre>
        </div>
      </div>
    </details>
  );
}

function PreScoreChecklist({
  resume,
  jd,
  resumeText,
  jdText,
}: {
  resume: StructuredResume | null;
  jd: ParsedJobDescription | null;
  resumeText: string;
  jdText: string;
}) {
  const checks = [
    {
      label: "Resume parsed and reviewed",
      done: Boolean(resume),
      detail: resume ? `${resume.experience.length} experience, ${resume.projects.length} projects, ${resume.certifications.length} certifications` : "Run Parse Resume first.",
    },
    {
      label: "JD parsed and reviewed",
      done: Boolean(jd),
      detail: jd ? `${jd.requiredSkills.length} required skills, ${(jd.emphasizedRequirements ?? []).length} emphasized requirements` : "Run Parse JD first.",
    },
    {
      label: "Contact, education, company, and dates checked",
      done: Boolean(resume?.profile.email && resume?.education.length && resume?.experience.length),
      detail: "These fields affect profile quality, experience fit, and saved history.",
    },
    {
      label: "JD priority signals checked",
      done: Boolean(jd && ((jd.emphasizedRequirements ?? []).length || jd.requiredSkills.length)),
      detail: "Must-have and strongly worded requirements carry more scoring weight.",
    },
    {
      label: "Enough text for scoring",
      done: resumeText.trim().length >= 20 && jdText.trim().length >= 20,
      detail: `${resumeText.length.toLocaleString()} resume chars / ${jdText.length.toLocaleString()} JD chars`,
    },
  ];

  return (
    <div className="preScoreChecklist">
      <div className="sectionHeading">
        <h3>Pre-score checklist</h3>
        <span>{checks.filter((check) => check.done).length}/{checks.length} ready</span>
      </div>
      {checks.map((check) => (
        <div className={check.done ? "checkItem done" : "checkItem"} key={check.label}>
          <strong>{check.done ? "Ready" : "Needs review"}</strong>
          <div>
            <b>{check.label}</b>
            <p>{check.detail}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function ScoreStepper({ currentStep, onChange }: { currentStep: ScoreStep; onChange: (step: ScoreStep) => void }) {
  const steps: Array<{ id: ScoreStep; title: string; meta: string }> = [
    { id: "upload", title: "Upload", meta: "Resume + JD" },
    { id: "review", title: "Review", meta: "Edit parsed data" },
    { id: "score", title: "Score", meta: "Calculate match" },
  ];

  return (
    <div className="scoreStepper" aria-label="Score calculator steps">
      {steps.map((step, index) => (
        <button
          type="button"
          key={step.id}
          className={`stepPill ${currentStep === step.id ? "active" : ""}`}
          onClick={() => onChange(step.id)}
        >
          <span>{index + 1}</span>
          <strong>{step.title}</strong>
          <em>{step.meta}</em>
        </button>
      ))}
    </div>
  );
}

function StructuredResumeEditor({
  resume,
  finalText,
  onChange,
}: {
  resume: StructuredResume;
  finalText: string;
  onChange: (resume: StructuredResume) => void;
}) {
  function updateProfile(field: keyof StructuredResume["profile"], value: string) {
    onChange({ ...resume, profile: { ...resume.profile, [field]: value } });
  }

  function updateExperience(index: number, patch: Partial<StructuredResume["experience"][number]>) {
    const experience = resume.experience.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item);
    onChange({ ...resume, experience });
  }

  function updateProject(index: number, patch: Partial<StructuredResume["projects"][number]>) {
    const projects = resume.projects.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item);
    onChange({ ...resume, projects });
  }

  function updateStringList(field: "skills" | "education" | "achievements" | "certifications", items: string[]) {
    onChange({ ...resume, [field]: items.map((item) => item.trim()).filter(Boolean) });
  }

  return (
    <details className="reviewEditor" open>
      <summary>Structured resume editor</summary>
      <div className="editorStats">
        <span>{resume.experience.length} experience</span>
        <span>{resume.projects.length} projects</span>
        <span>{resume.skills.length} skills</span>
        <span>{resume.certifications.length} certifications</span>
      </div>
      <div className="editorSection">
        <h4>Profile</h4>
        <div className="gridTwo">
          <label>Name<input value={resume.profile.name ?? ""} onChange={(event) => updateProfile("name", event.target.value)} /></label>
          <label>Location<input value={resume.profile.location ?? ""} onChange={(event) => updateProfile("location", event.target.value)} /></label>
        </div>
        <label>Summary<textarea rows={3} value={resume.profile.summary ?? ""} onChange={(event) => updateProfile("summary", event.target.value)} /></label>
        <div className="gridTwo">
          <label>Email<input value={resume.profile.email ?? ""} onChange={(event) => updateProfile("email", event.target.value)} /></label>
          <label>Phone<input value={resume.profile.phone ?? ""} onChange={(event) => updateProfile("phone", event.target.value)} /></label>
        </div>
        <div className="gridTwo">
          <label>LinkedIn<input value={resume.profile.linkedin ?? ""} onChange={(event) => updateProfile("linkedin", event.target.value)} /></label>
          <label>GitHub<input value={resume.profile.github ?? ""} onChange={(event) => updateProfile("github", event.target.value)} /></label>
        </div>
      </div>

      <div className="editorSection">
        <div className="editorTitle">
          <h4>Experience</h4>
          <button type="button" className="tinyButton" onClick={() => onChange({ ...resume, experience: [...resume.experience, { title: "", company: "", duration: "", location: "", highlights: [] }] })}>Add</button>
        </div>
        {resume.experience.map((item, index) => (
          <div className="editorCard" key={`experience-${index}`}>
            <div className="itemToolbar">
              <strong>Experience {index + 1}</strong>
              <div>
                <button type="button" className="tinyButton" disabled={index === 0} onClick={() => onChange({ ...resume, experience: moveItem(resume.experience, index, index - 1) })}>Up</button>
                <button type="button" className="tinyButton" disabled={index === resume.experience.length - 1} onClick={() => onChange({ ...resume, experience: moveItem(resume.experience, index, index + 1) })}>Down</button>
              </div>
            </div>
            <div className="gridTwo">
              <label>Title<input value={item.title ?? ""} onChange={(event) => updateExperience(index, { title: event.target.value })} /></label>
              <label>Company<input value={item.company ?? ""} onChange={(event) => updateExperience(index, { company: event.target.value })} /></label>
            </div>
            <div className="gridTwo">
              <label>Duration<input value={item.duration ?? ""} onChange={(event) => updateExperience(index, { duration: event.target.value })} /></label>
              <label>Location<input value={item.location ?? ""} onChange={(event) => updateExperience(index, { location: event.target.value })} /></label>
            </div>
            <label>Highlights<textarea rows={4} value={item.highlights.join("\n")} onChange={(event) => updateExperience(index, { highlights: lines(event.target.value) })} /></label>
            <button type="button" className="dangerButton" onClick={() => onChange({ ...resume, experience: resume.experience.filter((_item, itemIndex) => itemIndex !== index) })}>Remove experience</button>
          </div>
        ))}
      </div>

      <div className="editorSection">
        <div className="editorTitle">
          <h4>Projects</h4>
          <button type="button" className="tinyButton" onClick={() => onChange({ ...resume, projects: [...resume.projects, { name: "New Project", duration: "", techStack: [], highlights: [] }] })}>Add</button>
        </div>
        {resume.projects.map((item, index) => (
          <div className="editorCard" key={`project-${index}`}>
            <div className="itemToolbar">
              <strong>Project {index + 1}</strong>
              <div>
                <button type="button" className="tinyButton" disabled={index === 0} onClick={() => onChange({ ...resume, projects: moveItem(resume.projects, index, index - 1) })}>Up</button>
                <button type="button" className="tinyButton" disabled={index === resume.projects.length - 1} onClick={() => onChange({ ...resume, projects: moveItem(resume.projects, index, index + 1) })}>Down</button>
              </div>
            </div>
            <div className="gridTwo">
              <label>Name<input value={item.name} onChange={(event) => updateProject(index, { name: event.target.value })} /></label>
              <label>Duration<input value={item.duration ?? ""} onChange={(event) => updateProject(index, { duration: event.target.value })} /></label>
            </div>
            <label>Tech stack<input value={item.techStack.join(", ")} onChange={(event) => updateProject(index, { techStack: csv(event.target.value) })} /></label>
            <label>Highlights<textarea rows={4} value={item.highlights.join("\n")} onChange={(event) => updateProject(index, { highlights: lines(event.target.value) })} /></label>
            <button type="button" className="dangerButton" onClick={() => onChange({ ...resume, projects: resume.projects.filter((_item, itemIndex) => itemIndex !== index) })}>Remove project</button>
          </div>
        ))}
      </div>

      <div className="editorSection">
        <h4>Other Details</h4>
        <ListEditor title="Skills" items={resume.skills} placeholder="Add skill" onChange={(items) => updateStringList("skills", items)} />
        <ListEditor title="Education" items={resume.education} placeholder="Add education" onChange={(items) => updateStringList("education", items)} />
        <ListEditor title="Achievements" items={resume.achievements} placeholder="Add achievement" onChange={(items) => updateStringList("achievements", items)} />
        <ListEditor title="Certifications" items={resume.certifications} placeholder="Add certification" onChange={(items) => updateStringList("certifications", items)} />
      </div>

      <div className="editorSection">
        <h4>Final resume text used for analysis</h4>
        <pre className="textPreview">{finalText}</pre>
      </div>
    </details>
  );
}

function ListEditor({
  title,
  items,
  placeholder,
  onChange,
}: {
  title: string;
  items: string[];
  placeholder: string;
  onChange: (items: string[]) => void;
}) {
  return (
    <div className="listEditor">
      <div className="editorTitle">
        <h4>{title}</h4>
        <button type="button" className="tinyButton" onClick={() => onChange([...items, ""])}>Add</button>
      </div>
      {items.length === 0 && <p className="hint">No {title.toLowerCase()} detected yet.</p>}
      {items.map((item, index) => (
        <div className="listRow" key={`${title}-${index}`}>
          <input
            aria-label={`${title} ${index + 1}`}
            placeholder={placeholder}
            value={item}
            onChange={(event) => onChange(items.map((value, itemIndex) => itemIndex === index ? event.target.value : value))}
          />
          <button type="button" className="tinyButton" disabled={index === 0} onClick={() => onChange(moveItem(items, index, index - 1))}>Up</button>
          <button type="button" className="tinyButton" disabled={index === items.length - 1} onClick={() => onChange(moveItem(items, index, index + 1))}>Down</button>
          <button type="button" className="dangerButton" onClick={() => onChange(items.filter((_item, itemIndex) => itemIndex !== index))}>Remove</button>
        </div>
      ))}
    </div>
  );
}

function ParsedJdEditor({
  parsedJd,
  finalText,
  onChange,
}: {
  parsedJd: ParsedJobDescription;
  finalText: string;
  onChange: (jd: ParsedJobDescription) => void;
}) {
  function update(field: keyof ParsedJobDescription, value: ParsedJobDescription[keyof ParsedJobDescription]) {
    onChange({ ...parsedJd, [field]: value });
  }

  function updateExperience(field: "minYears" | "maxYears", value: string) {
    const numeric = value === "" ? null : Number(value);
    onChange({
      ...parsedJd,
      experienceRange: {
        ...parsedJd.experienceRange,
        [field]: Number.isFinite(numeric) ? numeric : null,
      },
    });
  }

  const experience =
    parsedJd.experienceRange.minYears === undefined || parsedJd.experienceRange.minYears === null
      ? "Not detected"
      : `${parsedJd.experienceRange.minYears}${parsedJd.experienceRange.maxYears ? `-${parsedJd.experienceRange.maxYears}` : "+"} years`;

  return (
    <details className="reviewEditor" open>
      <summary>Structured JD editor</summary>
      <div className="editorStats">
        <span>{parsedJd.requiredSkills.length} required</span>
        <span>{parsedJd.preferredSkills.length} preferred</span>
        <span>{parsedJd.requiredCertifications.length} certifications</span>
        <span>{(parsedJd.emphasizedRequirements ?? []).length} emphasized</span>
        <span>{experience}</span>
      </div>
      <div className="editorSection">
        <h4>Role and Experience</h4>
        <label>Role title<input value={parsedJd.roleTitle ?? ""} onChange={(event) => update("roleTitle", event.target.value)} /></label>
        <div className="gridTwo">
          <label>Minimum years<input type="number" min={0} max={50} step="0.1" value={parsedJd.experienceRange.minYears ?? ""} onChange={(event) => updateExperience("minYears", event.target.value)} /></label>
          <label>Maximum years<input type="number" min={0} max={50} step="0.1" value={parsedJd.experienceRange.maxYears ?? ""} onChange={(event) => updateExperience("maxYears", event.target.value)} /></label>
        </div>
      </div>
      <div className="editorSection">
        <ListEditor title="Required Skills" items={parsedJd.requiredSkills} placeholder="Add required skill" onChange={(items) => update("requiredSkills", items)} />
        <ListEditor title="Preferred Skills" items={parsedJd.preferredSkills} placeholder="Add preferred skill" onChange={(items) => update("preferredSkills", items)} />
        <ListEditor title="Required Certifications" items={parsedJd.requiredCertifications} placeholder="Add certification requirement" onChange={(items) => update("requiredCertifications", items)} />
        <ListEditor title="Emphasized Requirements" items={parsedJd.emphasizedRequirements ?? []} placeholder="Add must-have or strongly emphasized requirement" onChange={(items) => update("emphasizedRequirements", items)} />
        <ListEditor title="Responsibilities" items={parsedJd.responsibilities} placeholder="Add responsibility" onChange={(items) => update("responsibilities", items)} />
        <ListEditor title="Locations" items={parsedJd.locations} placeholder="Add location" onChange={(items) => update("locations", items)} />
        <ListEditor title="Work Modes" items={parsedJd.workModes} placeholder="Add work mode" onChange={(items) => update("workModes", items)} />
        <ListEditor title="Seniority Signals" items={parsedJd.senioritySignals} placeholder="Add seniority signal" onChange={(items) => update("senioritySignals", items)} />
      </div>
      <div className="editorSection">
        <h4>Final JD text used for analysis</h4>
        <pre className="textPreview">{finalText}</pre>
      </div>
    </details>
  );
}

function formatStructuredResume(resume: StructuredResume) {
  const output: string[] = [];
  if (resume.profile.name) output.push(resume.profile.name);
  if (resume.profile.location) output.push(`Location: ${resume.profile.location}`);
  const contacts = [resume.profile.email, resume.profile.phone, resume.profile.linkedin, resume.profile.github].filter(Boolean);
  if (contacts.length) output.push(`Contact: ${contacts.join(" | ")}`);
  if (resume.profile.summary) output.push("", "Summary", resume.profile.summary);
  if (resume.experience.length) {
    output.push("", "Experience");
    resume.experience.forEach((item) => {
      output.push([item.title, item.company, item.duration].filter(Boolean).join(" - "));
      item.highlights.forEach((highlight) => output.push(`- ${highlight}`));
    });
  }
  if (resume.projects.length) {
    output.push("", "Projects");
    resume.projects.forEach((item) => {
      output.push(item.duration ? `${item.name} (${item.duration})` : item.name);
      if (item.techStack.length) output.push(`Tech: ${item.techStack.join(", ")}`);
      item.highlights.forEach((highlight) => output.push(`- ${highlight}`));
    });
  }
  if (resume.skills.length) output.push("", "Skills", resume.skills.join(", "));
  if (resume.education.length) output.push("", "Education", ...resume.education);
  if (resume.achievements.length) output.push("", "Achievements", ...resume.achievements.map((item) => `- ${item}`));
  if (resume.certifications.length) output.push("", "Certifications", ...resume.certifications.map((item) => `- ${item}`));
  return output.join("\n").trim();
}

function rewriteSuggestionKey(item: ResumeRewriteSuggestion, index: number) {
  return `${index}:${item.targetRequirement}:${item.evidenceSource}:${item.rewrittenBullet}`;
}

function cleanResumeBullet(value: string) {
  return value.trim().replace(/^[-*•]\s*/, "").trim();
}

function addUniqueLine(items: string[], value: string) {
  const normalizedValue = normalizeLine(value);
  if (!normalizedValue) return;
  if (!items.some((item) => normalizeLine(item) === normalizedValue)) {
    items.push(value);
  }
}

function normalizeLine(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

function cloneStructuredResume(resume: StructuredResume): StructuredResume {
  return {
    ...resume,
    profile: { ...resume.profile },
    experience: resume.experience.map((entry) => ({ ...entry, highlights: [...entry.highlights] })),
    projects: resume.projects.map((project) => ({ ...project, techStack: [...project.techStack], highlights: [...project.highlights] })),
    skills: [...resume.skills],
    education: [...resume.education],
    achievements: [...resume.achievements],
    certifications: [...resume.certifications],
  };
}

function buildResumeVersionComparison(currentResume: StructuredResume, version: ResumeVersionRecord): ResumeVersionComparison {
  const currentLines = resumeComparableLines(currentResume);
  const versionLines = resumeComparableLines(version.structuredResume);
  const currentSet = new Set(currentLines.map(normalizeLine));
  const versionSet = new Set(versionLines.map(normalizeLine));
  const addedInVersion = versionLines.filter((line) => !currentSet.has(normalizeLine(line))).slice(0, 12);
  const missingFromVersion = currentLines.filter((line) => !versionSet.has(normalizeLine(line))).slice(0, 12);
  return {
    versionId: version.id,
    title: version.title,
    summary: `${addedInVersion.length} line(s) only in version, ${missingFromVersion.length} line(s) only in current draft.`,
    currentCounts: resumeSnapshotCounts(currentResume),
    versionCounts: resumeSnapshotCounts(version.structuredResume),
    addedInVersion,
    missingFromVersion,
  };
}

function resumeSnapshotCounts(resume: StructuredResume): ResumeSnapshotCounts {
  return {
    experience: resume.experience.length,
    projects: resume.projects.length,
    skills: resume.skills.length,
    certifications: resume.certifications.length,
    bullets: resume.experience.reduce((count, item) => count + item.highlights.length, 0)
      + resume.projects.reduce((count, item) => count + item.highlights.length, 0)
      + resume.achievements.length,
  };
}

function resumeComparableLines(resume: StructuredResume) {
  return [
    ...resume.experience.flatMap((item) => [item.title, item.company, ...item.highlights]),
    ...resume.projects.flatMap((item) => [item.name, ...item.techStack, ...item.highlights]),
    ...resume.skills,
    ...resume.certifications,
    ...resume.achievements,
  ].filter((item): item is string => Boolean(item && item.trim()));
}

function formatParsedJd(jd: ParsedJobDescription) {
  const output: string[] = [];
  if (jd.roleTitle) output.push(`Role: ${jd.roleTitle}`);
  if (jd.experienceRange.minYears !== null && jd.experienceRange.minYears !== undefined) {
    const max = jd.experienceRange.maxYears !== null && jd.experienceRange.maxYears !== undefined ? ` to ${jd.experienceRange.maxYears}` : "+";
    output.push(`Experience: ${jd.experienceRange.minYears}${max} years`);
  }
  if (jd.requiredSkills.length) output.push("", "Required Skills", ...jd.requiredSkills.map((item) => `- ${item}`));
  if (jd.preferredSkills.length) output.push("", "Preferred Skills", ...jd.preferredSkills.map((item) => `- ${item}`));
  if (jd.requiredCertifications.length) output.push("", "Required Certifications", ...jd.requiredCertifications.map((item) => `- ${item}`));
  if ((jd.emphasizedRequirements ?? []).length) output.push("", "Emphasized Requirements", ...(jd.emphasizedRequirements ?? []).map((item) => `- ${item}`));
  if (jd.responsibilities.length) output.push("", "Responsibilities", ...jd.responsibilities.map((item) => `- ${item}`));
  if (jd.locations.length) output.push("", "Locations", jd.locations.join(", "));
  if (jd.workModes.length) output.push("", "Work Modes", jd.workModes.join(", "));
  if (jd.senioritySignals.length) output.push("", "Seniority Signals", ...jd.senioritySignals.map((item) => `- ${item}`));
  return output.join("\n").trim();
}

function moveItem<T>(items: T[], fromIndex: number, toIndex: number) {
  if (toIndex < 0 || toIndex >= items.length) return items;
  const copy = [...items];
  const [item] = copy.splice(fromIndex, 1);
  copy.splice(toIndex, 0, item);
  return copy;
}

function csv(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function lines(value: string) {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function ParsedJdPanel({ parsedJd }: { parsedJd: JdParseResponse["parsedJobDescription"] }) {
  const experience =
    parsedJd.experienceRange.minYears === undefined || parsedJd.experienceRange.minYears === null
      ? "Not detected"
      : `${parsedJd.experienceRange.minYears}${parsedJd.experienceRange.maxYears ? `-${parsedJd.experienceRange.maxYears}` : "+"} years`;

  return (
    <div className="reviewSummary">
      <div>
        <span>Role</span>
        <strong>{parsedJd.roleTitle || "Not detected"}</strong>
      </div>
      <div>
        <span>Experience</span>
        <strong>{experience}</strong>
      </div>
      <ReviewTags title="Required" items={parsedJd.requiredSkills} />
      <ReviewTags title="Preferred" items={parsedJd.preferredSkills} />
      <ReviewTags title="Certifications" items={parsedJd.requiredCertifications} />
      <ReviewTags title="Emphasized" items={parsedJd.emphasizedRequirements ?? []} />
      <ReviewTags title="Location" items={parsedJd.locations} />
      <ReviewTags title="Work mode" items={parsedJd.workModes} />
    </div>
  );
}

function ReviewTags({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <span>{title}</span>
      <div className="miniTags">
        {items.length ? items.map((item) => <em key={`${title}-${item}`}>{item}</em>) : <em>None</em>}
      </div>
    </div>
  );
}

function OpportunityPanel({ result }: { result: AnalysisResponse }) {
  const scores = [
    ["Technical", result.technicalMatchScore],
    ["Shortlisting", result.shortlistingScore],
    ["Interview readiness", result.interviewReadinessScore],
    ["Overall opportunity", result.overallOpportunityScore],
  ].filter((item): item is [string, number] => typeof item[1] === "number");

  return (
    <div className="panel">
      <h3>Opportunity Scores</h3>
      <div className="scoreGrid">
        {scores.map(([label, score]) => (
          <div className="scoreTile" key={label}>
            <span>{label}</span>
            <strong>{score}%</strong>
          </div>
        ))}
      </div>
      {result.recommendedAction && <p className="recommendation">{result.recommendedAction}</p>}
    </div>
  );
}

function ScoreBreakdown({ items }: { items: AnalysisResponse["scoreBreakdown"] }) {
  return (
    <div className="panel">
      <h3>Explainable Score Breakdown</h3>
      <div className="breakdownList">
        {items.map((item) => (
          <div className="breakdownItem" key={item.category}>
            <div className="breakdownHeader">
              <strong>{formatCategory(item.category)}</strong>
              <span>{item.score}% x {item.weight}% = {item.weightedScore}</span>
            </div>
            <div className="meter"><span style={{ width: `${item.score}%` }} /></div>
            <p>{item.reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function RequirementMatrix({ items }: { items: AnalysisResponse["requirementMatches"] }) {
  return (
    <div className="panel">
      <h3>Requirement Match Matrix</h3>
      <div className="matrixList">
        {items.map((item, index) => (
          <div className="matrixItem" key={`${item.requirement}-${index}`}>
            <div className="matrixTop">
              <strong>{item.requirement}</strong>
              <span className={`importance ${item.importance}`}>{item.importance}</span>
              <b>{item.score}%</b>
            </div>
            <div className="matrixMeta">
              <span>{formatCategory(item.category)}</span>
              <span>{formatCategory(item.evidenceSource)}</span>
              <span>{formatCategory(item.matchType)}</span>
            </div>
            <p>{item.bestEvidence || "No matching resume evidence found."}</p>
            <small>{item.reason}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

function PreparationIntelligencePanel({ preparation }: { preparation: NonNullable<AnalysisResponse["preparationIntelligence"]> }) {
  return (
    <div className="panel prepPanel">
      <div className="panelHeader">
        <div>
          <p className="eyebrow">Phase 3</p>
          <h3>Preparation Intelligence</h3>
        </div>
      </div>
      <p className="recommendation">{preparation.summary}</p>

      <div className="prepSection">
        <h4>Priority Topics</h4>
        <div className="prepTopicList">
          {preparation.priorityTopics.map((topic) => (
            <div className="prepTopic" key={`${topic.topic}-${topic.sourceRequirement}`}>
              <div className="prepTopicTop">
                <strong>{topic.topic}</strong>
                <span className={`priority ${topic.priority}`}>{topic.priority}</span>
              </div>
              <p>{topic.reason}</p>
              {topic.currentEvidence && <small>Evidence: {topic.currentEvidence}</small>}
              <small>Target depth: {topic.targetDepth}</small>
              <ul>
                {topic.actions.map((action, index) => <li key={`${topic.topic}-action-${index}`}>{action}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="prepSection">
        <h4>Dynamic Daily Plan</h4>
        <div className="prepDayList">
          {preparation.dailyPlan.map((day) => (
            <div className="prepDay" key={`prep-day-${day.day}`}>
              <div className="prepDayTop">
                <strong>Day {day.day}</strong>
                <span>{day.focus}</span>
              </div>
              <p>{day.goal}</p>
              <ul>
                {day.tasks.map((task, index) => <li key={`prep-day-${day.day}-task-${index}`}>{task}</li>)}
              </ul>
              <small>Output: {day.output}</small>
            </div>
          ))}
        </div>
      </div>

      <div className="prepSection">
        <h4>Cross-Question Chains</h4>
        <div className="prepChainList">
          {preparation.crossQuestionChains.map((chain) => (
            <div className="prepChain" key={`${chain.topic}-${chain.openingQuestion}`}>
              <strong>{chain.topic}</strong>
              <p>{chain.openingQuestion}</p>
              <ol>
                {chain.followUps.map((question, index) => <li key={`${chain.topic}-follow-${index}`}>{question}</li>)}
              </ol>
              <small>Expected focus: {chain.expectedAnswerFocus}</small>
              <small>Risk: {chain.risk}</small>
            </div>
          ))}
        </div>
      </div>

      {preparation.phase5ResearchBacklog.length > 0 && (
        <div className="prepSection researchBacklog">
          <h4>Phase 5 Research Backlog</h4>
          <ul>
            {preparation.phase5ResearchBacklog.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function ShortlistingFactors({ items }: { items: AnalysisResponse["shortlistingFactors"] }) {
  return (
    <div className="panel">
      <h3>Shortlisting Factors</h3>
      <div className="factorList">
        {items.map((item) => (
          <div className={`factor ${item.impact}`} key={`${item.factor}-${item.reason}`}>
            <strong>{item.factor}</strong>
            <span>{item.impact}</span>
            <p>{item.reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatCategory(value: string) {
  return value.replace(/([A-Z])/g, " $1").replace(/^./, (char) => char.toUpperCase());
}

function DebugPanel({ debug }: { debug: NonNullable<AnalysisResponse["debug"]> }) {
  const provider = debug.provider ?? "not provided";
  const model = debug.model ?? "not provided";

  return (
    <details className="panel debugPanel" open>
      <summary>Debugger mode: {debug.mode} - {provider} / {model}</summary>
      <div className="debugGrid">
        <div>
          <h4>LLM Selection</h4>
          <p><strong>Mode:</strong> {debug.mode}</p>
          <p><strong>Provider:</strong> {provider}</p>
          <p><strong>Model:</strong> {model}</p>
        </div>
        <div>
          <h4>Received Context</h4>
          <p><strong>Experience:</strong> {debug.receivedExperienceYears} year(s)</p>
          <p><strong>Target role:</strong> {debug.receivedTargetRole}</p>
          <p><strong>Current stack:</strong> {debug.receivedCurrentStack.join(", ")}</p>
        </div>
      </div>
      <h4>Score Reason</h4>
      <p>{debug.scoreReason}</p>
      <h4>Prompt Preview</h4>
      <pre>{debug.promptPreview}</pre>
    </details>
  );
}

function Card({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      <ul>
        {items.map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}
      </ul>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
