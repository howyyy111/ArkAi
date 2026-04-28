import { initializeApp } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js";
import {
  GoogleAuthProvider,
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from "https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js";

const chatForm = document.getElementById("chat-form");
const messages = document.getElementById("messages");
const promptInput = document.getElementById("prompt");
const seedButton = document.getElementById("seed-button");
const changeGmailButton = document.getElementById("change-gmail-button");
const newSessionButton = document.getElementById("new-session-button");
const submitButton = document.getElementById("submit-button");
const usernameModal = document.getElementById("username-modal");
const usernameForm = document.getElementById("username-form");
const usernameInput = document.getElementById("username-input");
const googleSigninButton = document.getElementById("google-signin-button");
const authHelper = document.getElementById("auth-helper");
const authPill = document.getElementById("auth-pill");
const stateTitle = document.getElementById("state-title");
const stateSummary = document.getElementById("state-summary");
const startDiagnosticButton = document.getElementById("start-diagnostic-button");
const diagnosticTopicInput = document.getElementById("diagnostic-topic");
const diagnosticGoalInput = document.getElementById("diagnostic-goal");
const diagnosticTimeInput = document.getElementById("diagnostic-time");
const diagnosticLevelSelect = document.getElementById("diagnostic-level");
const assessmentStatus = document.getElementById("assessment-status");
const diagnosticForm = document.getElementById("diagnostic-form");
const diagnosticQuestions = document.getElementById("diagnostic-questions");
const diagnosticResult = document.getElementById("diagnostic-result");
const downloadAssessmentPdfButton = document.getElementById("download-assessment-pdf-button");
const masteryScore = document.getElementById("mastery-score");
const masteryTopics = document.getElementById("mastery-topics");
const generateRoadmapButton = document.getElementById("generate-roadmap-button");
const rebuildRoadmapButton = document.getElementById("rebuild-roadmap-button");
const roadmapTopicInput = document.getElementById("roadmap-topic");
const roadmapGoalInput = document.getElementById("roadmap-goal");
const roadmapTimeInput = document.getElementById("roadmap-time");
const roadmapDeadlineInput = document.getElementById("roadmap-deadline");
const roadmapStatus = document.getElementById("roadmap-status");
const roadmapMode = document.getElementById("roadmap-mode");
const roadmapSummary = document.getElementById("roadmap-summary");
const roadmapSessionDetail = document.getElementById("roadmap-session-detail");
const roadmapBoard = document.getElementById("roadmap-board");
const materialFileInput = document.getElementById("material-file");
const materialTextInput = document.getElementById("material-text");
const materialQueryInput = document.getElementById("material-query");
const materialsMockStructureInput = document.getElementById("materials-mock-structure");
const materialsMockStyleInput = document.getElementById("materials-mock-style");
const materialsMockStyleFileInput = document.getElementById("materials-mock-style-file");
const uploadMaterialButton = document.getElementById("upload-material-button");
const askMaterialsButton = document.getElementById("ask-materials-button");
const createMaterialsMockTestButton = document.getElementById("create-materials-mock-test-button");
const deleteAllMaterialsButton = document.getElementById("delete-all-materials-button");
const materialsStatus = document.getElementById("materials-status");
const materialsLibrary = document.getElementById("materials-library");
const materialsSelectionSummary = document.getElementById("materials-selection-summary");
const voiceInputButton = document.getElementById("voice-input-button");
const voiceReplyButton = document.getElementById("voice-reply-button");
const voiceAutospeak = document.getElementById("voice-autospeak");
const voiceStatus = document.getElementById("voice-status");
const refreshInsightsButton = document.getElementById("refresh-insights-button");
const generateReportButton = document.getElementById("generate-report-button");
const interventionRisk = document.getElementById("intervention-risk");
const interventionSummary = document.getElementById("intervention-summary");
const evaluationBoard = document.getElementById("evaluation-board");
const reportBoard = document.getElementById("report-board");
const overviewMastery = document.getElementById("overview-mastery");
const overviewMasteryCaption = document.getElementById("overview-mastery-caption");
const overviewRoadmap = document.getElementById("overview-roadmap");
const overviewRoadmapCaption = document.getElementById("overview-roadmap-caption");
const overviewMaterials = document.getElementById("overview-materials");
const overviewMaterialsCaption = document.getElementById("overview-materials-caption");
const overviewRisk = document.getElementById("overview-risk");
const overviewRiskCaption = document.getElementById("overview-risk-caption");
const overviewBlurb = document.getElementById("overview-blurb");
const refreshSystemButton = document.getElementById("refresh-system-button");
const systemStackTitle = document.getElementById("system-stack-title");
const systemStackSummary = document.getElementById("system-stack-summary");
const systemReadinessBoard = document.getElementById("system-readiness-board");
const refreshDemoKitButton = document.getElementById("refresh-demo-kit-button");
const demoPitchTitle = document.getElementById("demo-pitch-title");
const demoPitchCopy = document.getElementById("demo-pitch-copy");
const demoMetricsBoard = document.getElementById("demo-metrics-board");
const demoPersonasBoard = document.getElementById("demo-personas-board");
const demoScriptBoard = document.getElementById("demo-script-board");
const focusTabs = Array.from(document.querySelectorAll("[data-view-target]"));
const focusViews = Array.from(document.querySelectorAll("[data-view]"));

const sessionStorageKey = "arkai-session-id";
const usernameStorageKey = "arkai-user-email";
const idTokenStorageKey = "arkai-id-token";
const historyStorageKeyPrefix = "arkai-history-";
const activeViewStorageKey = "arkai-active-view";
const requestTimeoutMs = 90000;

let authMode = "email_fallback";
let firebaseAuthClient = null;
let googleProvider = null;
let activeAssessment = null;
let activeRoadmap = null;
let activeRoadmapSummary = null;
let selectedMaterialIds = new Set();
let lastAgentReply = "";
let speechRecognition = null;
let isListening = false;
let pendingInputMode = "text";
let latestLearnerState = null;
let latestMaterials = [];
let latestInterventionPlan = null;
let latestWeeklyReport = null;
let selectedRoadmapSessionKey = "";
let previousSessionsExpanded = false;
let selectedHistoryItemKey = "";
let previousResourcesExpanded = false;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizePdfText(value) {
  return String(value ?? "")
    .replace(/[^\x20-\x7E]/g, "?")
    .replaceAll("\\", "\\\\")
    .replaceAll("(", "\\(")
    .replaceAll(")", "\\)");
}

function wrapPdfText(text, maxChars = 88) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  if (!words.length) {
    return [""];
  }

  const lines = [];
  let current = words[0];
  for (const word of words.slice(1)) {
    if (`${current} ${word}`.length <= maxChars) {
      current += ` ${word}`;
    } else {
      lines.push(current);
      current = word;
    }
  }
  lines.push(current);
  return lines;
}

