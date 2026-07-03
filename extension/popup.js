const API_BASE_URL = window.CAREER_AGENT_OS_EXTENSION_CONFIG?.apiBaseUrl || "http://127.0.0.1:8001";
const WEB_APP_URL = window.CAREER_AGENT_OS_EXTENSION_CONFIG?.webAppUrl || "http://127.0.0.1:5173";

const state = {
  anonymousSessionId: null,
  sessionToken: null,
  jobDraft: null,
  quota: null,
};

const els = {
  status: document.getElementById("status"),
  userId: document.getElementById("userId"),
  displayName: document.getElementById("displayName"),
  email: document.getElementById("email"),
  password: document.getElementById("password"),
  resumeSelect: document.getElementById("resumeSelect"),
  quotaTier: document.getElementById("quotaTier"),
  quotaUsed: document.getElementById("quotaUsed"),
  quotaLimit: document.getElementById("quotaLimit"),
  quotaRemaining: document.getElementById("quotaRemaining"),
  quotaReset: document.getElementById("quotaReset"),
  claimSession: document.getElementById("claimSession"),
  loginSession: document.getElementById("loginSession"),
  registerSession: document.getElementById("registerSession"),
  clearSession: document.getElementById("clearSession"),
  sessionInfo: document.getElementById("sessionInfo"),
  parsePage: document.getElementById("parsePage"),
  matchJob: document.getElementById("matchJob"),
  manualJd: document.getElementById("manualJd"),
  manualTitle: document.getElementById("manualTitle"),
  manualCompany: document.getElementById("manualCompany"),
  jobTitle: document.getElementById("jobTitle"),
  jobMeta: document.getElementById("jobMeta"),
  result: document.getElementById("result"),
  feedbackSite: document.getElementById("feedbackSite"),
  parserRating: document.getElementById("parserRating"),
  titleFound: document.getElementById("titleFound"),
  companyFound: document.getElementById("companyFound"),
  descriptionFound: document.getElementById("descriptionFound"),
  manualPasteUsed: document.getElementById("manualPasteUsed"),
  feedbackNotes: document.getElementById("feedbackNotes"),
  saveParserFeedback: document.getElementById("saveParserFeedback"),
};

bootstrap();

els.loginSession.addEventListener("click", loginSession);
els.registerSession.addEventListener("click", registerSession);
els.claimSession.addEventListener("click", claimSession);
els.clearSession.addEventListener("click", () => clearSession());
els.parsePage.addEventListener("click", parseCurrentPage);
els.matchJob.addEventListener("click", matchJob);
els.saveParserFeedback.addEventListener("click", saveParserFeedback);

async function bootstrap() {
  setStatus("Connecting...");
  try {
    const saved = await chrome.storage.local.get(["anonymousSessionId", "userId", "displayName", "email", "sessionToken"]);
    if (saved.userId) els.userId.value = saved.userId;
    if (saved.displayName) els.displayName.value = saved.displayName;
    if (saved.email) els.email.value = saved.email;
    const userId = els.userId.value.trim() || null;
    const response = await post("/extension/bootstrap", {
      userId,
      sessionToken: saved.sessionToken || null,
      anonymousSessionId: saved.anonymousSessionId || null,
    });
    state.anonymousSessionId = response.anonymousSession.id;
    state.sessionToken = response.userSession?.sessionToken || saved.sessionToken || null;
    state.quota = response.quota || null;
    if (response.userSession?.userId) els.userId.value = response.userSession.userId;
    await chrome.storage.local.set({
      anonymousSessionId: state.anonymousSessionId,
      sessionToken: state.sessionToken || "",
      userId: response.userSession?.userId || userId || "",
      displayName: response.userSession?.displayName || saved.displayName || userId || "",
      email: saved.email || "",
    });
    renderResumes(response.resumes);
    renderQuota(state.quota);
    els.sessionInfo.textContent = response.userSession
      ? `Connected as ${response.userSession.displayName}. Session token active.`
      : `Anonymous session ${state.anonymousSessionId}. Connect a user to load saved resumes.`;
    setStatus(response.resumes.length ? "Ready" : "Connect user or paste resume/JD in app first");
  } catch (error) {
    await clearSession("Saved session failed. Connect again.");
  }
}

async function loginSession() {
  const identifier = els.userId.value.trim();
  const password = els.password.value;
  if (!identifier || password.length < 8) {
    setStatus("Enter user/email and password");
    return;
  }
  setStatus("Logging in...");
  await authenticate("/auth/login", {
    userIdOrEmail: identifier,
    password,
  });
}

async function registerSession() {
  const userId = els.userId.value.trim();
  const password = els.password.value;
  if (!userId || password.length < 8) {
    setStatus("Enter user id and 8+ character password");
    return;
  }
  setStatus("Registering...");
  await authenticate("/auth/register", {
    userId,
    displayName: els.displayName.value.trim() || userId,
    email: els.email.value.trim() || null,
    password,
    role: "member",
  });
}

