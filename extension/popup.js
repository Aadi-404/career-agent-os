const API_BASE_URL = "http://127.0.0.1:8001";

const state = {
  anonymousSessionId: null,
  sessionToken: null,
  jobDraft: null,
};

const els = {
  status: document.getElementById("status"),
  userId: document.getElementById("userId"),
  resumeSelect: document.getElementById("resumeSelect"),
  claimSession: document.getElementById("claimSession"),
  sessionInfo: document.getElementById("sessionInfo"),
  parsePage: document.getElementById("parsePage"),
  matchJob: document.getElementById("matchJob"),
  manualJd: document.getElementById("manualJd"),
  jobTitle: document.getElementById("jobTitle"),
  jobMeta: document.getElementById("jobMeta"),
  result: document.getElementById("result"),
};

bootstrap();

els.claimSession.addEventListener("click", claimSession);
els.parsePage.addEventListener("click", parseCurrentPage);
els.matchJob.addEventListener("click", matchJob);

async function bootstrap() {
  setStatus("Connecting...");
  const saved = await chrome.storage.local.get(["anonymousSessionId", "userId", "sessionToken"]);
  if (saved.userId) els.userId.value = saved.userId;
  const userId = els.userId.value.trim() || null;
  const response = await post("/extension/bootstrap", {
    userId,
    sessionToken: saved.sessionToken || null,
    anonymousSessionId: saved.anonymousSessionId || null,
  });
  state.anonymousSessionId = response.anonymousSession.id;
  state.sessionToken = response.userSession?.sessionToken || saved.sessionToken || null;
  if (response.userSession?.userId) els.userId.value = response.userSession.userId;
  await chrome.storage.local.set({
    anonymousSessionId: state.anonymousSessionId,
    sessionToken: state.sessionToken || "",
    userId: response.userSession?.userId || userId || "",
  });
  renderResumes(response.resumes);
  els.sessionInfo.textContent = response.userSession
    ? `Connected as ${response.userSession.displayName}. Session token active.`
    : `Anonymous session ${state.anonymousSessionId}. Connect a user to load saved resumes.`;
  setStatus(response.resumes.length ? "Ready" : "Connect user or paste resume/JD in app first");
}

async function claimSession() {
  const userId = els.userId.value.trim();
  if (!userId) {
    setStatus("Enter user id");
    return;
  }
  setStatus("Connecting user...");
  const response = await post("/extension/session/claim", {
    anonymousSessionId: state.anonymousSessionId,
    userId,
    displayName: userId,
  });
  state.anonymousSessionId = response.anonymousSession.id;
  state.sessionToken = response.userSession.sessionToken;
  await chrome.storage.local.set({ anonymousSessionId: state.anonymousSessionId, userId, sessionToken: state.sessionToken });
  renderResumes(response.resumes);
  els.sessionInfo.textContent = `Connected as ${userId}. Migrated ${response.migratedOpportunityCount} saved job(s).`;
  setStatus(response.resumes.length ? "Ready" : "No saved resumes");
}

async function parseCurrentPage() {
  setStatus("Parsing page...");
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const page = await chrome.tabs.sendMessage(tab.id, { type: "CAREER_AGENT_EXTRACT_JOB" });
  const draft = await post("/extension/jobs/parse-page", page);
  state.jobDraft = draft;
  els.manualJd.value = draft.description || "";
  els.jobTitle.textContent = draft.title || "Job parsed";
  els.jobMeta.textContent = `${draft.company || "Company unknown"} | ${draft.location || "Location unknown"} | ${draft.parseConfidence} confidence`;
  setStatus(draft.warnings?.length ? "Review JD text" : "Page parsed");
}

async function matchJob() {
  const resumeId = els.resumeSelect.value;
  const description = els.manualJd.value.trim() || state.jobDraft?.description || "";
  if (!resumeId) {
    renderResult("Select a saved resume first.", true);
    return;
  }
  if (description.length < 50) {
    renderResult("Paste the full JD before matching.", true);
    return;
  }
  setStatus("Matching...");
  els.matchJob.disabled = true;
  try {
    const analysis = await post("/extension/jobs/match", {
      userId: els.userId.value.trim(),
      sessionToken: state.sessionToken,
      anonymousSessionId: state.anonymousSessionId,
      resumeId,
      job: {
        title: state.jobDraft?.title || "Pasted job description",
        company: state.jobDraft?.company || null,
        location: state.jobDraft?.location || null,
        url: state.jobDraft?.url || null,
        description,
      },
      saveOpportunity: true,
      status: "viewed",
    });
    renderResult(`<strong>${analysis.analysis.technicalMatchScore}%</strong>${analysis.analysis.fitCategory}<br>${analysis.analysis.recommendedAction || ""}`);
    setStatus("Matched");
  } catch (error) {
    renderResult(error.message || "Match failed", true);
    setStatus("Error");
  } finally {
    els.matchJob.disabled = false;
  }
}

function renderResumes(resumes) {
  els.resumeSelect.innerHTML = "";
  if (!resumes.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No saved resumes found";
    els.resumeSelect.append(option);
    return;
  }
  for (const resume of resumes) {
    const option = document.createElement("option");
    option.value = resume.id;
    option.textContent = `${resume.title} - ${resume.summary}`;
    els.resumeSelect.append(option);
  }
}

function renderResult(html, isError = false) {
  els.result.classList.toggle("empty", isError);
  els.result.innerHTML = html;
}

function setStatus(value) {
  els.status.textContent = value;
}

async function post(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `${path} failed`);
  }
  return response.json();
}