function buildAssessmentPdfBlob(assessment) {
  const lines = [];
  const title = assessment.assessment_type === "mock_test" ? "ARKAIS Mock Test" : "ARKAIS Assessment";
  lines.push(title);
  lines.push(`Topic: ${assessment.topic || "General learning"}`);
  lines.push(`Level: ${assessment.level || "beginner"}`);
  if (assessment.goal) {
    lines.push(`Goal: ${assessment.goal}`);
  }
  lines.push("");

  (assessment.questions || []).forEach((question, index) => {
    const questionType = (question.question_type || "multiple_choice").replaceAll("_", " ");
    lines.push(`Question ${index + 1} (${questionType})`);
    wrapPdfText(question.prompt || "").forEach((line) => lines.push(line));
    if ((question.question_type || "multiple_choice") === "multiple_choice") {
      (question.options || []).forEach((option, optionIndex) => {
        const label = `${String.fromCharCode(65 + optionIndex)}. ${option}`;
        wrapPdfText(label || "", 82).forEach((line) => lines.push(line));
      });
    } else {
      lines.push("");
      lines.push("Answer:");
      const answerSpace = question.question_type === "essay" ? 10 : 4;
      for (let i = 0; i < answerSpace; i += 1) {
        lines.push("____________________________________________________________");
      }
    }
    lines.push("");
  });

  const pageHeight = 52;
  const pages = [];
  for (let i = 0; i < lines.length; i += pageHeight) {
    pages.push(lines.slice(i, i + pageHeight));
  }

  let pdf = "%PDF-1.4\n";
  const offsets = [];
  const objects = [];

  const addObject = (content) => {
    offsets.push(pdf.length);
    const objectNumber = offsets.length;
    pdf += `${objectNumber} 0 obj\n${content}\nendobj\n`;
    return objectNumber;
  };

  const fontObject = addObject("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
  const pageObjectNumbers = [];

  pages.forEach((pageLines) => {
    const contentCommands = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"];
    pageLines.forEach((line, lineIndex) => {
      const safeLine = normalizePdfText(line);
      if (lineIndex === 0) {
        contentCommands.push(`(${safeLine}) Tj`);
      } else {
        contentCommands.push("T*");
        contentCommands.push(`(${safeLine}) Tj`);
      }
    });
    contentCommands.push("ET");
    const stream = contentCommands.join("\n");
    const contentObject = addObject(`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`);
    const pageObject = addObject(
      `<< /Type /Page /Parent PAGES_REF 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 ${fontObject} 0 R >> >> /Contents ${contentObject} 0 R >>`
    );
    pageObjectNumbers.push(pageObject);
  });

  const kids = pageObjectNumbers.map((num) => `${num} 0 R`).join(" ");
  const pagesObjectNumber = addObject(`<< /Type /Pages /Kids [${kids}] /Count ${pageObjectNumbers.length} >>`);

  pageObjectNumbers.forEach((pageNumber) => {
    const marker = `${pageNumber} 0 obj\n`;
    const start = pdf.indexOf(marker);
    const end = pdf.indexOf("endobj\n", start);
    const original = pdf.slice(start, end);
    const updated = original.replace("PAGES_REF", String(pagesObjectNumber));
    pdf = `${pdf.slice(0, start)}${updated}${pdf.slice(end)}`;
  });

  const catalogObjectNumber = addObject(`<< /Type /Catalog /Pages ${pagesObjectNumber} 0 R >>`);
  const xrefStart = pdf.length;
  pdf += `xref\n0 ${offsets.length + 1}\n0000000000 65535 f \n`;
  offsets.forEach((offset) => {
    pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  });
  pdf += `trailer\n<< /Size ${offsets.length + 1} /Root ${catalogObjectNumber} 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;

  return new Blob([pdf], { type: "application/pdf" });
}

function updateAssessmentActions() {
  const hasAssessment = Boolean(activeAssessment?.assessment_id);
  downloadAssessmentPdfButton.classList.toggle("hidden", !hasAssessment);
}

function buildHistoryItemKey(item) {
  if (item?.record_id !== undefined && item?.record_id !== null && String(item.record_id).trim()) {
    return `record::${String(item.record_id).trim()}`;
  }
  return `${item.created_at || "time"}::${item.topic || "topic"}::${item.activity_type || "activity"}`;
}

function formatRelativeDays(value) {
  if (!value) {
    return "recently";
  }

  const then = new Date(value);
  if (Number.isNaN(then.getTime())) {
    return "recently";
  }

  const diffMs = Date.now() - then.getTime();
  const diffDays = Math.max(0, Math.round(diffMs / 86400000));
  if (diffDays <= 0) {
    return "today";
  }
  if (diffDays === 1) {
    return "1 day ago";
  }
  return `${diffDays} days ago`;
}

function getPreviousSessions() {
  return (latestLearnerState?.recent_history || [])
    .filter((item) => item?.topic)
    .map((item) => ({ ...item, key: buildHistoryItemKey(item) }));
}

function findHistoryItemByKey(key) {
  return getPreviousSessions().find((item) => item.key === key) || null;
}

function buildDetailFromHistoryItem(item) {
  const topic = item.topic || "Previous session";
  const title = `${topic} session`;
  const score = typeof item.score === "number" ? `${Math.round(item.score * 100)}%` : null;
  const status = item.activity_type || "session";
  const note = item.notes || `Reopen ${topic} and continue from the last saved step.`;

  return {
    key: item.key,
    title,
    focus: topic,
    duration_minutes: "",
    due_date: formatRelativeDays(item.created_at),
    phaseTitle: "Previous session",
    phaseGoal: topic,
    phaseOutcome: note,
    status: score ? `${status} • ${score}` : status,
    sourceLabel: "Previous session",
  };
}

function buildDetailFromRoadmapSession(session) {
  return {
    ...session,
    sourceLabel: "Selected session",
  };
}

function getActiveSessionDetail() {
  if (selectedHistoryItemKey) {
    const historyItem = findHistoryItemByKey(selectedHistoryItemKey);
    if (historyItem) {
      return buildDetailFromHistoryItem(historyItem);
    }
  }

  const selectedSession =
    findRoadmapSessionByKey(activeRoadmap, selectedRoadmapSessionKey)
    || findNextRoadmapSession(activeRoadmap)
    || findFirstRoadmapSession(activeRoadmap);

  return selectedSession ? buildDetailFromRoadmapSession(selectedSession) : null;
}

function setActiveView(viewName) {
  const nextView = String(viewName || "tutor").trim() || "tutor";
  focusTabs.forEach((tab) => {
    const isActive = tab.dataset.viewTarget === nextView;
    tab.classList.toggle("is-active", isActive);
    tab.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
  focusViews.forEach((view) => {
    view.classList.toggle("is-active", view.dataset.view === nextView);
  });
  window.localStorage.setItem(activeViewStorageKey, nextView);
}

function getHistory() {
  const sid = getSessionId();
  try {
    return JSON.parse(window.localStorage.getItem(historyStorageKeyPrefix + sid)) || [];
  } catch {
    return [];
  }
}

function saveHistoryItem(role, body) {
  const sid = getSessionId();
  const hist = getHistory();
  hist.push({ role, body });
  window.localStorage.setItem(historyStorageKeyPrefix + sid, JSON.stringify(hist));
}

function clearSessionState() {
  window.localStorage.removeItem(sessionStorageKey);
  messages.innerHTML = `
    <div class="empty-state">
      Let's begin your Journey!
    </div>
  `;
}

function restoreSession() {
  const hist = getHistory();
  if (hist.length > 0) {
    messages.innerHTML = "";
    for (const msg of hist) {
      appendMessage(msg.role, msg.body, true);
    }
  }
}

function getSessionId() {
  let sessionId = window.localStorage.getItem(sessionStorageKey);
  if (!sessionId) {
    sessionId = window.crypto.randomUUID();
    window.localStorage.setItem(sessionStorageKey, sessionId);
  }
  return sessionId;
}

function sanitizeUsername(value) {
  return value.trim().toLowerCase().slice(0, 120);
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function getUsername() {
  return sanitizeUsername(window.localStorage.getItem(usernameStorageKey) || "");
}

function setUsername(value) {
  const username = sanitizeUsername(value);
  window.localStorage.setItem(usernameStorageKey, username);
  return username;
}

function getIdToken() {
  return window.localStorage.getItem(idTokenStorageKey) || "";
}

function setIdToken(value) {
  if (value) {
    window.localStorage.setItem(idTokenStorageKey, value);
  } else {
    window.localStorage.removeItem(idTokenStorageKey);
  }
}

function openUsernameModal(prefill = true) {
  usernameModal.classList.add("open");
  usernameModal.setAttribute("aria-hidden", "false");
  usernameInput.value = prefill ? getUsername() : "";
  usernameInput.setCustomValidity("");
  usernameInput.focus();
  usernameInput.select();
}

function closeUsernameModal() {
  usernameModal.classList.remove("open");
  usernameModal.setAttribute("aria-hidden", "true");
}

function updateAuthPill(label, subtle = false) {
  authPill.textContent = label;
  authPill.classList.toggle("subtle", subtle);
}

async function refreshLearnerState() {
  const username = getUsername();
  if (!username) {
    latestLearnerState = null;
    stateTitle.textContent = "New learner";
    stateSummary.textContent = "Sign in to begin.";
    refreshOverview();
    return;
  }

  try {
    const response = await fetch(`/api/learner-state?userId=${encodeURIComponent(username)}`, {
      headers: buildAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || "Could not load learner state.");
    }
    latestLearnerState = data;

    const topic = data.current_topic || data.profile?.topic || "Personalized study plan";
    stateTitle.textContent = topic;

    const details = [];
    if (data.profile?.level) {
      details.push(`Level: ${data.profile.level}`);
    }
    if (data.profile?.available_time) {
      details.push(`Daily time: ${data.profile.available_time} minutes`);
    }
    if (data.completed_activities) {
      details.push(`Activities saved: ${data.completed_activities}`);
    }
    if (data.weak_topics?.length) {
      details.push(`Weak topics: ${data.weak_topics.join(", ")}`);
    }
    if (typeof data.mastery?.overall_score === "number") {
      details.push(`Mastery: ${Math.round(data.mastery.overall_score * 100)}%`);
    }
    if (data.roadmap_summary?.phase_count) {
      details.push(`Roadmap: ${data.roadmap_summary.mode} mode`);
    }
    details.push(data.recommended_next_action || "Take a diagnostic and generate your first roadmap.");
    stateSummary.textContent = details.join(" • ");
    refreshOverview();
  } catch (error) {
    latestLearnerState = null;
    stateTitle.textContent = "Learner state unavailable";
    stateSummary.textContent = error.message;
    refreshOverview();
  }
}

function renderMasteryBoard(mastery) {
  const overall = typeof mastery?.overall_score === "number" ? mastery.overall_score : 0;
  masteryScore.textContent = `${Math.round(overall * 100)}%`;

  const sessions = getPreviousSessions();
  const controls = `
    <div class="inline-actions">
      <button class="ghost-button history-toggle" type="button" data-history-toggle="true">
        Previous sessions
      </button>
      <button class="ghost-button" type="button" data-history-delete-all="true"${sessions.length ? "" : " disabled"}>
        Delete all
      </button>
    </div>
  `;

  if (!sessions.length) {
    masteryTopics.innerHTML = `
      ${controls}
      <p class="mastery-empty">No previous sessions yet.</p>
    `;
    return;
  }

  const selectedHistoryItem = findHistoryItemByKey(selectedHistoryItemKey) || sessions[0];
  if (!selectedHistoryItemKey) {
    selectedHistoryItemKey = "";
  }

  masteryTopics.innerHTML = `
    ${controls}
    ${previousSessionsExpanded ? `
      <div class="history-list">
        ${sessions
          .map((item) => `
            <article class="history-item${selectedHistoryItem?.key === item.key ? " is-selected" : ""}">
              <button
                class="history-item-main"
                type="button"
                data-history-item="${escapeHtml(item.key)}"
              >
                <strong>${escapeHtml(item.topic)}</strong>
                <span>${escapeHtml(formatRelativeDays(item.created_at))}</span>
              </button>
              <button
                class="mini-button"
                type="button"
                data-history-delete="${escapeHtml(item.key)}"
              >
                Delete
              </button>
            </article>
          `)
          .join("")}
      </div>
    ` : ""}
  `;
}

async function deleteHistoryItem(itemKey) {
  const username = ensureIdentity();
  if (!username) {
    return;
  }

  const historyItem = findHistoryItemByKey(itemKey);
  if (!historyItem?.record_id) {
    roadmapStatus.textContent = "Could not find that previous session.";
    return;
  }

  roadmapStatus.textContent = "Deleting previous session...";
  const response = await fetch("/api/history/delete", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
    },
    body: JSON.stringify({
      userId: username,
      idToken: getIdToken(),
      recordId: historyItem.record_id,
    }),
  });
  const data = await response.json();
  if (!response.ok || data.status !== "success") {
    throw new Error(data.error || data.message || "Could not delete previous session.");
  }

  if (selectedHistoryItemKey === itemKey) {
    selectedHistoryItemKey = "";
  }
  await refreshLearnerState();
  await refreshMasteryBoard();
  renderRoadmap({ roadmap: activeRoadmap, summary: activeRoadmapSummary });
  roadmapStatus.textContent = data.message || "Previous session deleted.";
}

async function deleteAllHistoryItems() {
  const username = ensureIdentity();
  if (!username) {
    return;
  }

  roadmapStatus.textContent = "Deleting previous sessions...";
  const response = await fetch("/api/history/delete-all", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
    },
    body: JSON.stringify({
      userId: username,
      idToken: getIdToken(),
    }),
  });
  const data = await response.json();
  if (!response.ok || data.status !== "success") {
    throw new Error(data.error || data.message || "Could not delete previous sessions.");
  }

  selectedHistoryItemKey = "";
  previousSessionsExpanded = false;
  await refreshLearnerState();
  await refreshMasteryBoard();
  renderRoadmap({ roadmap: activeRoadmap, summary: activeRoadmapSummary });
  roadmapStatus.textContent = data.message || "All previous sessions deleted.";
}

async function refreshMasteryBoard() {
  const username = getUsername();
  if (!username) {
    renderMasteryBoard({ topics: [], overall_score: 0 });
    return;
  }

  try {
    const response = await fetch(`/api/mastery?userId=${encodeURIComponent(username)}`, {
      headers: buildAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || "Could not load mastery.");
    }
    renderMasteryBoard(data);
  } catch (error) {
    masteryTopics.innerHTML = `<p class="mastery-empty">${error.message}</p>`;
  }
}

masteryTopics.addEventListener("click", async (event) => {
  const toggleButton = event.target.closest("[data-history-toggle]");
  if (toggleButton) {
    previousSessionsExpanded = !previousSessionsExpanded;
    renderMasteryBoard(latestLearnerState?.mastery || { overall_score: 0, topics: [] });
    return;
  }

  const deleteAllButton = event.target.closest("[data-history-delete-all]");
  if (deleteAllButton) {
    try {
      await deleteAllHistoryItems();
    } catch (error) {
      roadmapStatus.textContent = error.message;
    }
    return;
  }

  const deleteButton = event.target.closest("[data-history-delete]");
  if (deleteButton) {
    try {
      await deleteHistoryItem(deleteButton.dataset.historyDelete || "");
    } catch (error) {
      roadmapStatus.textContent = error.message;
    }
    return;
  }

  const historyButton = event.target.closest("[data-history-item]");
  if (!historyButton) {
    return;
  }

  selectedHistoryItemKey = historyButton.dataset.historyItem || "";
  const historyItem = findHistoryItemByKey(selectedHistoryItemKey);
  const matchingRoadmapSession = findRoadmapSessionByTopic(activeRoadmap, historyItem?.topic || "");
  selectedRoadmapSessionKey = matchingRoadmapSession?.key || selectedRoadmapSessionKey;

  renderMasteryBoard(latestLearnerState?.mastery || { overall_score: 0, topics: [] });
  renderRoadmap({ roadmap: activeRoadmap, summary: activeRoadmapSummary });
  roadmapStatus.textContent = "Previous session loaded below.";
  roadmapSessionDetail.scrollIntoView({ behavior: "smooth", block: "nearest" });
});

function buildRoadmapSessionKey(phaseId, sessionId) {
  return `${phaseId || "phase"}::${sessionId || "session"}`;
}

function normalizeRoadmapSession(phase, session) {
  return {
    ...session,
    key: buildRoadmapSessionKey(phase.phase_id, session.session_id),
    phaseId: phase.phase_id,
    phaseTitle: phase.title,
    phaseGoal: phase.goal,
    phaseOutcome: phase.expected_outcome,
  };
}

function findRoadmapSessionByKey(roadmap, key) {
  if (!roadmap || !key) {
    return null;
  }

  for (const phase of roadmap.phases || []) {
    for (const session of phase.sessions || []) {
      const normalized = normalizeRoadmapSession(phase, session);
      if (normalized.key === key) {
        return normalized;
      }
    }
  }
  return null;
}

function findFirstRoadmapSession(roadmap) {
  for (const phase of roadmap?.phases || []) {
    const firstSession = (phase.sessions || [])[0];
    if (firstSession) {
      return normalizeRoadmapSession(phase, firstSession);
    }
  }
  return null;
}

function findRoadmapSessionByTopic(roadmap, topic) {
  const normalizedTopic = String(topic || "").trim().toLowerCase();
  if (!roadmap || !normalizedTopic) {
    return null;
  }

  for (const phase of roadmap.phases || []) {
    for (const session of phase.sessions || []) {
      const haystack = `${session.title || ""} ${session.focus || ""} ${phase.goal || ""}`.toLowerCase();
      if (haystack.includes(normalizedTopic)) {
        return normalizeRoadmapSession(phase, session);
      }
    }
  }

  return null;
}

function findNextRoadmapSession(roadmap) {
  for (const phase of roadmap?.phases || []) {
    for (const session of phase.sessions || []) {
      if (session.status !== "completed") {
        return normalizeRoadmapSession(phase, session);
      }
    }
  }
  return null;
}

function buildStudyPrompt(session) {
  const bits = [
    `Teach me this roadmap session now: ${session.title}.`,
    session.focus ? `Topic: ${session.focus}.` : "",
    session.phaseGoal ? `Phase goal: ${session.phaseGoal}.` : "",
    session.duration_minutes ? `Keep it within ${session.duration_minutes} minutes.` : "",
    "Give me a short explanation, one example, and one small exercise.",
  ].filter(Boolean);
  return bits.join(" ");
}

function openRoadmapSession(session) {
  const prompt = buildStudyPrompt(session);
  setActiveView("tutor");
  promptInput.value = prompt;
  roadmapStatus.textContent = `Opened ${session.title} in Tutor.`;
  promptInput.focus();
  promptInput.setSelectionRange(prompt.length, prompt.length);
  promptInput.scrollIntoView({ behavior: "smooth", block: "center" });
}

function previewRoadmapSessionByKey(sessionKey, options = {}) {
  const session = findRoadmapSessionByKey(activeRoadmap, sessionKey);
  if (!session) {
    return;
  }

  selectedHistoryItemKey = "";
  selectedRoadmapSessionKey = session.key || "";
  renderRoadmap({ roadmap: activeRoadmap, summary: activeRoadmapSummary });

  if (options.statusMessage) {
    roadmapStatus.textContent = options.statusMessage;
  }

  if (options.scrollToDetail !== false) {
    roadmapSessionDetail.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

async function updateRoadmapSessionStatus(button) {
  roadmapStatus.textContent = `Marking session ${button.dataset.status}...`;
  try {
    const response = await fetch("/api/roadmap/session/update", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: getUsername(),
        idToken: getIdToken(),
        phaseId: button.dataset.phaseId,
        sessionId: button.dataset.sessionId,
        status: button.dataset.status,
      }),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not update roadmap session.");
    }
    renderRoadmap(data);
    roadmapStatus.textContent =
      button.dataset.status === "completed"
        ? "Session marked complete. The roadmap was updated."
        : "Session marked missed. The roadmap was updated.";
    roadmapStatus.scrollIntoView({ behavior: "smooth", block: "nearest" });
    await refreshLearnerState();
    await refreshMasteryBoard();
    await refreshInsights();
  } catch (error) {
    roadmapStatus.textContent = error.message;
  }
}

function renderRoadmapSessionDetail(session) {
  if (!session) {
    roadmapSessionDetail.innerHTML = "Select a session to see what to study next.";
    return;
  }

  const durationText = session.duration_minutes ? `${session.duration_minutes} min` : "";
  const dueText = session.due_date ? (String(session.due_date).includes("ago") || session.due_date === "today" ? session.due_date : `Due ${session.due_date}`) : "";
  const focusText = session.focus || session.phaseGoal || "Study focus";
  const explanation = session.phaseOutcome
    ? session.phaseOutcome
    : `Use this session to build confidence in ${focusText.toLowerCase()}.`;

  roadmapSessionDetail.innerHTML = `
    <div class="roadmap-detail-head">
      <div>
        <p class="section-label">${escapeHtml(session.sourceLabel || "Selected session")}</p>
        <h5>${escapeHtml(session.title)}</h5>
      </div>
      ${(durationText || dueText) ? `
        <div class="roadmap-detail-kicker">
          ${durationText ? `${escapeHtml(durationText)}<br />` : ""}
          ${dueText ? escapeHtml(dueText) : ""}
        </div>
      ` : ""}
    </div>
    <p class="roadmap-detail-copy">${escapeHtml(explanation)}</p>
    <div class="roadmap-detail-meta">
      <span class="status-pill subtle">${escapeHtml(focusText)}</span>
      <span class="status-pill">${escapeHtml(session.phaseTitle || "Roadmap step")}</span>
      <span class="status-pill">${escapeHtml(session.status || "planned")}</span>
    </div>
    <div class="roadmap-detail-steps">
      <strong>What to do</strong>
      <p>Open Tutor, learn this topic, do one short exercise, then come back here and mark the session complete.</p>
    </div>
    <div class="inline-actions">
      <button
        class="primary-button"
        type="button"
        data-open-session="true"
        data-session-key="${escapeHtml(session.key || "")}"
        data-session-title="${escapeHtml(session.title)}"
        data-session-focus="${escapeHtml(session.focus || "")}"
        data-session-duration="${escapeHtml(session.duration_minutes || "")}"
        data-phase-title="${escapeHtml(session.phaseTitle || "")}"
        data-phase-goal="${escapeHtml(session.phaseGoal || "")}"
      >
        Open in Tutor
      </button>
    </div>
  `;
}

function renderRoadmap(roadmapResult) {
  const roadmap = roadmapResult?.roadmap || null;
  const summary = roadmapResult?.summary || null;
  activeRoadmap = roadmap;
  activeRoadmapSummary = summary;

  if (!roadmap || !summary) {
    roadmapMode.textContent = "No roadmap yet";
    roadmapSummary.textContent = "Roadmap will appear here.";
    renderRoadmapSessionDetail(getActiveSessionDetail());
    roadmapBoard.innerHTML = `<p class="mastery-empty">No roadmap yet.</p>`;
    return;
  }

  const nextRoadmapSession = findNextRoadmapSession(roadmap);
  const selectedSession =
    findRoadmapSessionByKey(roadmap, selectedRoadmapSessionKey)
    || nextRoadmapSession
    || findFirstRoadmapSession(roadmap);

  selectedRoadmapSessionKey = selectedSession?.key || "";
  roadmapMode.textContent = `${summary.mode} mode`;
  const progressText =
    `${summary.completed_sessions}/${summary.total_sessions} sessions completed • ` +
    `${Math.round((summary.completion_rate || 0) * 100)}% complete`;
  if (nextRoadmapSession) {
    roadmapSummary.innerHTML = `
      <div class="roadmap-next-action">
        <div>
          <strong>Next up</strong>
          <p>${escapeHtml(nextRoadmapSession.title)} • Open the brief, then continue in Tutor.</p>
        </div>
        <button
          class="ghost-button roadmap-open-button"
          type="button"
          data-preview-session="true"
          data-session-key="${escapeHtml(nextRoadmapSession.key)}"
          data-session-title="${escapeHtml(nextRoadmapSession.title)}"
          data-session-focus="${escapeHtml(nextRoadmapSession.focus || "")}"
          data-session-duration="${escapeHtml(nextRoadmapSession.duration_minutes || "")}"
          data-phase-title="${escapeHtml(nextRoadmapSession.phaseTitle || "")}"
          data-phase-goal="${escapeHtml(nextRoadmapSession.phaseGoal || "")}"
        >
          Open brief
        </button>
      </div>
      <p class="roadmap-progress-copy">${escapeHtml(progressText)}</p>
    `;
  } else {
    roadmapSummary.innerHTML = `<p class="roadmap-progress-copy">${escapeHtml(progressText)} • All sessions are done.</p>`;
  }

  roadmapBoard.innerHTML = roadmap.phases
    .map((phase) => {
      const sessionsMarkup = (phase.sessions || [])
        .map(
          (session) => `
            <article
              class="roadmap-session${buildRoadmapSessionKey(phase.phase_id, session.session_id) === selectedRoadmapSessionKey ? " is-selected" : ""}"
              tabindex="0"
              role="button"
              aria-label="Open ${escapeHtml(session.title)} brief"
              data-preview-session="true"
              data-session-key="${escapeHtml(buildRoadmapSessionKey(phase.phase_id, session.session_id))}"
            >
              <div>
                <strong>${session.title}</strong>
                <p>${session.focus} • ${session.duration_minutes} min • due ${session.due_date}</p>
                <p>Status: ${session.status}</p>
              </div>
              <div class="roadmap-session-actions">
                <button
                  class="mini-button"
                  type="button"
                  data-preview-session="true"
                  data-session-key="${escapeHtml(buildRoadmapSessionKey(phase.phase_id, session.session_id))}"
                >
                  View brief
                </button>
                <button class="mini-button" type="button" data-phase-id="${phase.phase_id}" data-session-id="${session.session_id}" data-status="completed">Mark completed</button>
                <button class="mini-button" type="button" data-phase-id="${phase.phase_id}" data-session-id="${session.session_id}" data-status="missed">Mark missed</button>
              </div>
            </article>
          `
        )
        .join("");

      return `
        <section class="roadmap-phase">
          <div class="roadmap-phase-header">
            <div>
              <p class="section-label">${phase.title}</p>
              <h5>${phase.goal}</h5>
            </div>
            <div class="roadmap-kicker">
              checkpoint: ${phase.checkpoint_type}<br />
              due ${phase.checkpoint_due_date}
            </div>
          </div>
          <p>${phase.expected_outcome}</p>
          <div class="roadmap-session-list">${sessionsMarkup}</div>
        </section>
      `;
    })
    .join("");

  renderRoadmapSessionDetail(getActiveSessionDetail());
}

async function refreshRoadmap() {
  const username = getUsername();
  if (!username) {
    renderRoadmap(null);
    return;
  }

  try {
    const response = await fetch(`/api/roadmap?userId=${encodeURIComponent(username)}`, {
      headers: buildAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      renderRoadmap(null);
      return;
    }
    renderRoadmap(data);
  } catch {
    renderRoadmap(null);
  }
}

function updateMaterialsSelectionSummary() {
  if (!selectedMaterialIds.size) {
    materialsSelectionSummary.textContent = "Choose 1 source to use.";
    return;
  }
  materialsSelectionSummary.textContent = `${selectedMaterialIds.size} source${selectedMaterialIds.size === 1 ? "" : "s"} ready.`;
}

function formatMaterialTimeLabel(value) {
  if (!value) {
    return "recently";
  }
  const then = new Date(value);
  if (Number.isNaN(then.getTime())) {
    return "recently";
  }
  const diffMs = Date.now() - then.getTime();
  const diffDays = Math.max(0, Math.round(diffMs / 86400000));
  if (diffDays <= 0) {
    return "today";
  }
  if (diffDays === 1) {
    return "1 day ago";
  }
  return `${diffDays} days ago`;
}

function renderMaterials(materials = []) {
  latestMaterials = materials;
  if (!materials.length) {
    materialsLibrary.innerHTML = `<p class="mastery-empty">Nothing uploaded yet.</p>`;
    updateMaterialsSelectionSummary();
    refreshOverview();
    return;
  }

  const validIds = new Set(materials.map((material) => material.material_id));
  selectedMaterialIds = new Set([...selectedMaterialIds].filter((id) => validIds.has(id)));

  const latestMaterial = materials[0] || null;
  const previousMaterials = materials.slice(1);
  const renderMaterialCard = (material) => {
      const checked = selectedMaterialIds.has(material.material_id) ? "checked" : "";
      const meta = material.kind === "image"
        ? `${material.metadata?.width || "?"}x${material.metadata?.height || "?"}`
        : material.kind;
      return `
        <article class="material-card">
          <header>
            <div>
              <p class="section-label">${material.kind}</p>
              <h5>${material.name}</h5>
            </div>
            <div class="material-card-actions">
              <input class="material-select" type="checkbox" data-material-id="${material.material_id}" ${checked} />
              <button class="mini-button" type="button" data-delete-material="${material.material_id}">Delete</button>
            </div>
          </header>
          <p>${material.summary}</p>
          <p>${meta} • added ${formatMaterialTimeLabel(material.created_at)}</p>
        </article>
      `;
    };

  materialsLibrary.innerHTML = `
    ${latestMaterial ? `
      <section class="materials-group">
        <div class="materials-group-head">
          <p class="section-label">Current resource</p>
        </div>
        ${renderMaterialCard(latestMaterial)}
      </section>
    ` : ""}
    ${previousMaterials.length ? `
      <section class="materials-group">
        <button class="ghost-button" type="button" data-toggle-previous-resources="true">
          Previous resources
        </button>
        ${previousResourcesExpanded ? `
          <div class="materials-history">
            ${previousMaterials.map(renderMaterialCard).join("")}
          </div>
        ` : ""}
      </section>
    ` : ""}
  `;
  updateMaterialsSelectionSummary();
  refreshOverview();
}

async function deleteMaterial(materialId) {
  const username = ensureIdentity();
  if (!username) {
    return;
  }

  const previousMaterialsSnapshot = [...latestMaterials];
  latestMaterials = latestMaterials.filter((material) => material.material_id !== materialId);
  selectedMaterialIds.delete(materialId);
  renderMaterials(latestMaterials);
  materialsStatus.textContent = "Deleting resource...";
  try {
    const response = await fetch("/api/materials/delete", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: username,
        idToken: getIdToken(),
        materialId,
      }),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not delete material.");
    }
    materialsStatus.textContent = "Resource deleted.";
    await refreshMaterials();
    await refreshInsights();
  } catch (error) {
    latestMaterials = previousMaterialsSnapshot;
    renderMaterials(latestMaterials);
    materialsStatus.textContent = error.message;
  }
}

async function deleteAllMaterials() {
  const username = ensureIdentity();
  if (!username) {
    return;
  }

  const previousMaterialsSnapshot = [...latestMaterials];
  latestMaterials = [];
  selectedMaterialIds.clear();
  previousResourcesExpanded = false;
  renderMaterials([]);
  materialsStatus.textContent = "Deleting all resources...";
  try {
    const response = await fetch("/api/materials/delete-all", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: username,
        idToken: getIdToken(),
      }),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not delete all materials.");
    }
    materialsStatus.textContent = "All resources deleted.";
    await refreshMaterials();
    await refreshInsights();
  } catch (error) {
    latestMaterials = previousMaterialsSnapshot;
    renderMaterials(latestMaterials);
    materialsStatus.textContent = error.message;
  }
}

async function refreshMaterials() {
  const username = getUsername();
  if (!username) {
    renderMaterials([]);
    return;
  }

  try {
    const response = await fetch(`/api/materials?userId=${encodeURIComponent(username)}`, {
      headers: buildAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || "Could not load materials.");
    }
    renderMaterials(data.materials || []);
  } catch (error) {
    materialsLibrary.innerHTML = `<p class="mastery-empty">${error.message}</p>`;
  }
}

function renderEvaluationSnapshot(snapshot) {
  if (!snapshot) {
    evaluationBoard.innerHTML = `<p class="mastery-empty">No evaluation yet.</p>`;
    return;
  }
  evaluationBoard.innerHTML = `
    <article class="material-card">
      <header>
        <div>
          <p class="section-label">Coverage</p>
          <h5>System evaluation</h5>
        </div>
      </header>
      <p>Assessments: ${snapshot.coverage?.assessment_count || 0}</p>
      <p>Progress events: ${snapshot.coverage?.progress_events || 0}</p>
      <p>Roadmap present: ${snapshot.coverage?.roadmap_present ? "yes" : "no"}</p>
      <p>Grounding available: ${snapshot.coverage?.grounding_available ? "yes" : "no"}</p>
      <p>Warnings: ${(snapshot.warnings || []).join(", ") || "none"}</p>
    </article>
  `;
}

function renderInterventionPlan(plan) {
  latestInterventionPlan = plan;
  if (!plan) {
    interventionRisk.textContent = "Unknown";
    interventionSummary.textContent = "Refresh to load insights.";
    refreshOverview();
    return;
  }
  interventionRisk.textContent = `${plan.risk_level} risk`;
  interventionSummary.textContent = `${plan.summary} Recommended: ${(plan.recommended_actions || []).slice(0, 2).join(" ")}`;
  refreshOverview();
}

function renderWeeklyReport(report) {
  latestWeeklyReport = report || null;
  if (!report) {
    reportBoard.innerHTML = `<p class="mastery-empty">No report yet.</p>`;
    return;
  }
  reportBoard.innerHTML = `
    <article class="material-card">
      <header>
        <div>
          <p class="section-label">Weekly report</p>
          <h5>${escapeHtml(report.title)}</h5>
        </div>
      </header>
      <p>${escapeHtml(report.note_text).replace(/\n/g, "<br />")}</p>
      <div class="inline-actions">
        <button id="save-report-docs-button" class="ghost-button" type="button">Save to Google Docs</button>
      </div>
      <p id="report-save-status" class="state-summary">Save this report to Google Docs when you are ready.</p>
    </article>
  `;
}

function renderGoogleDocsAuthMessage(result) {
  const authUrl = String(result?.authorization_url || "").trim();
  if (!authUrl) {
    return "Google Docs sign-in is needed before saving.";
  }
  return `
    Google sign-in is needed before saving.<br />
    Open this link in Chrome or Safari:<br />
    <a href="${escapeHtml(authUrl)}" target="_blank" rel="noreferrer">${escapeHtml(authUrl)}</a>
  `;
}

async function refreshInsights() {
  const username = getUsername();
  if (!username) {
    renderInterventionPlan(null);
    renderEvaluationSnapshot(null);
    return;
  }

  try {
    const [interventionResponse, evaluationResponse] = await Promise.all([
      fetch(`/api/intervention?userId=${encodeURIComponent(username)}`, { headers: buildAuthHeaders() }),
      fetch(`/api/evaluation?userId=${encodeURIComponent(username)}`, { headers: buildAuthHeaders() }),
    ]);
    const intervention = await interventionResponse.json();
    const evaluation = await evaluationResponse.json();
    if (interventionResponse.ok && intervention.status === "success") {
      renderInterventionPlan(intervention);
    }
    if (evaluationResponse.ok && evaluation.status === "success") {
      renderEvaluationSnapshot(evaluation);
    }
  } catch (error) {
    interventionSummary.textContent = error.message;
  }
}

function refreshOverview() {
  const masteryScoreValue = typeof latestLearnerState?.mastery?.overall_score === "number"
    ? Math.round(latestLearnerState.mastery.overall_score * 100)
    : 0;
  overviewMastery.textContent = `${masteryScoreValue}%`;
  overviewMasteryCaption.textContent = latestLearnerState?.mastery?.overall_label
    ? `Current level: ${latestLearnerState.mastery.overall_label}`
    : "Waiting for first assessment.";

  const roadmapSummary = latestLearnerState?.roadmap_summary;
  if (roadmapSummary?.phase_count) {
    overviewRoadmap.textContent = `${roadmapSummary.mode}`;
    overviewRoadmapCaption.textContent = `${roadmapSummary.completed_sessions}/${roadmapSummary.total_sessions} sessions complete`;
  } else {
    overviewRoadmap.textContent = "No plan";
    overviewRoadmapCaption.textContent = "Generate a roadmap to activate pacing.";
  }

  overviewMaterials.textContent = `${latestMaterials.length}`;
  overviewMaterialsCaption.textContent = latestMaterials.length
    ? `${selectedMaterialIds.size} selected for grounding`
    : "No materials yet.";

  overviewRisk.textContent = latestInterventionPlan?.risk_level || "Unknown";
  overviewRiskCaption.textContent = latestInterventionPlan?.triggers?.length
    ? latestInterventionPlan.triggers.join(" • ")
    : "No insight yet.";

  overviewBlurb.textContent = latestLearnerState?.recommended_next_action
    || "Learn, plan, and review in one place.";
}

function renderSystemStatus(status) {
  if (!status) {
    systemStackTitle.textContent = "Unavailable";
    systemStackSummary.textContent = "Could not load status.";
    systemReadinessBoard.innerHTML = `<p class="mastery-empty">No system status yet.</p>`;
    return;
  }

  systemStackTitle.textContent = `${status.stack?.agent_runtime || "Runtime"} + ${status.stack?.model_routing || "Models"}`;
  systemStackSummary.textContent =
    `Database mode: ${status.stack?.database_mode || "unknown"} • ` +
    `Frontend: ${status.stack?.frontend || "unknown"}`;

  const readinessRows = Object.entries(status.readiness || {})
    .map(([key, value]) => `<p><strong>${key.replace(/_/g, " ")}:</strong> ${value ? "ready" : "not ready"}</p>`)
    .join("");
  const metricRows = Object.entries(status.metrics || {})
    .map(([key, value]) => `<p><strong>${key.replace(/_/g, " ")}:</strong> ${value}</p>`)
    .join("");
  const nextSteps = (status.recommended_next_steps || []).map((item) => `<p>- ${item}</p>`).join("");

  systemReadinessBoard.innerHTML = `
    <article class="material-card">
      <header>
        <div>
          <p class="section-label">Readiness</p>
          <h5>Google-native setup</h5>
        </div>
      </header>
      ${readinessRows}
    </article>
    <article class="material-card">
      <header>
        <div>
          <p class="section-label">Observability</p>
          <h5>App metrics</h5>
        </div>
      </header>
      ${metricRows}
    </article>
    <article class="material-card">
      <header>
        <div>
          <p class="section-label">Next steps</p>
          <h5>Architecture checklist</h5>
        </div>
      </header>
      ${nextSteps}
    </article>
  `;
}

async function refreshSystemStatus() {
  try {
    const response = await fetch("/api/system-status");
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || "Could not load system status.");
    }
    renderSystemStatus(data);
  } catch (error) {
    renderSystemStatus(null);
    systemStackSummary.textContent = error.message;
  }
}

function renderDemoKit(demoKit) {
  if (!demoKit) {
    demoPitchCopy.textContent = "Demo unavailable.";
    demoMetricsBoard.innerHTML = `<p class="mastery-empty">No demo metrics yet.</p>`;
    demoPersonasBoard.innerHTML = `<p class="mastery-empty">No demo personas yet.</p>`;
    demoScriptBoard.innerHTML = `<p class="mastery-empty">No demo script yet.</p>`;
    return;
  }

  demoPitchTitle.textContent = "Judge pitch";
  demoPitchCopy.textContent = `${demoKit.pitch?.one_liner || ""} ${demoKit.pitch?.judge_angle || ""}`.trim();

  demoMetricsBoard.innerHTML = (demoKit.metrics || [])
    .map(
      (metric) => `
        <article class="material-card">
          <header>
            <div>
              <p class="section-label">Metric</p>
              <h5>${metric.label}</h5>
            </div>
          </header>
          <p><strong>${metric.value}</strong></p>
          <p>${metric.detail}</p>
        </article>
      `
    )
    .join("") || `<p class="mastery-empty">No demo metrics yet.</p>`;

  demoPersonasBoard.innerHTML = (demoKit.personas || [])
    .map(
      (persona) => `
        <article class="material-card">
          <header>
            <div>
              <p class="section-label">Persona</p>
              <h5>${persona.title}</h5>
            </div>
            <button class="mini-button" type="button" data-demo-persona="${persona.id}">Load</button>
          </header>
          <p>${persona.profile}</p>
          <p>Topic: ${persona.topic} • ${persona.daily_minutes} min/day • ${persona.deadline_days} day(s)</p>
          <p>${persona.demo_prompt}</p>
        </article>
      `
    )
    .join("") || `<p class="mastery-empty">No demo personas yet.</p>`;

  demoScriptBoard.innerHTML = (demoKit.demo_script || [])
    .map(
      (step) => `
        <article class="material-card">
          <header>
            <div>
              <p class="section-label">Step ${step.step}</p>
              <h5>${step.title}</h5>
            </div>
          </header>
          <p>${step.detail}</p>
        </article>
      `
    )
    .join("") || `<p class="mastery-empty">No demo script yet.</p>`;
}

async function refreshDemoKit() {
  const username = getUsername() || "frontend-user";
  try {
    const response = await fetch(`/api/demo-kit?userId=${encodeURIComponent(username)}`, {
      headers: buildAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || "Could not load demo kit.");
    }
    renderDemoKit(data);
  } catch (error) {
    renderDemoKit(null);
    demoPitchCopy.textContent = error.message;
  }
}

function applyDemoPersona(personaId) {
  const personaCards = Array.from(demoPersonasBoard.querySelectorAll("[data-demo-persona]"));
  const card = personaCards.find((button) => button.dataset.demoPersona === personaId);
  if (!card) {
    return;
  }
  const personaArticle = card.closest(".material-card");
  const title = personaArticle?.querySelector("h5")?.textContent || "";
  const personaMap = {
    beginner_student: {
      topic: "Python loops",
      goal: "Understand for and while loops well enough to solve basic exercises.",
      dailyMinutes: "45",
      deadlineDays: "14",
      prompt: "Teach me Python loops simply, then create a study roadmap.",
      level: "beginner",
    },
    exam_crammer: {
      topic: "Recursion",
      goal: "Recover fast and focus only on high-impact recursion concepts before the exam.",
      dailyMinutes: "30",
      deadlineDays: "7",
      prompt: "I missed several sessions. Give me a catch-up plan for recursion this week.",
      level: "beginner",
    },
    working_professional: {
      topic: "Binary search",
      goal: "Learn one interview algorithm deeply using notes and short evening sessions.",
      dailyMinutes: "25",
      deadlineDays: "10",
      prompt: "Use my uploaded notes to teach binary search and make a short roadmap.",
      level: "intermediate",
    },
  };
  const persona = personaMap[personaId];
  if (!persona) {
    return;
  }

  diagnosticTopicInput.value = persona.topic;
  diagnosticGoalInput.value = persona.goal;
  diagnosticTimeInput.value = persona.dailyMinutes;
  diagnosticLevelSelect.value = persona.level;
  roadmapTopicInput.value = persona.topic;
  roadmapGoalInput.value = persona.goal;
  roadmapTimeInput.value = persona.dailyMinutes;
  roadmapDeadlineInput.value = persona.deadlineDays;
  promptInput.value = persona.prompt;
  overviewBlurb.textContent = `Loaded demo persona: ${title}.`;
}

function speakText(text) {
  if (!("speechSynthesis" in window) || !text) {
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

function setupVoiceRecognition() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    voiceStatus.textContent = "Browser speech recognition is not supported here.";
    voiceInputButton.disabled = true;
    return;
  }

  speechRecognition = new Recognition();
  speechRecognition.lang = "en-US";
  speechRecognition.interimResults = false;
  speechRecognition.maxAlternatives = 1;

  speechRecognition.onstart = () => {
    isListening = true;
    voiceInputButton.textContent = "Listening...";
    voiceStatus.textContent = "Voice input is listening. Speak your study request.";
  };

  speechRecognition.onend = () => {
    isListening = false;
    voiceInputButton.textContent = "Start voice input";
    if (voiceStatus.textContent.startsWith("Voice input is listening")) {
      voiceStatus.textContent = "Voice mode idle.";
    }
  };

  speechRecognition.onresult = (event) => {
    const transcript = event.results?.[0]?.[0]?.transcript || "";
    if (!transcript) {
      return;
    }
    promptInput.value = transcript.trim();
    pendingInputMode = "voice";
    voiceStatus.textContent = "Voice transcript captured. Edit if needed, then send.";
    promptInput.focus();
  };

  speechRecognition.onerror = (event) => {
    voiceStatus.textContent = `Voice input error: ${event.error}`;
  };
}

function renderAssessmentQuestions(questions) {
  diagnosticQuestions.innerHTML = questions
    .map((question, index) => {
      const questionType = question.question_type || "multiple_choice";
      let inputMarkup = "";
      if (questionType === "multiple_choice") {
        inputMarkup = (question.options || [])
          .map(
            (option, optionIndex) => `
              <label class="option-row">
                <input type="radio" name="${question.question_id}" value="${String.fromCharCode(65 + optionIndex)}" />
                <span><strong>${String.fromCharCode(65 + optionIndex)}.</strong> ${option}</span>
              </label>
            `
          )
          .join("");
        inputMarkup = `<div class="options-list">${inputMarkup}</div>`;
      } else {
        inputMarkup = `
          <textarea
            class="assessment-text-answer"
            name="${question.question_id}"
            rows="${questionType === "essay" ? 6 : 3}"
            placeholder="${questionType === "essay" ? "Write your full answer here" : "Write a short answer here"}"
          ></textarea>
        `;
      }

      return `
        <section class="diagnostic-question">
          <h5>Question ${index + 1}</h5>
          <p class="section-label">${questionType.replace("_", " ")}</p>
          <p>${question.prompt}</p>
          ${inputMarkup}
        </section>
      `;
    })
    .join("");
}

function renderAssessmentResult(result) {
  const weakConcepts = result.weak_concepts?.length ? result.weak_concepts.join(", ") : "None";
  const questionCards = result.question_results
    .map(
      (item) => `
        <article class="result-card">
          <strong>${item.concept}</strong>
          <p>${item.is_correct ? "Strong answer" : `Needs review${item.correct_answer ? ` • expected: ${item.correct_answer}` : ""}`}</p>
          <p>${item.question_type ? `Type: ${item.question_type.replace("_", " ")}` : ""}</p>
          <p>${typeof item.score === "number" ? `Score: ${Math.round(item.score * 100)}%` : ""}</p>
          <p>${item.explanation}</p>
        </article>
      `
    )
    .join("");

  diagnosticResult.innerHTML = `
    <article class="result-card">
      <strong>Score: ${Math.round((result.score || 0) * 100)}%</strong>
      <p>${result.correct_count}/${result.question_count} strong responses</p>
      <p>Weak concepts: ${weakConcepts}</p>
      <p>${result.recommended_next_action}</p>
    </article>
    ${questionCards}
  `;
  diagnosticResult.classList.remove("hidden");
}

downloadAssessmentPdfButton.addEventListener("click", () => {
  if (!activeAssessment?.assessment_id) {
    assessmentStatus.textContent = "Create a mock test first.";
    return;
  }

  const blob = buildAssessmentPdfBlob(activeAssessment);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const topicSlug = String(activeAssessment.topic || "mock-test")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "mock-test";
  link.href = url;
  link.download = `${topicSlug}-mock-test.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  assessmentStatus.textContent = "Mock test PDF downloaded.";
});