async function authenticate(path, payload) {
  els.loginSession.disabled = true;
  els.registerSession.disabled = true;
  try {
    const session = await post(path, payload, { includeSessionHeader: false });
    state.sessionToken = session.sessionToken;
    els.userId.value = session.user.id;
    els.displayName.value = session.user.displayName;
    els.email.value = session.user.email || els.email.value.trim();
    els.password.value = "";
    await chrome.storage.local.set({
      userId: session.user.id,
      displayName: session.user.displayName,
      email: session.user.email || "",
      sessionToken: state.sessionToken,
      anonymousSessionId: state.anonymousSessionId || "",
    });
    await refreshConnectedWorkspace(session.user.displayName);
  } catch (error) {
    setStatus(error.message || "Authentication failed");
  } finally {
    els.loginSession.disabled = false;
    els.registerSession.disabled = false;
  }
}

async function refreshConnectedWorkspace(displayName) {
  const response = await post("/extension/bootstrap", {
    userId: els.userId.value.trim(),
    sessionToken: state.sessionToken,
    anonymousSessionId: state.anonymousSessionId,
  });
  state.anonymousSessionId = response.anonymousSession.id;
  state.sessionToken = response.userSession?.sessionToken || state.sessionToken;
  state.quota = response.quota || null;
  await chrome.storage.local.set({
    anonymousSessionId: state.anonymousSessionId,
    userId: response.userSession?.userId || els.userId.value.trim(),
    sessionToken: state.sessionToken || "",
  });
  renderResumes(response.resumes);
  renderQuota(state.quota);
  els.sessionInfo.textContent = `Connected as ${displayName || response.userSession?.displayName || els.userId.value.trim()}. ${response.resumes.length} saved resume(s).`;
  setStatus(response.resumes.length ? "Ready" : "No saved resumes");
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
  state.quota = response.quota || null;
  await chrome.storage.local.set({
    anonymousSessionId: state.anonymousSessionId,
    userId,
    displayName: els.displayName.value.trim() || userId,
    email: els.email.value.trim() || "",
    sessionToken: state.sessionToken,
  });
  renderResumes(response.resumes);
  renderQuota(state.quota);
  els.sessionInfo.textContent = `Connected as ${userId}. Migrated ${response.migratedOpportunityCount} saved job(s).`;
  setStatus(response.resumes.length ? "Ready" : "No saved resumes");
}

async function clearSession(message = "Session cleared. Connect again to load saved resumes.") {
  state.sessionToken = null;
  state.anonymousSessionId = null;
  state.jobDraft = null;
  els.password.value = "";
  await chrome.storage.local.remove(["anonymousSessionId", "sessionToken"]);
  renderResumes([]);
  renderQuota(null);
  els.sessionInfo.textContent = message;
  setStatus("Disconnected");
  try {
    const response = await post("/extension/bootstrap", {
      userId: null,
      sessionToken: null,
      anonymousSessionId: null,
    });
    state.anonymousSessionId = response.anonymousSession.id;
    state.quota = response.quota || null;
    await chrome.storage.local.set({ anonymousSessionId: state.anonymousSessionId });
    renderQuota(state.quota);
    els.sessionInfo.textContent = `${message} Anonymous session ${state.anonymousSessionId} is ready.`;
  } catch {
    els.sessionInfo.textContent = `${message} Backend is not reachable yet.`;
  }
}

async function parseCurrentPage() {
  setStatus("Parsing page...");
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const page = await chrome.tabs.sendMessage(tab.id, { type: "CAREER_AGENT_EXTRACT_JOB" });
  const draft = await post("/extension/jobs/parse-page", page);
  state.jobDraft = draft;
  els.manualJd.value = draft.description || "";
  els.manualTitle.value = draft.title || "";
  els.manualCompany.value = draft.company || "";
  els.jobTitle.textContent = draft.title || "Job parsed";
  els.jobMeta.textContent = `${draft.company || "Company unknown"} | ${draft.location || "Location unknown"} | ${draft.parseConfidence} confidence`;
  els.titleFound.checked = Boolean(draft.title);
  els.companyFound.checked = Boolean(draft.company);
  els.descriptionFound.checked = Boolean(draft.description && draft.description.length >= 50);
  els.parserRating.value = draft.parseConfidence === "high" ? "pass" : draft.parseConfidence === "medium" ? "partial" : "fail";
  setStatus(draft.warnings?.length ? "Review JD text" : "Page parsed");
}

