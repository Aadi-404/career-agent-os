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
type ActiveTask = "matching" | "review" | "report" | "preparation" | "progress" | "history";
type PreparationIntelligence = NonNullable<AnalysisResponse["preparationIntelligence"]>;

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
};

type HistoryAnalysisRecord = {
  id: string;
  title: string;
  fingerprint?: string | null;
  technicalMatchScore: number;
  fitCategory: string;
  createdAt: string;
  request: AnalyzeRequestPayload;
  response: AnalysisResponse;
};

type HistoryResumeRecord = {
  id: string;
  title: string;
  createdAt: string;
};

type HistoryJobDescriptionRecord = {
  id: string;
  title: string;
  company?: string | null;
  createdAt: string;
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

type TaskStatus = "todo" | "in_progress" | "done" | "skipped";
type ConfidenceLevel = "low" | "medium" | "high";

type PreparationProgress = {
  tasks: Record<string, TaskStatus>;
  notes: Record<string, string>;
  confidence: Record<string, ConfidenceLevel>;
};

type JobOpportunityStatus = "viewed" | "shortlisted" | "applied" | "interview" | "rejected" | "offer" | "archived";

type HistoryJobOpportunityRecord = {
  id: string;
  title: string;
  company?: string | null;
  location?: string | null;
  url?: string | null;
  description: string;
  status: JobOpportunityStatus;
  technicalMatchScore?: number | null;
  fitCategory?: string | null;
  createdAt: string;
  updatedAt: string;
};

type WorkspaceSummary = {
  resumeCount: number;
  jobDescriptionCount: number;
  analysisCount: number;
  preparationSessionCount: number;
  jobOpportunityCount: number;
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

const defaultUserId = "local-aditya";

function App() {
  const [activeTask, setActiveTask] = useState<ActiveTask>("matching");
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
  const [lastAnalysisFingerprint, setLastAnalysisFingerprint] = useState<string | null>(null);
  const [activePreparationSession, setActivePreparationSession] = useState<HistoryPreparationRecord | null>(null);
  const [progressSaving, setProgressSaving] = useState(false);
  const [progressInfo, setProgressInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [artifactLoading, setArtifactLoading] = useState("");
  const [error, setError] = useState("");
  const [preparationInfo, setPreparationInfo] = useState("");
  const [historyInfo, setHistoryInfo] = useState("");
  const [historyLoading, setHistoryLoading] = useState(false);
  const [workspaceSummary, setWorkspaceSummary] = useState<WorkspaceSummary | null>(null);
  const [analysisHistory, setAnalysisHistory] = useState<HistoryAnalysisRecord[]>([]);
  const [resumeHistory, setResumeHistory] = useState<HistoryResumeRecord[]>([]);
  const [jdHistory, setJdHistory] = useState<HistoryJobDescriptionRecord[]>([]);
  const [preparationHistory, setPreparationHistory] = useState<HistoryPreparationRecord[]>([]);
  const [jobOpportunityHistory, setJobOpportunityHistory] = useState<HistoryJobOpportunityRecord[]>([]);

  useEffect(() => {
    ensureLocalUser().catch(() => {
      setHistoryInfo("History is offline until the backend database is available.");
    });
  }, []);

  useEffect(() => {
    if (activeTask === "history") {
      loadHistory();
    }
  }, [activeTask]);

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
    await fetch(`${API_BASE_URL}/history/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: defaultUserId,
        displayName: "Aditya Local Workspace",
        email: "aditya.local@career-agent-os",
      }),
    });
  }

  async function lookupSavedAnalysis(fingerprint: string): Promise<HistoryAnalysisRecord | null> {
    await ensureLocalUser();
    const response = await fetch(`${API_BASE_URL}/history/analyses/lookup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: defaultUserId,
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: defaultUserId,
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: defaultUserId,
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: defaultUserId,
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: defaultUserId,
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
      const [workspaceResponse, analysesResponse, resumesResponse, jdsResponse, preparationsResponse, opportunitiesResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/history/users/${defaultUserId}/workspace`),
        fetch(`${API_BASE_URL}/history/users/${defaultUserId}/analyses`),
        fetch(`${API_BASE_URL}/history/users/${defaultUserId}/resumes`),
        fetch(`${API_BASE_URL}/history/users/${defaultUserId}/job-descriptions`),
        fetch(`${API_BASE_URL}/history/users/${defaultUserId}/preparation-sessions`),
        fetch(`${API_BASE_URL}/history/users/${defaultUserId}/job-opportunities`),
      ]);

      if (!workspaceResponse.ok || !analysesResponse.ok || !resumesResponse.ok || !jdsResponse.ok || !preparationsResponse.ok || !opportunitiesResponse.ok) {
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
      setHistoryInfo("Loaded saved PostgreSQL history.");
    } catch (err) {
      setHistoryInfo(err instanceof Error ? err.message : "History load failed");
    } finally {
      setHistoryLoading(false);
    }
  }

  async function updateJobOpportunityStatus(jobOpportunityId: string, status: JobOpportunityStatus) {
    setHistoryInfo("");
    try {
      const response = await fetch(`${API_BASE_URL}/history/job-opportunities/${jobOpportunityId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!response.ok) throw new Error("Opportunity status update failed");
      const updated = await response.json() as HistoryJobOpportunityRecord;
      setJobOpportunityHistory((items) => items.map((item) => item.id === updated.id ? updated : item));
      setHistoryInfo(`Updated ${updated.title} to ${updated.status}.`);
    } catch (err) {
      setHistoryInfo(err instanceof Error ? err.message : "Opportunity status update failed");
    }
  }

  async function analyze() {
    setLoading(true);
    setError("");
    setPreparationInfo("");
    setProgressInfo("");
    setResult(null);
    setActivePreparationSession(null);

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
        setLastAnalysisFingerprint(savedAnalysis.fingerprint ?? fingerprint);
        setResult(savedAnalysis.response);
        setHistoryInfo(`Reused saved score from ${formatDate(savedAnalysis.createdAt)}. Edit inputs to calculate a new score.`);
        setActiveTask("report");
        return;
      }
      const response = await fetch(`${API_BASE_URL}/ai/match/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const details = await response.text();
        throw new Error(details || "Analysis failed");
      }

      const analysis = await response.json() as AnalysisResponse;
      setLastAnalysisRequest(payload);
      setLastAnalysisFingerprint(fingerprint);
      setResult(analysis);
      try {
        const saved = await saveHistorySnapshot(payload, analysis, fingerprint);
        setLastSavedAnalysisId(saved.id);
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

  async function buildPreparation() {
    if (!result || !lastAnalysisRequest) {
      setError("Run resume matching before building the preparation plan.");
      return;
    }

    setPreparing(true);
    setError("");
    setPreparationInfo("");

    try {
      const response = await fetch(`${API_BASE_URL}/ai/preparation/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sourceRequest: lastAnalysisRequest,
          analysis: result,
          preparationPlanDays,
        }),
      });

      if (!response.ok) {
        const details = await response.text();
        throw new Error(details || "Preparation build failed");
      }

      const preparation = await response.json() as PreparationIntelligence;
      setResult({ ...result, preparationIntelligence: preparation });
      try {
        const savedSession = await savePreparationSession(preparation);
        setActivePreparationSession(savedSession);
        if (activeTask === "history") void loadHistory();
        setPreparationInfo(`Built and saved a ${preparation.dailyPlan.length}-day preparation plan from the latest match result.`);
      } catch (historyError) {
        setPreparationInfo(`Built a ${preparation.dailyPlan.length}-day preparation plan, but history save failed.`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preparation build failed");
    } finally {
      setPreparing(false);
    }
  }

  async function buildOptionalArtifact(
    label: string,
    endpoint: string,
    applyResult: (current: AnalysisResponse, payload: unknown) => AnalysisResponse,
  ) {
    if (!result || !lastAnalysisRequest) {
      setError("Run resume matching before generating optional artifacts.");
      return;
    }

    setArtifactLoading(label);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sourceRequest: lastAnalysisRequest,
          analysis: result,
          limit: 8,
        }),
      });

      if (!response.ok) {
        const details = await response.text();
        throw new Error(details || `${label} generation failed`);
      }

      const payload = await response.json();
      setResult(applyResult(result, payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} generation failed`);
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId: defaultUserId,
          status: nextStatus ?? inferPreparationStatus(nextProgress, activePreparationSession.plan),
          progress: nextProgress,
        }),
      });
      if (!response.ok) throw new Error("Progress save failed");
      const updated = await response.json() as HistoryPreparationRecord;
      setActivePreparationSession(updated);
      setPreparationHistory((items) => items.map((item) => item.id === updated.id ? updated : item));
      setProgressInfo("Progress saved.");
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
        const details = await response.text();
        throw new Error(details || "Resume extraction failed");
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
        const details = await response.text();
        throw new Error(details || "JD extraction failed");
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
        const details = await response.text();
        throw new Error(details || "Resume normalization failed");
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
        const details = await response.text();
        throw new Error(details || "JD parsing failed");
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
              {historyInfo && <p className="hint">{historyInfo}</p>}
              {result && (
                <div className="actionBar">
                  <button
                    type="button"
                    className="secondaryButton premiumButton"
                    disabled={Boolean(artifactLoading)}
                    onClick={() => buildOptionalArtifact(
                      "Resume improvements",
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
                    disabled={Boolean(artifactLoading)}
                    onClick={() => buildOptionalArtifact(
                      "Interview questions",
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
                    disabled={Boolean(artifactLoading)}
                    onClick={() => buildOptionalArtifact(
                      "Cross questions",
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
              <div className="prepControls">
                <label>
                  Preparation plan days
                  <input type="number" min={1} max={30} value={preparationPlanDays} onChange={(event) => setPreparationPlanDays(Math.max(1, Math.min(30, Number(event.target.value) || 7)))} />
                </label>
                <button type="button" className="premiumButton" disabled={!result || preparing} onClick={buildPreparation}>
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
              <PreparationProgressTracker
                currentSession={activePreparationSession}
                sessions={preparationHistory}
                currentResult={result}
                saving={progressSaving}
                info={progressInfo}
                onSelectSession={setActivePreparationSession}
                onUpdate={updatePreparationProgress}
              />
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
                currentResult={result}
                onOpportunityStatusChange={updateJobOpportunityStatus}
              />
            </TaskPanel>
          )}
        </section>
      </section>
    </main>
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
      status: "Next backend",
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

function HistoryPanel({
  summary,
  analyses,
  resumes,
  jobDescriptions,
  preparations,
  opportunities,
  currentResult,
  onOpportunityStatusChange,
}: {
  summary: WorkspaceSummary | null;
  analyses: HistoryAnalysisRecord[];
  resumes: HistoryResumeRecord[];
  jobDescriptions: HistoryJobDescriptionRecord[];
  preparations: HistoryPreparationRecord[];
  opportunities: HistoryJobOpportunityRecord[];
  currentResult: AnalysisResponse | null;
  onOpportunityStatusChange: (jobOpportunityId: string, status: JobOpportunityStatus) => void;
}) {
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
        </div>
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
        <h3>Job Opportunities</h3>
        {opportunities.length ? (
          <div className="historyList">
            {opportunities.slice(0, 10).map((opportunity) => (
              <div className="historyItem opportunityHistoryItem" key={opportunity.id}>
                <div>
                  <strong>{opportunity.title}</strong>
                  <small>
                    {[opportunity.company, opportunity.location, formatDate(opportunity.createdAt)].filter(Boolean).join(" - ")}
                  </small>
                  <p>{opportunity.description.slice(0, 180)}{opportunity.description.length > 180 ? "..." : ""}</p>
                </div>
                <span>{opportunity.technicalMatchScore ?? "--"}%</span>
                <em>{opportunity.fitCategory ?? "Not scored"}</em>
                <select
                  aria-label={`Status for ${opportunity.title}`}
                  value={opportunity.status}
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

      <div className="panel">
        <h3>Resume Versions</h3>
        {resumes.length ? <CompactHistoryList items={resumes.map((item) => ({ id: item.id, title: item.title, meta: formatDate(item.createdAt) }))} /> : <p className="hint">No resumes saved yet.</p>}
      </div>

      <div className="panel">
        <h3>JD Library</h3>
        {jobDescriptions.length ? <CompactHistoryList items={jobDescriptions.map((item) => ({ id: item.id, title: item.title, meta: item.company ? `${item.company} - ${formatDate(item.createdAt)}` : formatDate(item.createdAt) }))} /> : <p className="hint">No JDs saved yet.</p>}
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
