import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type AnalysisResponse = {
  technicalMatchScore: number;
  shortlistingScore?: number | null;
  interviewReadinessScore?: number | null;
  overallOpportunityScore?: number | null;
  overallSummary: string;
  fitCategory: "Strong Fit" | "Good Fit" | "Partial Fit" | "Weak Fit";
  scoreBreakdown: Array<{ category: string; weight: number; score: number; weightedScore: number; reason: string }>;
  shortlistingFactors: Array<{ factor: string; impact: "positive" | "neutral" | "negative"; reason: string }>;
  recommendedAction?: string | null;
  matchingSkills: Array<{ skill: string; evidenceFromResume: string; jdRequirement: string }>;
  weaklyEvidencedSkills: Array<{ skill: string; source: string; whyWeak: string; howToStrengthenResume: string }>;
  missingSkills: Array<{ skill: string; importance: "high" | "medium" | "low"; whyItMatters: string; howToPrepare: string }>;
  resumeImprovements: Array<{ currentIssue: string; suggestedBullet: string; reason: string }>;
  interviewQuestions: Array<{ topic: string; question: string; difficulty: "easy" | "medium" | "hard"; expectedFocus: string }>;
  crossQuestions: Array<{ question: string; whyAsked: string; expectedAnswerHint: string }>;
  systemDesignReadiness: { level: "strong" | "moderate" | "weak"; reason: string; topicsToPrepare: string[] };
  sevenDayPlan: Array<{ day: number; focus: string; tasks: string[] }>;
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

type JdParseResponse = {
  normalizedJobDescriptionText: string;
  warnings: string[];
  parsedJobDescription: {
    roleTitle?: string | null;
    experienceRange: { minYears?: number | null; maxYears?: number | null };
    requiredSkills: string[];
    preferredSkills: string[];
    responsibilities: string[];
    locations: string[];
    workModes: string[];
    senioritySignals: string[];
  };
};

const modelOptions: Record<LlmProvider, string[]> = {
  groq: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
  openai: ["gpt-4.1-mini", "gpt-4o-mini"],
  gemini: ["gemini-2.0-flash", "gemini-1.5-flash"],
};

const defaultResume =
  "3 years .NET fullstack developer at Capgemini. Worked on ASP.NET Core APIs, SQL Server, React UI changes, bug fixes, production support, API integration, and Agile delivery. Familiar with Java, Python, C++, and basic cloud concepts.";

const defaultJd =
  "Looking for a skilled .NET Developer with 2 to 5 years of experience in ASP.NET, .NET Core, C#, Web API, MVC and Azure Cloud Services. Strong knowledge of LINQ, Entity Framework, HTML, CSS, JavaScript, jQuery, Azure DevOps CI/CD pipelines, code compliance and enterprise application development.";

function App() {
  const [resumeText, setResumeText] = useState(defaultResume);
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
  const [resumeSource, setResumeSource] = useState<ResumeSource>("text");
  const [uploading, setUploading] = useState(false);
  const [normalizing, setNormalizing] = useState(false);
  const [parsingJd, setParsingJd] = useState(false);
  const [uploadInfo, setUploadInfo] = useState("");
  const [normalizeInfo, setNormalizeInfo] = useState("");
  const [jdParseInfo, setJdParseInfo] = useState("");
  const [parsedJd, setParsedJd] = useState<JdParseResponse["parsedJobDescription"] | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function analyze() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("http://localhost:8000/ai/resume-jd/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resumeText,
          jobDescriptionText,
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
        }),
      });

      if (!response.ok) {
        const details = await response.text();
        throw new Error(details || "Analysis failed");
      }

      setResult((await response.json()) as AnalysisResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
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
      const response = await fetch("http://localhost:8000/ai/resume/extract", {
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

  async function normalizeCurrentResume() {
    setNormalizing(true);
    setError("");
    setNormalizeInfo("");

    try {
      const response = await fetch("http://localhost:8000/ai/resume/normalize", {
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
        structuredResume: {
          skills: string[];
          experience: unknown[];
          projects: unknown[];
        };
      };

      setResumeText(normalized.normalizedResumeText);
      const warnings = normalized.warnings.length ? ` Warnings: ${normalized.warnings.join(" ")}` : "";
      setNormalizeInfo(
        `Normalized ${normalized.structuredResume.experience.length} experience item(s), ${normalized.structuredResume.projects.length} project(s), ${normalized.structuredResume.skills.length} skill(s).${warnings}`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume normalization failed");
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
      const response = await fetch("http://localhost:8000/ai/jd/parse", {
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
      setJdParseInfo(`Parsed ${requiredCount} required skill(s), ${preferredCount} preferred skill(s).${warnings}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "JD parsing failed");
    } finally {
      setParsingJd(false);
    }
  }

  return (
    <main className="shell">
      <section className="header">
        <div>
          <p className="eyebrow">Level 1</p>
          <h1>Career Agent OS</h1>
          <p className="subtitle">Resume and JD technical fit analyzer for job switch preparation.</p>
        </div>
        <div className="scorePreview">{result ? `${result.technicalMatchScore}%` : "Mock"}</div>
      </section>

      <section className="layout">
        <form className="panel inputPanel" onSubmit={(event) => { event.preventDefault(); analyze(); }}>
          <div className="controlBand">
            <div>
              <span className="fieldTitle">Analyzer mode</span>
              <div className="segmented">
                <button type="button" className={llmMode === "mock" ? "active" : ""} onClick={() => setLlmMode("mock")}>Mock</button>
                <button type="button" className={llmMode === "live" ? "active" : ""} onClick={() => setLlmMode("live")}>Live LLM</button>
              </div>
            </div>
            <label>
              Provider
              <select
                value={llmProvider}
                onChange={(event) => {
                  const provider = event.target.value as LlmProvider;
                  setLlmProvider(provider);
                  setLlmModel(modelOptions[provider][0]);
                }}
              >
                <option value="groq">Groq</option>
                <option value="openai">OpenAI</option>
                <option value="gemini">Gemini</option>
              </select>
            </label>
            <label>
              Model
              <select value={llmModel} onChange={(event) => setLlmModel(event.target.value)}>
                {modelOptions[llmProvider].map((model) => <option key={model} value={model}>{model}</option>)}
              </select>
            </label>
          </div>
          <div className="gridTwo">
            <label>
              Target role
              <input value={targetRole} onChange={(event) => setTargetRole(event.target.value)} />
            </label>
            <label>
              Experience years
              <input type="number" min={0} max={50} value={experienceYears} onChange={(event) => setExperienceYears(Number(event.target.value))} />
            </label>
          </div>
          <label>
            Preparation plan days
            <input type="number" min={1} max={30} value={preparationPlanDays} onChange={(event) => setPreparationPlanDays(Math.max(1, Math.min(30, Number(event.target.value) || 7)))} />
          </label>
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
          <div>
            <span className="fieldTitle">Resume source</span>
            <div className="segmented">
              <button type="button" className={resumeSource === "text" ? "active" : ""} onClick={() => setResumeSource("text")}>Text</button>
              <button type="button" className={resumeSource === "file" ? "active" : ""} onClick={() => setResumeSource("file")}>File upload</button>
            </div>
          </div>
          {resumeSource === "file" && (
            <label>
              Upload resume (.txt, .pdf, .docx)
              <input type="file" accept=".txt,.pdf,.docx" onChange={(event) => uploadResume(event.target.files?.[0] ?? null)} />
              {uploading && <span className="hint">Extracting resume...</span>}
              {uploadInfo && <span className="hint">{uploadInfo}</span>}
            </label>
          )}
          <label>
            Resume review window
            <textarea value={resumeText} onChange={(event) => setResumeText(event.target.value)} rows={8} />
          </label>
          <button type="button" className="secondaryButton" disabled={normalizing || resumeText.trim().length < 20} onClick={normalizeCurrentResume}>
            {normalizing ? "Normalizing..." : "Normalize Resume for Review"}
          </button>
          {normalizeInfo && <p className="hint">{normalizeInfo}</p>}
          <label>
            JD review window
            <textarea value={jobDescriptionText} onChange={(event) => setJobDescriptionText(event.target.value)} rows={8} />
          </label>
          <button type="button" className="secondaryButton" disabled={parsingJd || jobDescriptionText.trim().length < 20} onClick={parseCurrentJd}>
            {parsingJd ? "Parsing JD..." : "Parse JD for Review"}
          </button>
          {jdParseInfo && <p className="hint">{jdParseInfo}</p>}
          {parsedJd && <ParsedJdPanel parsedJd={parsedJd} />}
          <button disabled={loading}>{loading ? "Analyzing..." : "Analyze Technical Fit"}</button>
          {error && <p className="error">{error}</p>}
        </form>

        <section className="results">
          {!result && <EmptyState />}
          {result && <Results result={result} />}
        </section>
      </section>
    </main>
  );
}

function EmptyState() {
  return (
    <div className="panel empty">
      <h2>Ready to test the contract</h2>
      <p>Submit the sample data to verify the frontend, API endpoint, and response rendering before we plug in a real LLM.</p>
    </div>
  );
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
      {result.shortlistingFactors?.length > 0 && <ShortlistingFactors items={result.shortlistingFactors} />}
      <Card title="Matching Skills" items={result.matchingSkills.map((item) => `${item.skill}: ${item.evidenceFromResume}`)} />
      <Card title="Weakly Evidenced Skills" items={result.weaklyEvidencedSkills.map((item) => `${item.skill}: ${item.whyWeak}`)} />
      <Card title="Missing Skills" items={result.missingSkills.map((item) => `${item.skill} (${item.importance}): ${item.howToPrepare}`)} />
      <Card title="Resume Improvements" items={result.resumeImprovements.map((item) => `${item.suggestedBullet} Reason: ${item.reason}`)} />
      <Card title="Interview Questions" items={result.interviewQuestions.map((item) => `${item.topic}: ${item.question}`)} />
      <Card title="Cross-Questions" items={result.crossQuestions.map((item) => `${item.question} Hint: ${item.expectedAnswerHint}`)} />
      {result.debug && <DebugPanel debug={result.debug} />}
      <div className="panel">
        <h3>System Design Readiness: {result.systemDesignReadiness.level}</h3>
        <p>{result.systemDesignReadiness.reason}</p>
        <div className="tags">{result.systemDesignReadiness.topicsToPrepare.map((topic) => <span key={topic}>{topic}</span>)}</div>
      </div>
      <Card title={`${result.sevenDayPlan.length}-Day Plan`} items={result.sevenDayPlan.map((item) => `Day ${item.day} - ${item.focus}: ${item.tasks.join(" ")}`)} />
    </>
  );
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