function ensureIdentity() {
  const username = getUsername();
  if (username) {
    closeUsernameModal();
    return username;
  }
  openUsernameModal(false);
  return "";
}

function buildMessageBody(body) {
  const container = document.createElement("div");
  container.className = "message-body markdown-body";

  if (window.marked) {
    window.marked.setOptions({ breaks: true, gfm: true });
    container.innerHTML = window.marked.parse(body);

    if (window.hljs) {
      container.querySelectorAll("pre code").forEach((element) => {
        const langClass = Array.from(element.classList).find((c) => c && c.startsWith("language-"));
        if (langClass) {
          const lang = langClass.replace("language-", "");
          const label = document.createElement("div");
          label.className = "code-language";
          label.textContent = lang;

          const pre = element.parentElement;
          const block = document.createElement("div");
          block.className = "code-block";

          pre.parentNode.insertBefore(block, pre);
          block.appendChild(label);
          block.appendChild(pre);
        }
        window.hljs.highlightElement(element);
      });
    }

    container.querySelectorAll("a").forEach((anchor) => {
      anchor.target = "_blank";
      anchor.rel = "noreferrer";
      anchor.className = "message-link";
    });

    container.querySelectorAll("pre").forEach((pre) => {
      const raw = String(pre.textContent || "").trim();
      if (!/^https:\/\/accounts\.google\.com\/o\/oauth2\/auth\?/.test(raw)) {
        return;
      }
      const wrapper = document.createElement("p");
      const anchor = document.createElement("a");
      anchor.href = raw;
      anchor.target = "_blank";
      anchor.rel = "noreferrer";
      anchor.className = "message-link";
      anchor.textContent = "Open Google Sign-In";
      wrapper.appendChild(anchor);
      pre.replaceWith(wrapper);
    });
  } else {
    const p = document.createElement("p");
    p.textContent = body;
    container.appendChild(p);
  }

  return container;
}