async function saveParserFeedback() {
  const userId = els.userId.value.trim();
  if (!userId || !state.sessionToken) {
    setStatus("Connect user before saving feedback");
    return;
  }
  const description = els.manualJd.value.trim();
  setStatus("Saving parser feedback...");
  els.saveParserFeedback.disabled = true;
  try {
    await post("/extension/validation-results", {
      userId,
      site: els.feedbackSite.value,
      url: state.jobDraft?.url || null,
      parserRating: els.parserRating.value,
      autoParsed: Boolean(state.jobDraft),
      manualPasteUsed: els.manualPasteUsed.checked || description !== (state.jobDraft?.description || ""),
      titleFound: els.titleFound.checked,
      companyFound: els.companyFound.checked,
      descriptionFound: els.descriptionFound.checked || description.length >= 50,
      notes: els.feedbackNotes.value.trim() || null,
    });
    setStatus("Parser feedback saved");
  } catch (error) {
    setStatus(error.message || "Feedback save failed");
  } finally {
    els.saveParserFeedback.disabled = false;
  }
}

async function matchJob() {
  const resumeId = els.resumeSelect.value;
  const description = els.manualJd.value.trim() || state.jobDraft?.description || "";
  const title = els.manualTitle.value.trim() || state.jobDraft?.title || "Pasted job description";
  const company = els.manualCompany.value.trim() || state.jobDraft?.company || null;
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
    const response = await post("/extension/jobs/match", {
      userId: els.userId.value.trim(),
      sessionToken: state.sessionToken,
      anonymousSessionId: state.anonymousSessionId,
      resumeId,
      job: {
        title,
        company,
        location: state.jobDraft?.location || null,
        url: state.jobDraft?.url || null,
        description,
      },
      saveOpportunity: true,
      status: "viewed",
    });
    state.quota = response.quota || state.quota;
    renderQuota(state.quota);
    renderResult(renderMatchResult(response));
    setStatus("Matched");
  } catch (error) {
    if (error.statusCode === 429) {
      renderResult(`<strong>Usage limit reached</strong><br>${escapeHtml(error.message || "Monthly quota exceeded.")}<br><small>Login or upgrade from the web app to continue matching more jobs.</small>`, true);
      setStatus("Limit reached");
    } else {
      renderResult(escapeHtml(error.message || "Match failed"), true);
      setStatus("Error");
    }
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

function renderMatchResult(response) {
  const opportunity = response.jobOpportunity;
  const savedStatus = opportunity
    ? `<br><small>Saved as ${escapeHtml(opportunity.status)} job ${escapeHtml(opportunity.id)}.</small>`
    : "<br><small>Matched without saving a job opportunity.</small>";
  const link = opportunity
    ? `<br><a href="${escapeHtml(WEB_APP_URL)}" target="_blank" rel="noreferrer">Open web app history</a>`
    : "";
  return `<strong>${response.analysis.technicalMatchScore}%</strong>${escapeHtml(response.analysis.fitCategory)}<br>${escapeHtml(response.analysis.recommendedAction || "")}${savedStatus}${link}`;
}

function renderQuota(quota) {
  if (!quota) {
    els.quotaTier.textContent = "Connect to view quota";
    els.quotaUsed.textContent = "--";
    els.quotaLimit.textContent = "--";
    els.quotaRemaining.textContent = "--";
    els.quotaReset.textContent = "--";
    return;
  }
  els.quotaTier.textContent = `${formatLabel(quota.tier)} tier, ${formatLabel(quota.window || "monthly")} window`;
  els.quotaUsed.textContent = String(quota.usedUnits ?? 0);
  els.quotaLimit.textContent = quota.unlimited ? "Unlimited" : String(quota.limitUnits ?? "--");
  els.quotaRemaining.textContent = quota.unlimited ? "Unlimited" : String(quota.remainingUnits ?? "--");
  els.quotaReset.textContent = quota.resetAt ? formatShortDate(quota.resetAt) : "--";
}

function formatLabel(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatShortDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function setStatus(value) {
  els.status.textContent = value;
}

async function post(path, body, options = {}) {
  const includeSessionHeader = options.includeSessionHeader !== false;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(includeSessionHeader && state.sessionToken ? { "X-Session-Token": state.sessionToken } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text();
    let message = text || `${path} failed`;
    try {
      const payload = JSON.parse(text);
      message = normalizeApiMessage(payload.detail || payload.message || message);
      if (payload.requestId) message = `${message} (${payload.requestId})`;
    } catch {
      // Keep the raw text if the backend did not return JSON.
    }
    if (response.status === 401 || response.status === 403) {
      await clearSession("Session expired or invalid. Connect again.");
    }
    const error = new Error(message);
    error.statusCode = response.status;
    error.isQuotaError = response.status === 429;
    throw error;
  }
  return response.json();
}

function normalizeApiMessage(value) {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object" && item.msg) return item.msg;
      return "";
    }).filter(Boolean).join("; ") || "Request failed";
  }
  return "Request failed";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