function appendMessage(role, body, skipSave = false) {
  const emptyState = messages.querySelector(".empty-state");
  if (emptyState) {
    emptyState.remove();
  }

  const article = document.createElement("article");
  article.className = `message ${role}`;

  const roleLabel = document.createElement("p");
  roleLabel.className = "message-role";
  roleLabel.textContent = role === "user" ? getUsername() || "You" : "ARKAI";

  article.appendChild(roleLabel);
  article.appendChild(buildMessageBody(body));
  messages.appendChild(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });

  if (role === "agent") {
    lastAgentReply = body;
    if (voiceAutospeak.checked) {
      speakText(body.replace(/[#*_`>-]/g, " "));
    }
  }

  if (!skipSave) {
    saveHistoryItem(role, body);
  }
}

function buildAuthHeaders() {
  const headers = {};
  const idToken = getIdToken();
  if (idToken) {
    headers.Authorization = `Bearer ${idToken}`;
  }
  return headers;
}

async function bootstrapAuth() {
  try {
    const response = await fetch("/api/config");
    const config = await response.json();
    authMode = config.authMode || "email_fallback";

    if (!config.firebase) {
      updateAuthPill("Email fallback", true);
      googleSigninButton.disabled = true;
      googleSigninButton.textContent = "Firebase Auth not configured";
      authHelper.textContent =
        "Add Firebase web config env vars to enable Google Sign-In. The Gmail fallback still works locally.";
      return;
    }

    const app = initializeApp(config.firebase);
    firebaseAuthClient = getAuth(app);
    googleProvider = new GoogleAuthProvider();
    googleProvider.setCustomParameters({ prompt: "select_account" });

    onAuthStateChanged(firebaseAuthClient, async (user) => {
      if (!user) {
        setIdToken("");
        if (!getUsername()) {
          updateAuthPill("Auth not connected", true);
        }
        return;
      }

      const idToken = await user.getIdToken();
      setIdToken(idToken);
      if (user.email) {
        setUsername(user.email);
        closeUsernameModal();
        updateAuthPill(user.email, false);
      }
      await refreshLearnerState();
      await refreshMasteryBoard();
      await refreshRoadmap();
      await refreshMaterials();
      await refreshInsights();
    });

    if (getUsername()) {
      updateAuthPill(getUsername(), false);
    } else {
      updateAuthPill("Google Sign-In ready", true);
    }
  } catch (error) {
    updateAuthPill("Auth setup failed", true);
    authHelper.textContent = `Firebase Auth could not start: ${error.message}`;
  }
}

async function submitRoadmapRequest({ forceRebuild = false, revisionReason = "" } = {}) {
  const username = ensureIdentity();
  if (!username) {
    return;
  }

  const topic = roadmapTopicInput.value.trim() || diagnosticTopicInput.value.trim();
  if (!topic) {
    roadmapStatus.textContent = "Choose a roadmap topic first.";
    roadmapTopicInput.focus();
    return;
  }

  roadmapStatus.textContent = forceRebuild ? "Generating recovery roadmap..." : "Generating roadmap...";
  const response = await fetch("/api/roadmap/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
    },
    body: JSON.stringify({
      userId: username,
      idToken: getIdToken(),
      topic,
      goal: roadmapGoalInput.value.trim() || diagnosticGoalInput.value.trim(),
      availableTime: roadmapTimeInput.value ? Number(roadmapTimeInput.value) : (diagnosticTimeInput.value ? Number(diagnosticTimeInput.value) : null),
      deadlineDays: roadmapDeadlineInput.value ? Number(roadmapDeadlineInput.value) : 14,
      level: diagnosticLevelSelect.value,
      forceRebuild,
      revisionReason,
    }),
  });
  const data = await response.json();
  if (!response.ok || data.status !== "success") {
    throw new Error(data.error || data.message || "Could not generate roadmap.");
  }
    renderRoadmap(data);
    roadmapStatus.textContent = data.message || "Roadmap generated.";
    await refreshLearnerState();
    await refreshInsights();
  }

async function readFileAsDataUrl(file) {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read file."));
    reader.readAsDataURL(file);
  });
}

async function readFileAsText(file) {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read file."));
    reader.readAsText(file);
  });
}

seedButton.addEventListener("click", () => {
  setActiveView("tutor");
  promptInput.value = "Teach me loops with one example and one exercise.";
  diagnosticTopicInput.value = "Python loops";
  diagnosticGoalInput.value = "Build a strong foundation";
  diagnosticTimeInput.value = "45";
  roadmapTopicInput.value = "Python loops";
  roadmapGoalInput.value = "Be comfortable solving basic loop problems";
  roadmapTimeInput.value = "45";
  roadmapDeadlineInput.value = "14";
  materialQueryInput.value = "Summarize the selected materials for me.";
});

if (newSessionButton) {
  newSessionButton.addEventListener("click", () => {
    clearSessionState();
  });
}

changeGmailButton.addEventListener("click", async () => {
  if (firebaseAuthClient && firebaseAuthClient.currentUser) {
    await signOut(firebaseAuthClient);
  }
  setIdToken("");
  window.localStorage.removeItem(usernameStorageKey);
  updateAuthPill("Auth not connected", true);
  openUsernameModal(false);
  await refreshLearnerState();
  await refreshMasteryBoard();
  await refreshRoadmap();
  await refreshMaterials();
  await refreshInsights();
});

promptInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey) {
    return;
  }

  event.preventDefault();
  submitButton.click();
});

googleSigninButton.addEventListener("click", async () => {
  if (!firebaseAuthClient || !googleProvider) {
    openUsernameModal(true);
    return;
  }

  try {
    const result = await signInWithPopup(firebaseAuthClient, googleProvider);
    const idToken = await result.user.getIdToken();
    setIdToken(idToken);
    setUsername(result.user.email || "");
    updateAuthPill(result.user.email || "Signed in", false);
    closeUsernameModal();
    await refreshLearnerState();
    await refreshMasteryBoard();
    await refreshRoadmap();
    await refreshMaterials();
    await refreshInsights();
    promptInput.focus();
  } catch (error) {
    authHelper.textContent = `Google Sign-In failed: ${error.message}`;
  }
});

usernameForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const username = sanitizeUsername(usernameInput.value);
  if (!isValidEmail(username)) {
    usernameInput.focus();
    usernameInput.setCustomValidity("Enter a valid Gmail address.");
    usernameInput.reportValidity();
    return;
  }

  if (!username.endsWith("@gmail.com")) {
    usernameInput.focus();
    usernameInput.setCustomValidity("Use a Gmail address ending in @gmail.com.");
    usernameInput.reportValidity();
    return;
  }

  usernameInput.setCustomValidity("");
  setUsername(username);
  setIdToken("");
  updateAuthPill(`${username} (fallback)`, true);
  closeUsernameModal();
  promptInput.focus();
  await refreshLearnerState();
  await refreshMasteryBoard();
  await refreshRoadmap();
  await refreshMaterials();
  await refreshInsights();
});

generateRoadmapButton.addEventListener("click", async () => {
  setActiveView("plan");
  try {
    await submitRoadmapRequest();
  } catch (error) {
    roadmapStatus.textContent = error.message;
  }
});

rebuildRoadmapButton.addEventListener("click", async () => {
  setActiveView("plan");
  try {
    await submitRoadmapRequest({ forceRebuild: true, revisionReason: "manual recovery rebuild" });
  } catch (error) {
    roadmapStatus.textContent = error.message;
  }
});

refreshInsightsButton.addEventListener("click", async () => {
  setActiveView("insights");
  await refreshInsights();
});

generateReportButton.addEventListener("click", async () => {
  setActiveView("insights");
  const username = ensureIdentity();
  if (!username) {
    return;
  }
  try {
    const response = await fetch("/api/report/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: username,
        idToken: getIdToken(),
      }),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not generate report.");
    }
    renderWeeklyReport(data);
    await refreshInsights();
  } catch (error) {
    reportBoard.innerHTML = `<p class="mastery-empty">${error.message}</p>`;
  }
});

reportBoard.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement) || target.id !== "save-report-docs-button") {
    return;
  }

  const username = ensureIdentity();
  if (!username) {
    return;
  }

  if (!latestWeeklyReport) {
    renderWeeklyReport(null);
    return;
  }

  const statusNode = document.getElementById("report-save-status");
  if (statusNode) {
    statusNode.textContent = "Saving to Google Docs...";
  }
  target.setAttribute("disabled", "disabled");

  try {
    const response = await fetch("/api/report/save-google-doc", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: username,
        idToken: getIdToken(),
        title: latestWeeklyReport.title || "",
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || data.message || "Could not save report.");
    }

    if (data.status === "auth_required") {
      if (statusNode) {
        statusNode.innerHTML = renderGoogleDocsAuthMessage(data);
      }
      return;
    }

    if (data.status !== "success") {
      throw new Error(data.error || data.message || "Could not save report.");
    }

    if (statusNode) {
      statusNode.textContent = data.message || "Saved to Google Docs.";
    }
  } catch (error) {
    if (statusNode) {
      statusNode.textContent = error.message;
    }
  } finally {
    target.removeAttribute("disabled");
  }
});

refreshSystemButton.addEventListener("click", async () => {
  await refreshSystemStatus();
});

refreshDemoKitButton.addEventListener("click", async () => {
  await refreshDemoKit();
});

uploadMaterialButton.addEventListener("click", async () => {
  setActiveView("materials");
  const username = ensureIdentity();
  if (!username) {
    return;
  }

  const file = materialFileInput.files?.[0] || null;
  const pastedText = materialTextInput.value.trim();
  if (!file && !pastedText) {
    materialsStatus.textContent = "Add a file or paste notes first.";
    return;
  }

  uploadMaterialButton.disabled = true;
  materialsStatus.textContent = "Saving material...";
  try {
    const dataBase64 = file ? await readFileAsDataUrl(file) : "";
    const response = await fetch("/api/materials/upload", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: username,
        idToken: getIdToken(),
        name: file?.name || `pasted-notes-${Date.now()}.txt`,
        mimeType: file?.type || "text/plain",
        dataBase64,
        pastedText,
      }),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not upload material.");
    }
    materialsStatus.textContent = `${data.material.name} is ready.`;
    materialFileInput.value = "";
    materialTextInput.value = "";
    await refreshMaterials();
    await refreshInsights();
  } catch (error) {
    materialsStatus.textContent = error.message;
  } finally {
    uploadMaterialButton.disabled = false;
  }
});

askMaterialsButton.addEventListener("click", async () => {
  setActiveView("materials");
  const username = ensureIdentity();
  if (!username) {
    return;
  }

    const query = materialQueryInput.value.trim() || promptInput.value.trim();
  if (!query) {
    materialsStatus.textContent = "Type one question first.";
    materialQueryInput.focus();
    return;
  }

  materialsStatus.textContent = "Preparing answer from your selected source...";
  try {
    const response = await fetch("/api/materials/tutor", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: username,
        idToken: getIdToken(),
        query,
        materialIds: [...selectedMaterialIds],
      }),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not answer from materials.");
    }
    setActiveView("tutor");
    appendMessage("user", `[Materials] ${query}`);
    appendMessage("agent", data.answer);
    materialsStatus.textContent = "Answer is ready in Tutor.";
    await refreshLearnerState();
    await refreshInsights();
  } catch (error) {
    materialsStatus.textContent = error.message;
  }
});

createMaterialsMockTestButton.addEventListener("click", async () => {
  setActiveView("materials");
  const username = ensureIdentity();
  if (!username) {
    return;
  }

  if (!selectedMaterialIds.size) {
    materialsStatus.textContent = "Choose 1 source first.";
    return;
  }

  const sampleStyleFile = materialsMockStyleFileInput.files?.[0] || null;
  createMaterialsMockTestButton.disabled = true;
  materialsStatus.textContent = "Creating mock test from your material...";
  try {
    const sampleStyleFromFile = sampleStyleFile ? await readFileAsText(sampleStyleFile) : "";
    const sampleStylePayload = [
      materialsMockStyleInput.value.trim(),
      sampleStyleFile ? `Uploaded sample exam: ${sampleStyleFile.name}` : "",
      sampleStyleFromFile.trim(),
    ].filter(Boolean).join("\n\n");

    const response = await fetch("/api/materials/mock-test", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: username,
        idToken: getIdToken(),
        materialIds: [...selectedMaterialIds],
        topic: materialQueryInput.value.trim(),
        level: diagnosticLevelSelect.value,
        goal: "Practice from uploaded materials",
        questionCount: 5,
        structure: materialsMockStructureInput.value.trim(),
        sampleStyle: sampleStylePayload,
      }),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not create mock test.");
    }

    activeAssessment = data;
    renderAssessmentQuestions(data.questions || []);
    diagnosticResult.classList.add("hidden");
    diagnosticForm.classList.remove("hidden");
    updateAssessmentActions();
    diagnosticTopicInput.value = data.topic || diagnosticTopicInput.value;
    assessmentStatus.textContent = "Mock test ready from your materials.";
    materialsStatus.textContent = "Mock test opened in Plan.";
    materialsMockStyleFileInput.value = "";
    setActiveView("plan");
    diagnosticForm.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    materialsStatus.textContent = error.message;
  } finally {
    createMaterialsMockTestButton.disabled = false;
  }
});

startDiagnosticButton.addEventListener("click", async () => {
  setActiveView("plan");
  const username = ensureIdentity();
  if (!username) {
    return;
  }

  const topic = diagnosticTopicInput.value.trim();
  if (!topic) {
    assessmentStatus.textContent = "Choose a topic first so the diagnostic can be personalized.";
    diagnosticTopicInput.focus();
    return;
  }

  startDiagnosticButton.disabled = true;
  assessmentStatus.textContent = "Generating your diagnostic...";
  diagnosticResult.classList.add("hidden");

  try {
    const response = await fetch("/api/diagnostic/start", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: username,
        idToken: getIdToken(),
        topic,
        goal: diagnosticGoalInput.value.trim(),
        availableTime: diagnosticTimeInput.value ? Number(diagnosticTimeInput.value) : null,
        level: diagnosticLevelSelect.value,
        questionCount: 5,
      }),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not generate diagnostic.");
    }

    activeAssessment = data;
    renderAssessmentQuestions(data.questions || []);
    diagnosticForm.classList.remove("hidden");
    updateAssessmentActions();
    assessmentStatus.textContent = `Diagnostic ready: ${data.question_count} questions on ${data.topic}.`;
  } catch (error) {
    assessmentStatus.textContent = error.message;
  } finally {
    startDiagnosticButton.disabled = false;
  }
});

diagnosticForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!activeAssessment?.assessment_id) {
    assessmentStatus.textContent = "Start a diagnostic first.";
    return;
  }

  const answers = {};
  for (const question of activeAssessment.questions || []) {
    if ((question.question_type || "multiple_choice") === "multiple_choice") {
      const selected = diagnosticForm.querySelector(`input[name="${question.question_id}"]:checked`);
      if (selected) {
        answers[question.question_id] = selected.value;
      }
    } else {
      const textAnswer = diagnosticForm.querySelector(`[name="${question.question_id}"]`);
      if (textAnswer?.value?.trim()) {
        answers[question.question_id] = textAnswer.value.trim();
      }
    }
  }

  if (Object.keys(answers).length < (activeAssessment.questions?.length || 0)) {
    assessmentStatus.textContent = "Answer every question before submitting.";
    return;
  }

  assessmentStatus.textContent = "Scoring your diagnostic and updating mastery...";
  try {
    const response = await fetch("/api/diagnostic/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: getUsername(),
        idToken: getIdToken(),
        assessmentId: activeAssessment.assessment_id,
        answers,
      }),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not submit diagnostic.");
    }

    renderAssessmentResult(data.result);
    assessmentStatus.textContent = data.result.recommended_next_action;
    diagnosticForm.classList.add("hidden");
    activeAssessment = null;
    updateAssessmentActions();
    await refreshLearnerState();
    await refreshMasteryBoard();
    await refreshRoadmap();
    await refreshInsights();
  } catch (error) {
    assessmentStatus.textContent = error.message;
  }
});

roadmapBoard.addEventListener("click", async (event) => {
  const openButton = event.target.closest("[data-open-session]");
  if (openButton) {
    openRoadmapSession({
      title: openButton.dataset.sessionTitle,
      focus: openButton.dataset.sessionFocus,
      duration_minutes: openButton.dataset.sessionDuration,
      phaseTitle: openButton.dataset.phaseTitle,
      phaseGoal: openButton.dataset.phaseGoal,
    });
    return;
  }

  const button = event.target.closest("[data-phase-id][data-session-id][data-status]");
  if (button) {
    await updateRoadmapSessionStatus(button);
    return;
  }

  const previewButton = event.target.closest("[data-preview-session]");
  if (previewButton) {
    previewRoadmapSessionByKey(previewButton.dataset.sessionKey, {
      statusMessage: "Session brief updated below.",
    });
    return;
  }
});

roadmapSummary.addEventListener("click", (event) => {
  const openButton = event.target.closest("[data-open-session]");
  if (openButton) {
    openRoadmapSession({
      title: openButton.dataset.sessionTitle,
      focus: openButton.dataset.sessionFocus,
      duration_minutes: openButton.dataset.sessionDuration,
      phaseTitle: openButton.dataset.phaseTitle,
      phaseGoal: openButton.dataset.phaseGoal,
    });
    return;
  }

  const previewButton = event.target.closest("[data-preview-session]");
  if (!previewButton) {
    return;
  }
  previewRoadmapSessionByKey(previewButton.dataset.sessionKey, {
    statusMessage: "Session brief updated below.",
  });
});

roadmapBoard.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }

  if (event.target.closest("[data-phase-id][data-session-id][data-status]")) {
    return;
  }

  const sessionCard = event.target.closest("[data-preview-session]");
  if (!sessionCard) {
    return;
  }

  event.preventDefault();
  previewRoadmapSessionByKey(sessionCard.dataset.sessionKey, {
    statusMessage: "Session brief updated below.",
  });
});

roadmapSessionDetail.addEventListener("click", (event) => {
  const openButton = event.target.closest("[data-open-session]");
  if (!openButton) {
    return;
  }

  openRoadmapSession({
    title: openButton.dataset.sessionTitle,
    focus: openButton.dataset.sessionFocus,
    duration_minutes: openButton.dataset.sessionDuration,
    phaseTitle: openButton.dataset.phaseTitle,
    phaseGoal: openButton.dataset.phaseGoal,
  });
});

materialsLibrary.addEventListener("change", (event) => {
  const checkbox = event.target.closest("[data-material-id]");
  if (!checkbox) {
    return;
  }
  if (checkbox.checked) {
    selectedMaterialIds.add(checkbox.dataset.materialId);
  } else {
    selectedMaterialIds.delete(checkbox.dataset.materialId);
  }
  updateMaterialsSelectionSummary();
});

materialsLibrary.addEventListener("click", async (event) => {
  const toggleButton = event.target.closest("[data-toggle-previous-resources]");
  if (toggleButton) {
    previousResourcesExpanded = !previousResourcesExpanded;
    renderMaterials(latestMaterials);
    return;
  }

  const deleteButton = event.target.closest("[data-delete-material]");
  if (!deleteButton) {
    return;
  }

  await deleteMaterial(deleteButton.dataset.deleteMaterial);
});

deleteAllMaterialsButton.addEventListener("click", async () => {
  await deleteAllMaterials();
});

demoPersonasBoard.addEventListener("click", (event) => {
  const button = event.target.closest("[data-demo-persona]");
  if (!button) {
    return;
  }
  applyDemoPersona(button.dataset.demoPersona);
});

focusTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    setActiveView(tab.dataset.viewTarget);
  });
});

voiceInputButton.addEventListener("click", () => {
  if (!speechRecognition) {
    voiceStatus.textContent = "Voice recognition is not available in this browser.";
    return;
  }
  if (isListening) {
    speechRecognition.stop();
    return;
  }
  speechRecognition.start();
});

voiceReplyButton.addEventListener("click", () => {
  if (!lastAgentReply) {
    voiceStatus.textContent = "No tutor reply available to speak yet.";
    return;
  }
  speakText(lastAgentReply.replace(/[#*_`>-]/g, " "));
  voiceStatus.textContent = "Speaking the latest tutor reply.";
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const username = ensureIdentity();
  if (!username) {
    return;
  }

  const userPrompt = promptInput.value.trim();
  if (!userPrompt) {
    promptInput.focus();
    return;
  }

  appendMessage("user", userPrompt);
  promptInput.value = "";

  const payload = {
    message: userPrompt,
    sessionId: getSessionId(),
    userId: username,
    idToken: getIdToken(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
    selectedMaterialIds: [...selectedMaterialIds],
    inputMode: pendingInputMode,
  };
  pendingInputMode = "text";

  submitButton.disabled = true;
  submitButton.classList.add("loading");

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), requestTimeoutMs);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      signal: controller.signal,
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Request failed.");
    }
    appendMessage("agent", data.reply);
    await refreshLearnerState();
    await refreshMasteryBoard();
    await refreshRoadmap();
    await refreshInsights();
  } catch (error) {
    const message = error.name === "AbortError" ? "Request timed out after 90 seconds." : error.message;
    appendMessage("agent", `Request failed: ${message}`);
  } finally {
    window.clearTimeout(timeoutId);
    submitButton.disabled = false;
    submitButton.classList.remove("loading");
  }
});

await bootstrapAuth();
setupVoiceRecognition();
setActiveView(window.localStorage.getItem(activeViewStorageKey) || "tutor");
ensureIdentity();
restoreSession();
await refreshLearnerState();
await refreshMasteryBoard();
await refreshRoadmap();
await refreshMaterials();
await refreshInsights();
await refreshSystemStatus();
await refreshDemoKit();
