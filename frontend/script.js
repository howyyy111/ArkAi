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
const tutorAttachmentInput = document.getElementById("tutor-attachment-input");
const attachTutorFileButton = document.getElementById("attach-tutor-file-button");
const tutorAttachmentsTray = document.getElementById("tutor-attachments");
const newSessionButton = document.getElementById("new-session-button");
const submitButton = document.getElementById("submit-button");
const usernameModal = document.getElementById("username-modal");
const closeModalButton = document.getElementById("close-modal-button");
const usernameForm = document.getElementById("username-form");
const usernameInput = document.getElementById("username-input");
const usernameSubmit = document.getElementById("username-submit");
const googleSigninButton = document.getElementById("google-signin-button");
const authHelper = document.getElementById("auth-helper");
const authPill = document.getElementById("auth-pill");
const authPillLabel = document.getElementById("auth-pill-label");
const profileDropdown = document.getElementById("profile-dropdown");
const displayEmail = document.getElementById("display-email");
const headerChangeAccount = document.getElementById("header-change-account");
const googleSavesStatus = document.getElementById("google-saves-status");
const connectGoogleSavesButton = document.getElementById("connect-google-saves-button");
const tutorIdentity = document.getElementById("tutor-identity");
const stateTitle = document.getElementById("state-title");
const stateSummary = document.getElementById("state-summary");
const sidebarProgressSummary = document.getElementById("sidebar-progress-summary");
const sideProgressTitle = document.getElementById("side-progress-title");
const sideProgressDetail = document.getElementById("side-progress-detail");
const sideProgressFill = document.getElementById("side-progress-fill");
const sideProgressPercent = document.getElementById("side-progress-percent");
const sideProgressLink = document.getElementById("side-progress-link");
const sideProgressAction = document.getElementById("side-progress-action");
const sidebarToggleButton = document.getElementById("sidebar-toggle-button");
const startDiagnosticButton = document.getElementById("start-diagnostic-button");
const planHome = document.getElementById("plan-home");
const diagnosticWorkspace = document.getElementById("diagnostic-workspace");
const roadmapWorkspace = document.getElementById("roadmap-workspace");
const diagnosticTopicInput = document.getElementById("diagnostic-topic");
const diagnosticGoalInput = document.getElementById("diagnostic-goal");
const diagnosticTimeInput = document.getElementById("diagnostic-time");
const diagnosticTimeUnitSelect = document.getElementById("diagnostic-time-unit");
const diagnosticLevelSelect = document.getElementById("diagnostic-level");
const diagnosticHomeStatus = document.getElementById("diagnostic-home-status");
const assessmentStatus = document.getElementById("assessment-status");
const materialsMockBackButton = document.getElementById("materials-mock-back-button");
const diagnosticForm = document.getElementById("diagnostic-form");
const diagnosticQuestions = document.getElementById("diagnostic-questions");
const diagnosticResult = document.getElementById("diagnostic-result");
const saveAssessmentGoogleDocButton = document.getElementById("save-assessment-google-doc-button");
const masteryScore = document.getElementById("mastery-score");
const masteryTopics = document.getElementById("mastery-topics");
const generateRoadmapButton = document.getElementById("generate-roadmap-button");
const rebuildRoadmapButton = document.getElementById("rebuild-roadmap-button");
const roadmapTopicInput = document.getElementById("roadmap-topic");
const roadmapGoalInput = document.getElementById("roadmap-goal");
const roadmapTimeInput = document.getElementById("roadmap-time");
const roadmapTimeUnitSelect = document.getElementById("roadmap-time-unit");
const roadmapDeadlineInput = document.getElementById("roadmap-deadline");
const roadmapStartDateInput = document.getElementById("roadmap-start-date");
const roadmapCalendarSyncInput = document.getElementById("roadmap-calendar-sync");
const roadmapCalendarStartTimeInput = document.getElementById("roadmap-calendar-start-time");
const roadmapCalendarTimeInput = document.getElementById("roadmap-calendar-time-input");
const roadmapCalendarTimeOptions = document.getElementById("roadmap-calendar-time-options");
const roadmapCalendarPeriodSelect = document.getElementById("roadmap-calendar-period-select");
const roadmapLevelSelect = document.getElementById("roadmap-level");
const roadmapHomeStatus = document.getElementById("roadmap-home-status");
const roadmapStatus = document.getElementById("roadmap-status");
const roadmapMode = document.getElementById("roadmap-mode");
const roadmapSummary = document.getElementById("roadmap-summary");
const roadmapSessionDetail = document.getElementById("roadmap-session-detail");
const roadmapBoard = document.getElementById("roadmap-board");
const viewRoadmapButton = document.getElementById("view-roadmap-button");
const previousRoadmapsButton = document.getElementById("previous-roadmaps-button");
const savedRoadmapsPanel = document.getElementById("saved-roadmaps-panel");
const savedRoadmapsList = document.getElementById("saved-roadmaps-list");
const closeSavedRoadmapsButton = document.getElementById("close-saved-roadmaps-button");
const deleteAllSavedRoadmapsButton = document.getElementById("delete-all-saved-roadmaps-button");
const deleteRoadmapButton = document.getElementById("delete-roadmap-button");
const saveRoadmapTasksButton = document.getElementById("save-roadmap-tasks-button");
const materialFileInput = document.getElementById("material-file");
const materialQueryInput = document.getElementById("material-query");
const materialsMockStructureInput = document.getElementById("materials-mock-structure");
const materialsMockStyleInput = document.getElementById("materials-mock-style");
const materialsMockStyleFileInput = document.getElementById("materials-mock-style-file");
const uploadMaterialButton = document.getElementById("upload-material-button");
const askMaterialsButton = document.getElementById("ask-materials-button");
const createMaterialsMockTestButton = document.getElementById("create-materials-mock-test-button");
const downloadMaterialsMockTestButton = document.getElementById("download-materials-mock-test-button");
const deleteAllMaterialsButton = document.getElementById("delete-all-materials-button");
const materialsStatus = document.getElementById("materials-status");
const materialsLibrary = document.getElementById("materials-library");
const materialsLibrarySummary = document.getElementById("materials-library-summary");
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
const insightsHome = document.getElementById("insights-home");
const reportWorkspace = document.getElementById("report-workspace");
const reportBoard = document.getElementById("report-board");
const focusTabs = Array.from(document.querySelectorAll("[data-view-target]"));
const focusViews = Array.from(document.querySelectorAll("[data-view]"));
const showHistoryButton = document.getElementById("show-history-button");
const shareChatButton = document.getElementById("share-chat-button");
const historyModal = document.getElementById("history-modal");
const closeHistoryButton = document.getElementById("close-history-button");
const historyListModal = document.getElementById("history-list-modal");

const idTokenStorageKey = "arkai-id-token";
const historyStorageKeyPrefix = "arkai-history-";
const activeViewStorageKey = "arkai-active-view";
const sidebarCollapsedStorageKey = "arkai-sidebar-collapsed";
const requestTimeoutMs = 90000;
const googleSavesPollIntervalMs = 2500;
const googleSavesPollTimeoutMs = 120000;
const googleSavesScopes = [
  "https://www.googleapis.com/auth/calendar.events",
  "https://www.googleapis.com/auth/tasks",
  "https://www.googleapis.com/auth/documents",
  "https://www.googleapis.com/auth/drive.file",
];
const maxMaterialFileSizeBytes = 5 * 1024 * 1024;
const maxMaterialLibrarySizeBytes = 25 * 1024 * 1024;
const maxTutorAttachmentCount = 3;
const maxTutorAttachmentTotalBytes = 5 * 1024 * 1024;

let authMode = "email_fallback";
let firebaseAuthClient = null;
let googleProvider = null;
let googleSavesProvider = null;
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
let latestSavedRoadmaps = [];
let selectedSavedRoadmapId = "";
let selectedRoadmapSessionKey = "";
let currentRoadmapDetailsExpanded = false;
let previousSessionsExpanded = false;
let selectedHistoryItemKey = "";
let previousResourcesExpanded = false;
let latestChatSessions = [];
let pendingTutorAttachments = [];
let googleSavesConnected = false;
let googleSavesConnectionInProgress = false;
let googleSavesSetupReady = true;
let hostedGoogleOauthReady = false;
let activeSession = {
  userId: "",
  sessionId: "",
  displayName: "",
  isAnonymous: true,
};
let isLoggingOutServerSession = false;
let shouldClearServerSessionOnFirebaseSignOut = false;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function parseApiResponse(response) {
  const rawText = await response.text();
  if (!rawText) {
    return {};
  }
  try {
    return JSON.parse(rawText);
  } catch {
    return {
      status: "error",
      message: rawText.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim() || "Server returned an unreadable response.",
    };
  }
}

function isLocalDevelopmentHost() {
  return ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
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
  const hasMockAssessment = hasAssessment && activeAssessment?.assessment_type === "mock_test";
  saveAssessmentGoogleDocButton?.classList.toggle("hidden", !hasAssessment);
  downloadMaterialsMockTestButton?.classList.toggle("hidden", !hasMockAssessment);
  materialsMockBackButton?.classList.toggle("hidden", !hasMockAssessment);
}

function downloadActiveAssessmentPdf() {
  if (!activeAssessment?.assessment_id) {
    materialsStatus.textContent = "Create a mock test first.";
    return;
  }
  const blob = buildAssessmentPdfBlob(activeAssessment);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const filenameTopic = String(activeAssessment.topic || "mock-test")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "mock-test";
  link.href = url;
  link.download = `${filenameTopic}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  materialsStatus.textContent = "Mock test downloaded.";
}

function setSidebarCollapsed(collapsed) {
  document.body.classList.toggle("sidebar-collapsed", Boolean(collapsed));
  window.localStorage.setItem(sidebarCollapsedStorageKey, collapsed ? "1" : "0");
  if (sidebarToggleButton) {
    sidebarToggleButton.setAttribute("aria-pressed", collapsed ? "true" : "false");
    sidebarToggleButton.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
    sidebarToggleButton.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
  }
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

function formatFileSize(bytes) {
  const size = Number(bytes || 0);
  if (!Number.isFinite(size) || size <= 0) {
    return "";
  }
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1).replace(/\.0$/, "")} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1).replace(/\.0$/, "")} MB`;
}

function validateSelectedFile(file, { fieldLabel = "File" } = {}) {
  if (!file) {
    return null;
  }
  if (file.size > maxMaterialFileSizeBytes) {
    return `${fieldLabel} is too large. Max size is ${formatFileSize(maxMaterialFileSizeBytes)}.`;
  }
  return null;
}

function roadmapProgressPercent(completedSessions, totalSessions, fallbackRate = null) {
  const completed = Number(completedSessions || 0);
  const total = Number(totalSessions || 0);
  if (Number.isFinite(completed) && Number.isFinite(total) && total > 0) {
    return Math.max(0, Math.min(100, Math.round((completed / total) * 100)));
  }
  const rate = Number(fallbackRate);
  if (Number.isFinite(rate)) {
    return Math.max(0, Math.min(100, Math.round(rate * 100)));
  }
  return 0;
}

function parseMockQuestionCount(structureText, fallback = 5) {
  const text = String(structureText || "").toLowerCase();
  const typePattern = "(?:mcqs?|multiple[-\\s]?choice|short[-\\s]?answers?|essays?)";
  const counts = [];
  for (const match of text.matchAll(new RegExp(`\\b(\\d{1,2})\\s+(?:x\\s+)?${typePattern}\\b`, "g"))) {
    counts.push(Number(match[1]));
  }
  for (const match of text.matchAll(new RegExp(`\\b${typePattern}\\s*[:x-]?\\s*(\\d{1,2})\\b`, "g"))) {
    counts.push(Number(match[1]));
  }
  if (!counts.length) {
    const totalMatch = text.match(/\b(?:generate|make|create|include|total)\s+(\d{1,2})\s+(?:questions?|items?)\b/);
    if (totalMatch) {
      counts.push(Number(totalMatch[1]));
    }
  }
  const total = counts.reduce((sum, count) => sum + (Number.isFinite(count) ? count : 0), 0);
  if (total > 0) {
    return Math.max(1, Math.min(30, total));
  }
  return fallback;
}

function updateUploadMaterialButtonState() {
  if (!uploadMaterialButton || !materialFileInput) {
    return;
  }
  const hasFile = Boolean(materialFileInput.files?.length);
  uploadMaterialButton.disabled = !hasFile;
  uploadMaterialButton.setAttribute("aria-disabled", hasFile ? "false" : "true");
}

function getTimeInMinutes(input, unitSelect) {
  normalizeTimeControlValue(input, unitSelect);
  const rawValue = Number(input?.value || 0);
  if (!Number.isFinite(rawValue) || rawValue <= 0) {
    return null;
  }
  const unit = unitSelect?.value === "hours" ? "hours" : "minutes";
  const cappedValue = unit === "hours"
    ? Math.min(24, rawValue)
    : Math.min(60, rawValue);
  return Math.max(1, Math.round(unit === "hours" ? cappedValue * 60 : cappedValue));
}

function syncTimeControl(input, unitSelect) {
  if (!input || !unitSelect) {
    return;
  }
  const isHours = unitSelect.value === "hours";
  input.min = "1";
  input.max = isHours ? "24" : "60";
  input.step = "1";
  input.placeholder = isHours ? "1" : "45";
  input.removeAttribute("list");
}

function normalizeTimeControlValue(input, unitSelect) {
  if (!input || !unitSelect || input.value === "") {
    syncTimeControl(input, unitSelect);
    return;
  }

  let rawValue = Number(input.value);
  if (!Number.isFinite(rawValue) || rawValue <= 0) {
    input.value = "";
    syncTimeControl(input, unitSelect);
    return;
  }

  const maxValue = unitSelect.value === "hours" ? 24 : 60;
  input.value = String(Math.min(maxValue, Math.max(1, Math.round(rawValue))));
  unitSelect.dataset.previousUnit = unitSelect.value || "minutes";
  syncTimeControl(input, unitSelect);
}

function setupTimeControl(input, unitSelect) {
  if (!input || !unitSelect) {
    return;
  }

  const getEmptySpinDefault = () => {
    const configuredDefault = Number(input.dataset.emptySpinDefault || 0);
    const fallbackDefault = unitSelect.value === "hours" ? 1 : 45;
    const maxValue = unitSelect.value === "hours" ? 24 : 60;
    const nextValue = Number.isFinite(configuredDefault) && configuredDefault > 0
      ? configuredDefault
      : fallbackDefault;
    return String(Math.min(maxValue, Math.max(1, Math.round(nextValue))));
  };

  const applyEmptySpinDefault = () => {
    input.value = getEmptySpinDefault();
    unitSelect.dataset.previousUnit = unitSelect.value || "minutes";
    syncTimeControl(input, unitSelect);
  };

  unitSelect.dataset.previousUnit = unitSelect.value || "minutes";
  syncTimeControl(input, unitSelect);

  input.addEventListener("pointerdown", (event) => {
    if (input.value !== "" || input.type !== "number") {
      return;
    }
    if (event.offsetX >= input.clientWidth - 32) {
      input.dataset.pendingEmptySpinDefault = "true";
    }
  });
  input.addEventListener("keydown", (event) => {
    if ((event.key === "ArrowUp" || event.key === "ArrowDown") && input.value === "") {
      event.preventDefault();
      applyEmptySpinDefault();
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });
  input.addEventListener("input", () => {
    if (input.dataset.pendingEmptySpinDefault === "true") {
      delete input.dataset.pendingEmptySpinDefault;
      applyEmptySpinDefault();
      return;
    }
    const maxValue = unitSelect.value === "hours" ? 24 : 60;
    if (Number(input.value) > maxValue) {
      normalizeTimeControlValue(input, unitSelect);
    }
  });
  input.addEventListener("blur", () => normalizeTimeControlValue(input, unitSelect));
  input.addEventListener("change", () => normalizeTimeControlValue(input, unitSelect));
  unitSelect.addEventListener("change", () => {
    const previousUnit = unitSelect.dataset.previousUnit || "minutes";
    const rawValue = Number(input.value || 0);
    if (Number.isFinite(rawValue) && rawValue > 0) {
      if (previousUnit === "minutes" && unitSelect.value === "hours") {
        input.value = String(Math.min(24, Math.max(1, Math.ceil(rawValue / 60))));
      } else if (previousUnit === "hours" && unitSelect.value !== "hours") {
        input.value = String(Math.min(60, Math.max(1, Math.round(rawValue * 60))));
      }
    }
    unitSelect.dataset.previousUnit = unitSelect.value || "minutes";
    normalizeTimeControlValue(input, unitSelect);
  });
}

function normalizeRoadmapStatus(status) {
  const normalizedStatus = String(status || "planned").trim().toLowerCase();
  if (normalizedStatus === "completed" || normalizedStatus === "missed") {
    return normalizedStatus;
  }
  return "planned";
}

function getCurrentLibraryUsageBytes() {
  return latestMaterials.reduce((sum, material) => sum + Number(material?.metadata?.size_bytes || 0), 0);
}

function updateMaterialsLibrarySummary() {
  if (!materialsLibrarySummary) {
    return;
  }
  const used = getCurrentLibraryUsageBytes();
  materialsLibrarySummary.textContent = `Upload and save files. Create a mock test when ready. ${formatFileSize(used)} used of ${formatFileSize(maxMaterialLibrarySizeBytes)}.`;
  if (deleteAllMaterialsButton) {
    deleteAllMaterialsButton.disabled = latestMaterials.length === 0;
  }
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
  setActiveNavigation(nextView);
  focusViews.forEach((view) => {
    view.classList.toggle("is-active", view.dataset.view === nextView);
  });
  window.localStorage.setItem(activeViewStorageKey, nextView);
}

function setActiveNavigation(viewName) {
  const nextView = String(viewName || "tutor").trim() || "tutor";
  focusTabs.forEach((tab) => {
    const isActive = tab.dataset.viewTarget === nextView;
    tab.classList.toggle("is-active", isActive);
    tab.setAttribute("aria-pressed", isActive ? "true" : "false");
  });
}

function showPlanWorkspace(workspace = "home") {
  const target = String(workspace || "home");
  planHome?.classList.toggle("hidden", target !== "home");
  diagnosticWorkspace?.classList.toggle("hidden", target !== "diagnostic");
  roadmapWorkspace?.classList.toggle("hidden", target !== "roadmap");
  if (target !== "roadmap") {
    roadmapWorkspace?.classList.remove("showing-previous-roadmaps");
  }
}

function showInsightsWorkspace(workspace = "home") {
  const target = String(workspace || "home");
  insightsHome?.classList.toggle("hidden", target !== "home");
  reportWorkspace?.classList.toggle("hidden", target !== "report");
}

function getHistory() {
  const sid = getSessionId();
  const uid = getUsername() || "anonymous";
  try {
    return JSON.parse(window.localStorage.getItem(`${historyStorageKeyPrefix}${uid}-${sid}`)) || [];
  } catch {
    return [];
  }
}

function saveHistoryItem(role, body) {
  const sid = getSessionId();
  const uid = getUsername() || "anonymous";
  const hist = getHistory();
  hist.push({ role, body });
  window.localStorage.setItem(`${historyStorageKeyPrefix}${uid}-${sid}`, JSON.stringify(hist));
}

function buildClientChatMessages() {
  const visibleMessages = Array.from(messages.querySelectorAll(".message"))
    .map((messageNode) => {
      const bodyNode = messageNode.querySelector(".message-body");
      const content = String(bodyNode?.innerText || bodyNode?.textContent || "").trim();
      if (!content) {
        return null;
      }
      return {
        role: messageNode.classList.contains("user") ? "user" : "assistant",
        content,
      };
    })
    .filter(Boolean);

  if (visibleMessages.some((message) => message.role === "assistant")) {
    return visibleMessages.slice(-30);
  }

  return getHistory().slice(-30).map((message) => ({
    role: message.role === "agent" ? "assistant" : message.role,
    content: message.body || "",
  })).filter((message) => message.content.trim());
}

function buildEmptyStateMarkup() {
  return `
    <div class="empty-state">
      <div class="empty-state-copy">
        <h4>Start with a small, clear ask.</h4>
        <p>Choose a prompt below or write your own question.</p>
      </div>
      <div class="starter-prompts">
        <button class="starter-chip" type="button" data-starter-prompt="Teach me Python loops simply">Teach me Python loops simply</button>
        <button class="starter-chip" type="button" data-starter-prompt="Quiz me on this topic">Quiz me on this topic</button>
        <button class="starter-chip" type="button" data-starter-prompt="Continue my roadmap session">Continue my roadmap session</button>
        <button class="starter-chip" type="button" data-starter-prompt="Give me one lesson and one exercise">Give me one lesson and one exercise</button>
      </div>
    </div>
  `;
}

function setVoiceStatus(message = "") {
  if (!voiceStatus) {
    return;
  }
  const text = String(message || "").trim();
  voiceStatus.textContent = text;
  voiceStatus.classList.toggle("hidden", !text);
}

function autoresizePrompt() {
  if (!promptInput) {
    return;
  }
  promptInput.style.height = "auto";
  const nextHeight = Math.min(promptInput.scrollHeight, 150);
  promptInput.style.height = `${Math.max(nextHeight, 36)}px`;
}

async function clearSessionState() {
  setVoiceStatus("");
  const previousUserId = getUsername() || "anonymous";
  const previousSessionId = getSessionId();
  if (previousSessionId) {
    window.localStorage.removeItem(`${historyStorageKeyPrefix}${previousUserId}-${previousSessionId}`);
  }
  await refreshSession({ resetSession: true });
  messages.innerHTML = buildEmptyStateMarkup();
  autoresizePrompt();
}

async function loadChatSession(sessionId) {
  const targetSessionId = String(sessionId || "").trim();
  if (!targetSessionId) {
    return;
  }

  const response = await fetch(`/api/chat/messages?sessionId=${encodeURIComponent(targetSessionId)}`, {
    headers: buildAuthHeaders(),
  });
  const data = await response.json();
  if (!response.ok || data.status !== "success") {
    throw new Error(data.error || data.message || "Could not open that chat.");
  }

  await refreshSession({ sessionId: targetSessionId });
  messages.innerHTML = "";
  const chatMessages = data.messages || [];
  if (!chatMessages.length) {
    messages.innerHTML = buildEmptyStateMarkup();
  } else {
    for (const message of chatMessages) {
      appendMessage(message.role === "assistant" ? "agent" : message.role, message.content || "", true);
    }
  }
  closeHistoryModal();
  setVoiceStatus("Saved chat opened.");
}

async function deleteChatSessionFromHistory(sessionId) {
  const targetSessionId = String(sessionId || "").trim();
  if (!targetSessionId) {
    return;
  }

  const response = await fetch("/api/chat/delete", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
    },
    body: JSON.stringify({ targetSessionId }),
  });
  const data = await response.json();
  if (!response.ok || data.status !== "success") {
    throw new Error(data.error || data.message || "Could not delete saved chat.");
  }

  const uid = getUsername() || "anonymous";
  window.localStorage.removeItem(`${historyStorageKeyPrefix}${uid}-${targetSessionId}`);
  if (targetSessionId === getSessionId()) {
    await clearSessionState();
  }
}

async function deleteAllChatSessionsFromHistory() {
  const confirmed = window.confirm("Delete all saved Tutor chat sessions? This cannot be undone.");
  if (!confirmed) {
    return;
  }

  const response = await fetch("/api/chat/delete-all", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
    },
    body: JSON.stringify({}),
  });

  let data = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok || data.status !== "success") {
    if (response.status !== 404 || !latestChatSessions.length) {
      throw new Error(data.error || data.message || "Could not delete saved chats.");
    }
    for (const session of latestChatSessions) {
      if (session?.session_id) {
        await deleteChatSessionFromHistory(session.session_id);
      }
    }
  } else {
    const uid = getUsername() || "anonymous";
    for (const session of latestChatSessions) {
      if (session?.session_id) {
        window.localStorage.removeItem(`${historyStorageKeyPrefix}${uid}-${session.session_id}`);
      }
    }
  }

  await clearSessionState();
  if (historyListModal) {
    historyListModal.innerHTML = `<p class="mastery-empty">${escapeHtml(data.message || "Saved chats deleted.")}</p>`;
  }
}

async function openAccountSwitcher() {
  closeProfileDropdown();
  if (firebaseAuthClient && firebaseAuthClient.currentUser) {
    await signOut(firebaseAuthClient);
  }
  await logoutServerSession();
  updateAuthPill(activeSession.displayName || "Guest session", true);
  openUsernameModal(false);
  await refreshLearnerState();
  await refreshMasteryBoard();
  await refreshRoadmap();
  await refreshMaterials();
  await refreshInsights();
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
  return activeSession.sessionId || "";
}

function sanitizeUsername(value) {
  return value.trim().toLowerCase().slice(0, 120);
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function getFallbackUserId() {
  return sanitizeUsername(window.localStorage.getItem("arkai-fallback-user") || "");
}

function setFallbackUserId(value) {
  const normalized = sanitizeUsername(value || "");
  if (normalized) {
    window.localStorage.setItem("arkai-fallback-user", normalized);
  } else {
    window.localStorage.removeItem("arkai-fallback-user");
  }
}

function getUsername() {
  return sanitizeUsername(activeSession.userId || "");
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

function applySession(session) {
  activeSession = {
    userId: session?.userId || "",
    sessionId: session?.sessionId || "",
    displayName: session?.displayName || "",
    isAnonymous: Boolean(session?.isAnonymous),
  };
  shouldClearServerSessionOnFirebaseSignOut = !activeSession.isAnonymous;
  syncSessionChrome();
  refreshGoogleSavesStatus();
  return activeSession;
}

async function refreshSession(options = {}) {
  const loadSession = async () => {
    const method = Object.keys(options).length ? "POST" : "GET";
    return await fetch("/api/session", {
      method,
      headers: {
        ...(method === "POST" ? { "Content-Type": "application/json" } : {}),
        ...buildAuthHeaders(),
      },
      body: method === "POST" ? JSON.stringify(options) : undefined,
    });
  };

  let response = await loadSession();
  if (response.status === 401 && getIdToken()) {
    setIdToken("");
    response = await loadSession();
  }

  const data = await response.json();
  if (!response.ok || data.status !== "success") {
    throw new Error(data.error || "Could not establish a user session.");
  }
  return applySession(data);
}

function openUsernameModal(prefill = true) {
  usernameModal.classList.add("open");
  usernameModal.setAttribute("aria-hidden", "false");
  usernameInput.value = prefill ? getUsername() || getFallbackUserId() : "";
  usernameInput.setCustomValidity("");
  usernameInput.focus();
  usernameInput.select();
}

function closeUsernameModal() {
  usernameModal.classList.remove("open");
  usernameModal.setAttribute("aria-hidden", "true");
}

if (closeModalButton) {
  closeModalButton.addEventListener("click", () => {
    // Only allow closing if we already have a session (don't let them bypass initial setup if required)
    if (activeSession || getUsername()) {
      closeUsernameModal();
    } else {
      // If they somehow have no session at all, just fall back to guest session
      usernameForm.dispatchEvent(new Event("submit"));
    }
  });
}

function updateAuthPill(label, subtle = false) {
  const value = String(label || "").trim() || "Guest session";
  authPill.setAttribute("aria-label", value);
  authPill.setAttribute("title", value);
  authPill.classList.toggle("subtle", subtle);
  if (authPillLabel) {
    authPillLabel.textContent = value;
  }
  if (displayEmail) {
    displayEmail.textContent = value;
  }
  if (tutorIdentity) {
    tutorIdentity.textContent = value;
  }
}

function syncSessionChrome() {
  const label = activeSession.displayName || activeSession.userId || "Guest session";
  if (displayEmail) {
    displayEmail.textContent = label;
  }
  if (authPillLabel) {
    authPillLabel.textContent = label;
  }
  if (tutorIdentity) {
    tutorIdentity.textContent = label;
  }
  if (authPill) {
    authPill.setAttribute("aria-label", label);
    authPill.setAttribute("title", label);
  }
}

function setGoogleSavesStatus(text, connected = false) {
  googleSavesConnected = Boolean(connected);
  if (googleSavesStatus) {
    googleSavesStatus.textContent = text;
  }
  if (connectGoogleSavesButton) {
    const statusText = String(text || "").toLowerCase();
    const connectionFailed =
      statusText.includes("failed")
      || (statusText.includes("not connected") && !statusText.includes("not connected yet"))
      || statusText.includes("check failed")
      || statusText.includes("closed before")
      || statusText.includes("try connect again");
    connectGoogleSavesButton.textContent = googleSavesConnectionInProgress
      ? "Connecting..."
      : connected ? "Connected" : connectionFailed ? "Reconnect" : "Connect";
    connectGoogleSavesButton.disabled =
      googleSavesConnectionInProgress
      || !googleSavesSetupReady
      || connected
      || Boolean(activeSession.isAnonymous)
      || authMode !== "firebase";
  }
}

async function refreshGoogleSavesStatus() {
  if (activeSession.isAnonymous) {
    setGoogleSavesStatus("Sign in with Google first", false);
    return { connected: false };
  }
  try {
    const response = await fetch("/api/google/status", { headers: buildAuthHeaders() });
    const data = await parseApiResponse(response);
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not check Google saves.");
    }
    googleSavesSetupReady = data.setup_ready !== false;
    hostedGoogleOauthReady = Boolean(data.hosted_oauth_ready);
    if (!googleSavesSetupReady) {
      setGoogleSavesStatus(data.message || "Google saves is not configured", false);
      return data;
    }
    setGoogleSavesStatus(data.connected ? "Connected to Google saves" : "Not connected yet", Boolean(data.connected));
    return data;
  } catch (error) {
    setGoogleSavesStatus("Check failed", false);
    return { connected: false, error: error.message };
  }
}

async function waitForGoogleSavesConnection(authWindow) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < googleSavesPollTimeoutMs) {
    const status = await refreshGoogleSavesStatus();
    if (status.connected) {
      if (authWindow && !authWindow.closed) {
        authWindow.close();
      }
      authHelper.textContent = "Google saves connected. Docs, Calendar, and Tasks are ready.";
      return status;
    }
    if (authWindow?.closed) {
      authHelper.textContent = "Google permission window closed before ArkAI could confirm the connection.";
      return status;
    }
    await new Promise((resolve) => window.setTimeout(resolve, googleSavesPollIntervalMs));
  }
  authHelper.textContent = "Still waiting for Google. If you finished the permission screen, try Connect again to refresh the status.";
  return { connected: false };
}

async function connectGoogleSavesWithAccessToken(accessToken, { expiresIn = null } = {}) {
  const token = String(accessToken || "").trim();
  if (!token) {
    throw new Error("Google did not return a saves permission token. Try Connect again and approve the requested permissions.");
  }
  const response = await fetch("/api/google/connect-token", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
    },
    body: JSON.stringify({
      accessToken: token,
      expiresIn,
    }),
  });
  const data = await parseApiResponse(response);
  if (!response.ok || data.status !== "success") {
    throw new Error(data.error || data.message || "Could not connect Google saves.");
  }
  setGoogleSavesStatus("Connected to Google saves", true);
  authHelper.textContent = "Google saves connected. Docs, Calendar, and Tasks are ready.";
  return data;
}

async function connectGoogleSavesWithFirebasePopup({ askFirst = true } = {}) {
  if (!firebaseAuthClient || !googleSavesProvider) {
    throw new Error("Google Sign-In is not ready yet.");
  }
  if (askFirst) {
    const approved = window.confirm(
      "Connect Google saves for this ArkAI account? Google will ask permission for Docs, Drive, Tasks, and Calendar saves."
    );
    if (!approved) {
      return { connected: false };
    }
  }
  googleSavesConnectionInProgress = true;
  setGoogleSavesStatus("Opening Google permission screen...", false);
  try {
    const result = await signInWithPopup(firebaseAuthClient, googleSavesProvider);
    if (result?.user) {
      const idToken = await result.user.getIdToken();
      await createServerSession(idToken);
      updateAuthPill(result.user.email || activeSession.displayName || "Signed in", false);
    }
    const credential = GoogleAuthProvider.credentialFromResult(result);
    await connectGoogleSavesWithAccessToken(credential?.accessToken || "");
    return { connected: true };
  } finally {
    googleSavesConnectionInProgress = false;
    await refreshGoogleSavesStatus();
  }
}

async function connectGoogleSaves({ askFirst = true, forceReconnect = false } = {}) {
  if (!googleSavesSetupReady) {
    authHelper.textContent = "Google saves is not configured on this server. Add the OAuth client credentials and callback URL, then restart ArkAI.";
    setGoogleSavesStatus("Google saves not configured", false);
    return;
  }
  if (activeSession.isAnonymous) {
    authHelper.textContent = "Sign in with Google before connecting Docs, Calendar, and Tasks.";
    openUsernameModal(false);
    return;
  }
  const currentStatus = await refreshGoogleSavesStatus();
  if (currentStatus.connected && !forceReconnect) {
    authHelper.textContent = "Google saves connected. Docs, Calendar, and Tasks are ready.";
    return;
  }
  if (askFirst) {
    const approved = window.confirm(
      "Connect Google saves for this ArkAI account? ArkAI will ask Google for permission to create study docs, tasks, and calendar events when you request them."
    );
    if (!approved) {
      setGoogleSavesStatus("Not connected", false);
      return;
    }
  }

  if ((isLocalDevelopmentHost() || !hostedGoogleOauthReady) && firebaseAuthClient && googleSavesProvider) {
    try {
      await connectGoogleSavesWithFirebasePopup({ askFirst: false });
      return;
    } catch (error) {
      console.warn("Firebase Google saves connection failed; trying hosted OAuth callback.", error);
    }
  }

  const authWindow = window.open("", "_blank");
  if (authWindow) {
    authWindow.document.title = "Connecting Google saves";
    authWindow.document.body.innerHTML = "<p style=\"font-family: system-ui, sans-serif; padding: 24px;\">Opening Google permission screen...</p>";
  }

  googleSavesConnectionInProgress = true;
  const oldText = connectGoogleSavesButton.textContent;
  setGoogleSavesStatus("Opening Google permission screen...", false);
  try {
    const response = await fetch("/api/google/connect", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({ forceReconnect }),
    });
    const data = await parseApiResponse(response);
    if (!response.ok || !["success", "auth_required"].includes(data.status)) {
      if (String(data.message || "").includes("credentials.json") || String(data.message || "").includes("AUTH_CALLBACK_URL")) {
        await connectGoogleSavesWithFirebasePopup({ askFirst: false });
        return;
      }
      throw new Error(data.error || data.message || "Could not connect Google saves.");
    }
    if (data.status === "success" && data.connected) {
      if (authWindow && !authWindow.closed) {
        authWindow.close();
      }
      setGoogleSavesStatus("Connected", true);
      authHelper.textContent = "Google saves connected. Docs, Calendar, and Tasks are ready.";
      return;
    }
    const authUrl = String(data.authorization_url || "").trim();
    if (!authUrl) {
      throw new Error(data.message || "Google authorization link is missing.");
    }
    if (authWindow && !authWindow.closed) {
      authWindow.location.href = authUrl;
    } else {
      window.location.assign(authUrl);
      return;
    }
    setGoogleSavesStatus("Finish permission in Google", false);
    await waitForGoogleSavesConnection(authWindow);
  } catch (error) {
    if (authWindow && !authWindow.closed) {
      authWindow.close();
    }
    setGoogleSavesStatus("Not connected", false);
    authHelper.textContent = error.message;
  } finally {
    googleSavesConnectionInProgress = false;
    if (connectGoogleSavesButton.textContent === "Connecting..." || connectGoogleSavesButton.textContent === oldText) {
      connectGoogleSavesButton.textContent = oldText;
    }
    await refreshGoogleSavesStatus();
  }
}

window.addEventListener("message", (event) => {
  const payload = event.data || {};
  if (payload.type !== "arkai:google-oauth") {
    return;
  }
  if (payload.status === "success") {
    authHelper.textContent = "Google confirmed permission. Checking connection...";
    refreshGoogleSavesStatus().then((status) => {
      if (status.connected) {
        authHelper.textContent = "Google saves connected. Docs, Calendar, and Tasks are ready.";
      }
    });
  }
});

function handleGoogleSaveAuthRequired(message, statusNode) {
  const text = message || "Connect Google saves from the account menu first.";
  if (statusNode) {
    statusNode.textContent = text;
  }
  setGoogleSavesStatus("Not connected", false);
  toggleProfileDropdown(true);
}

function isGoogleSavePrompt(value) {
  const text = String(value || "").toLowerCase();
  if (!text.includes("save")) {
    return false;
  }
  return [
    "google doc",
    "google docs",
    "google drive",
    "drive",
    "google task",
    "google tasks",
    "task",
    "tasks",
    "todo",
    "to-do",
    "google calendar",
    "google calender",
    "calendar",
    "calender",
    "gcal",
  ].some((phrase) => text.includes(phrase));
}

function requestGoogleSaveSetupFromChat() {
  if (activeSession.isAnonymous) {
    appendMessage(
      "agent",
      "You are still in a private guest session, so I cannot save to Google yet. Use Continue with Google first, then connect Google saves from the account menu."
    );
    openUsernameModal(false);
    return false;
  }
  if (!googleSavesConnected) {
    appendMessage(
      "agent",
      "Your ArkAI account is signed in, but Google saves is not connected yet. Open the account menu and press Connect under Google saves, then try the save again."
    );
    toggleProfileDropdown(true);
    refreshGoogleSavesStatus();
    return false;
  }
  return true;
}

function closeProfileDropdown() {
  if (!profileDropdown) {
    return;
  }
  profileDropdown.classList.add("hidden");
}

function toggleProfileDropdown(forceOpen) {
  if (!profileDropdown) {
    return;
  }
  const shouldOpen = typeof forceOpen === "boolean"
    ? forceOpen
    : profileDropdown.classList.contains("hidden");
  profileDropdown.classList.toggle("hidden", !shouldOpen);
}

function renderChatHistoryModal(sessions = []) {
  if (!historyModal || !historyListModal) {
    return;
  }
  latestChatSessions = sessions;
  historyListModal.innerHTML = sessions.length
    ? `
        <div class="history-modal-actions">
          <button class="ghost-button subtle-action" type="button" data-chat-session-delete-all="true">
            Delete all
          </button>
        </div>
        ${sessions.map((item) => `
          <article class="history-item history-item-modal${activeSession.sessionId === item.session_id ? " is-selected" : ""}">
            <button
              class="history-item-main"
              type="button"
              data-chat-session-open="${escapeHtml(item.session_id)}"
            >
              <strong>${escapeHtml(item.title || "Tutor session")}</strong>
              <span>${escapeHtml(formatRelativeDays(item.last_message_at || item.updated_at || item.created_at))} • ${Number(item.message_count || 0)} messages</span>
            </button>
            <button
              class="mini-button icon-label-button"
              type="button"
              data-chat-session-delete="${escapeHtml(item.session_id)}"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M3 6h18"></path>
                <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
                <path d="M10 11v6"></path>
                <path d="M14 11v6"></path>
              </svg>
              <span>Delete</span>
            </button>
          </article>
        `).join("")}
      `
    : `<p class="mastery-empty">No saved Tutor chats yet. Send a message, then use History to reopen it later.</p>`;
}

async function openHistoryModal() {
  if (!historyModal || !historyListModal) {
    return;
  }
  historyModal.classList.add("open");
  historyModal.setAttribute("aria-hidden", "false");
  historyListModal.innerHTML = `<p class="mastery-empty">Loading saved chats...</p>`;
  try {
    const response = await fetch("/api/chat/sessions", {
      headers: buildAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not load chat history.");
    }
    renderChatHistoryModal(data.sessions || []);
  } catch (error) {
    historyListModal.innerHTML = `<p class="mastery-empty">${escapeHtml(error.message || "Could not load chat history.")}</p>`;
  }
}

function closeHistoryModal() {
  if (!historyModal) {
    return;
  }
  historyModal.classList.remove("open");
  historyModal.setAttribute("aria-hidden", "true");
}

function buildShareTranscript() {
  const transcript = getHistory();
  if (!transcript.length) {
    return "";
  }
  return transcript
    .map((entry) => `${entry.role === "user" ? activeSession.displayName || getUsername() || "You" : "ARKAI"}: ${entry.body}`)
    .join("\n\n");
}

async function refreshLearnerState() {
  const username = getUsername();
  if (!username) {
    latestLearnerState = null;
    stateTitle.textContent = "Start with one clear question";
    stateSummary.textContent = "Ask a question or continue a session.";
    refreshOverview();
    refreshContinueLearningCard();
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

    const topic = data.current_topic || data.profile?.topic || "Your current learning focus";
    stateTitle.textContent = topic;

    const details = [];
    if (data.profile?.level) {
      details.push(data.profile.level);
    }
    if (data.profile?.available_time) {
      details.push(`${data.profile.available_time} min / day`);
    }
    if (typeof data.mastery?.overall_score === "number") {
      details.push(`${Math.round(data.mastery.overall_score * 100)}% mastery`);
    }
    if (data.roadmap_summary?.phase_count) {
      details.push(`${data.roadmap_summary.completed_sessions}/${data.roadmap_summary.total_sessions} sessions complete`);
    }
    details.push(data.recommended_next_action || "Ask one focused question.");
    stateSummary.textContent = details.join(" • ");
    refreshOverview();
    refreshContinueLearningCard();
  } catch (error) {
    latestLearnerState = null;
    stateTitle.textContent = "Your learning focus";
    stateSummary.textContent = "You can still ask the tutor a focused question.";
    refreshOverview();
    refreshContinueLearningCard();
  }
}

function renderMasteryBoard(mastery) {
  const overall = typeof mastery?.overall_score === "number" ? mastery.overall_score : 0;
  masteryScore.textContent = `${Math.round(overall * 100)}%`;

  const sessions = getPreviousSessions();
  const controls = `
    <div class="history-controls">
      <button class="ghost-button history-toggle" type="button" data-history-toggle="true">
        ${previousSessionsExpanded ? "Hide session history" : "Show session history"}
      </button>
      ${previousSessionsExpanded ? `
        <button class="ghost-button subtle-action" type="button" data-history-delete-all="true"${sessions.length ? "" : " disabled"}>
          Delete all
        </button>
      ` : ""}
    </div>
  `;

  if (!sessions.length) {
    masteryTopics.innerHTML = `
    ${controls}
      <p class="mastery-empty">No saved sessions yet.</p>
    `;
    return;
  }

  const selectedHistoryItem = findHistoryItemByKey(selectedHistoryItemKey) || sessions[0];
  if (!selectedHistoryItemKey) {
    selectedHistoryItemKey = "";
  }

  masteryTopics.innerHTML = `
    ${controls}
    ${previousSessionsExpanded ? `<p class="mastery-empty">Use History in the tutor panel to reopen or delete saved sessions.</p>` : ""}
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

  renderMasteryBoard(latestLearnerState?.mastery || { overall_score: 0, topics: [] });
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

function findSavedRoadmapItem(roadmapId) {
  const normalizedRoadmapId = String(roadmapId || "").trim();
  return latestSavedRoadmaps.find((item) => {
    const roadmap = item.roadmap || item;
    return String(roadmap?.roadmap_id || "").trim() === normalizedRoadmapId;
  }) || null;
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

function roadmapDisplayTitle(roadmap) {
  return String(roadmap?.topic || roadmap?.goal || "Saved roadmap").trim() || "Saved roadmap";
}

function roadmapShortDescription(roadmap, summary = {}) {
  const total = Number(summary.total_sessions || 0);
  const phaseCount = Number(summary.phase_count || roadmap?.phases?.length || 0);
  const days = Number(roadmap?.deadline_days || 0);
  const level = String(roadmap?.level || "beginner").trim();
  const bits = [];
  if (level) {
    bits.push(`${level.charAt(0).toUpperCase()}${level.slice(1)} plan`);
  }
  if (total) {
    bits.push(`${total} study sessions`);
  }
  if (phaseCount) {
    bits.push(`${phaseCount} phases`);
  }
  if (days) {
    bits.push(`${days} days`);
  }
  return bits.join(" • ") || "Saved study plan";
}

function renderRoadmapReadOnlyDetails(roadmap) {
  return (roadmap?.phases || [])
    .map((phase, phaseIndex) => `
      <section class="saved-roadmap-phase">
        <div class="saved-roadmap-phase-head">
          <div class="saved-roadmap-phase-index">${escapeHtml(String(phaseIndex + 1).padStart(2, "0"))}</div>
          <div>
            <p class="section-label">${escapeHtml(phase.title || "Phase")}</p>
            <h5>${escapeHtml(phase.goal || "Study phase")}</h5>
            ${phase.expected_outcome ? `<p>${escapeHtml(phase.expected_outcome)}</p>` : ""}
          </div>
        </div>
        <div class="saved-roadmap-sessions">
          ${(phase.sessions || []).map((session) => {
            const status = normalizeRoadmapStatus(session.status);
            return `
            <article class="saved-roadmap-session" data-session-status="${escapeHtml(status)}">
              <div>
                <strong>${escapeHtml(session.title || "Study session")}</strong>
                <p>${escapeHtml(session.focus || roadmapDisplayTitle(roadmap))} • ${escapeHtml(session.duration_minutes || 45)} min</p>
                <p class="roadmap-session-status">${escapeHtml(session.status || "planned")}</p>
              </div>
              <div class="saved-roadmap-session-actions">
                <button
                  class="mini-button"
                  type="button"
                  data-open-saved-session="true"
                  data-session-title="${escapeHtml(session.title || "Study session")}"
                  data-session-focus="${escapeHtml(session.focus || "")}"
                  data-session-duration="${escapeHtml(session.duration_minutes || "")}"
                  data-phase-title="${escapeHtml(phase.title || "")}"
                  data-phase-goal="${escapeHtml(phase.goal || "")}"
                >
                  Open in Tutor
                </button>
                <button class="mini-button${status === "completed" ? " is-active-status" : ""}" type="button" data-saved-session-status="completed" data-roadmap-id="${escapeHtml(roadmap.roadmap_id || "")}" data-phase-id="${escapeHtml(phase.phase_id || "")}" data-session-id="${escapeHtml(session.session_id || "")}">Complete</button>
                <button class="mini-button${status === "missed" ? " is-active-status" : ""}" type="button" data-saved-session-status="missed" data-roadmap-id="${escapeHtml(roadmap.roadmap_id || "")}" data-phase-id="${escapeHtml(phase.phase_id || "")}" data-session-id="${escapeHtml(session.session_id || "")}">Missed</button>
              </div>
            </article>
          `;
          }).join("")}
        </div>
      </section>
    `)
    .join("");
}

function renderSavedRoadmapDetail(item) {
  const roadmap = item?.roadmap || item;
  const summary = item?.summary || {};
  const title = roadmapDisplayTitle(roadmap);
  const completed = Number(summary.completed_sessions || 0);
  const total = Number(summary.total_sessions || 0);
  const progressText = total ? `${completed}/${total} sessions complete` : "No sessions counted yet";
  const description = roadmapShortDescription(roadmap, summary);

  savedRoadmapsList.innerHTML = `
    <article class="saved-roadmap-detail-page">
      <div class="saved-roadmap-detail-hero">
        <button class="ghost-button mini-button icon-only-button" type="button" data-back-to-saved-roadmaps="true" aria-label="Back to saved roadmaps" title="Back to saved roadmaps">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="m15 18-6-6 6-6"></path>
          </svg>
        </button>
        <div>
          <p class="section-label">Saved roadmap</p>
          <h4>${escapeHtml(title)} roadmap</h4>
          <p>${escapeHtml(roadmap.goal || "Saved study plan")}</p>
        </div>
        <div class="saved-roadmap-detail-meta">
          <span>${escapeHtml(description)}</span>
          <strong>${escapeHtml(progressText)}</strong>
        </div>
      </div>
      <div class="saved-roadmap-body">
        ${renderRoadmapReadOnlyDetails(roadmap)}
      </div>
    </article>
  `;
}

function renderSavedRoadmaps(roadmapItems = latestSavedRoadmaps) {
  if (!savedRoadmapsList || !savedRoadmapsPanel) {
    return;
  }
  latestSavedRoadmaps = (Array.isArray(roadmapItems) ? roadmapItems : []).filter((item) => !item?.is_current);
  const selectedItem = selectedSavedRoadmapId ? findSavedRoadmapItem(selectedSavedRoadmapId) : null;
  if (selectedItem) {
    renderSavedRoadmapDetail(selectedItem);
    return;
  }
  selectedSavedRoadmapId = "";
  if (!latestSavedRoadmaps.length) {
    savedRoadmapsList.innerHTML = `<p class="mastery-empty">No previous roadmaps yet. Create another topic roadmap and earlier roadmaps will appear here.</p>`;
    return;
  }

  savedRoadmapsList.innerHTML = latestSavedRoadmaps
    .map((item) => {
      const roadmap = item.roadmap || item;
      const summary = item.summary || {};
      const title = roadmapDisplayTitle(roadmap);
      const roadmapId = String(roadmap.roadmap_id || "").trim();
      const completed = Number(summary.completed_sessions || 0);
      const total = Number(summary.total_sessions || 0);
      const updated = roadmap.updated_at || roadmap.created_at || "";
      const progressText = total ? `${completed}/${total} sessions complete` : "No sessions counted yet";
      const description = roadmapShortDescription(roadmap, summary);
      return `
        <article class="saved-roadmap-item" data-saved-roadmap-card="${escapeHtml(roadmapId)}">
          <div class="saved-roadmap-overview">
            <div>
              <strong>${escapeHtml(title)} roadmap</strong>
              <span>${escapeHtml(description)}</span>
              <p>${escapeHtml(roadmap.goal || "Saved study plan")}</p>
            </div>
            <div class="saved-roadmap-meta">
              ${updated ? `<time>${escapeHtml(String(updated).slice(0, 10))}</time>` : ""}
              <span>${escapeHtml(progressText)}</span>
            </div>
          </div>
          <div class="saved-roadmap-actions">
            ${roadmapId ? `
              <button class="ghost-button mini-button" type="button" data-view-saved-roadmap="${escapeHtml(roadmapId)}">
                View details
              </button>
              <button class="saved-roadmap-delete-icon" type="button" data-delete-saved-roadmap="${escapeHtml(roadmapId)}" aria-label="Delete ${escapeHtml(title)} roadmap">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M3 6h18"></path>
                  <path d="M8 6V4h8v2"></path>
                  <path d="M19 6l-1 14H6L5 6"></path>
                  <path d="M10 11v5"></path>
                  <path d="M14 11v5"></path>
                </svg>
              </button>
            ` : ""}
          </div>
        </article>
      `;
    })
    .join("");
}

async function refreshSavedRoadmaps({ showPanel = false } = {}) {
  if (showPanel && savedRoadmapsPanel) {
    roadmapWorkspace?.classList.add("showing-previous-roadmaps");
    savedRoadmapsPanel.classList.remove("hidden");
    roadmapWorkspace?.scrollTo({ top: 0, behavior: "smooth" });
  }
  const username = getUsername();
  if (!username) {
    latestSavedRoadmaps = [];
    renderSavedRoadmaps([]);
    return;
  }
  try {
    const response = await fetch(`/api/roadmaps?userId=${encodeURIComponent(username)}`, {
      headers: buildAuthHeaders(),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not load saved roadmaps.");
    }
    renderSavedRoadmaps(data.roadmaps || []);
  } catch (error) {
    if (savedRoadmapsList) {
      savedRoadmapsList.innerHTML = `<p class="mastery-empty">${escapeHtml(error.message || "Could not load saved roadmaps.")}</p>`;
    }
  }
}

async function deleteSavedRoadmap(roadmapId) {
  const normalizedRoadmapId = String(roadmapId || "").trim();
  const username = getUsername();
  if (!normalizedRoadmapId || !username) {
    return;
  }
  const confirmed = window.confirm("Remove this previous saved roadmap? Your current roadmap will not be changed.");
  if (!confirmed) {
    return;
  }
  const response = await fetch("/api/roadmap/delete-saved", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
    },
    body: JSON.stringify({
      userId: username,
      idToken: getIdToken(),
      roadmapId: normalizedRoadmapId,
    }),
  });
  const data = await response.json();
  if (!response.ok || data.status !== "success") {
    throw new Error(data.error || data.message || "Could not remove saved roadmap.");
  }
  if (roadmapStatus) {
    roadmapStatus.textContent = data.message || "Saved roadmap removed.";
  }
  await refreshSavedRoadmaps({ showPanel: true });
}

async function deleteAllSavedRoadmaps() {
  const username = getUsername();
  if (!username || !latestSavedRoadmaps.length) {
    return;
  }
  const confirmed = window.confirm("Delete all previous saved roadmaps? Your current roadmap will not be changed.");
  if (!confirmed) {
    return;
  }
  const response = await fetch("/api/roadmap/delete-all-saved", {
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
    throw new Error(data.error || data.message || "Could not delete saved roadmaps.");
  }
  selectedSavedRoadmapId = "";
  if (roadmapStatus) {
    roadmapStatus.textContent = data.message || "Saved roadmaps deleted.";
  }
  await refreshSavedRoadmaps({ showPanel: true });
}

async function updateSavedRoadmapSessionStatus(button) {
  const username = getUsername();
  if (!username) {
    return;
  }
  button.disabled = true;
  const oldText = button.textContent;
  button.textContent = "Saving...";
  try {
    const response = await fetch("/api/roadmap/saved-session/update", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: username,
        idToken: getIdToken(),
        roadmapId: button.dataset.roadmapId,
        phaseId: button.dataset.phaseId,
        sessionId: button.dataset.sessionId,
        status: button.dataset.savedSessionStatus,
      }),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not update saved roadmap session.");
    }
    if (roadmapStatus) {
      roadmapStatus.textContent = data.message || "Saved session updated.";
    }
    await refreshSavedRoadmaps({ showPanel: true });
  } catch (error) {
    if (roadmapStatus) {
      roadmapStatus.textContent = error.message || "Could not update saved roadmap session.";
    }
  } finally {
    button.disabled = false;
    button.textContent = oldText;
  }
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
  roadmapStatus.textContent = `Loaded ${session.title} into Tutor.`;
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
  roadmapStatus.textContent = button.dataset.status === "completed" ? "Saving completion..." : "Saving miss...";
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
        ? "Session marked complete."
        : "Session marked missed.";
    roadmapStatus.scrollIntoView({ behavior: "smooth", block: "nearest" });
    await refreshLearnerState();
    await refreshMasteryBoard();
    await refreshInsights();
  } catch (error) {
    roadmapStatus.textContent = error.message;
  }
}

function renderRoadmapSessionDetail(session) {
  if (!roadmapSessionDetail) {
    return;
  }
  if (!session) {
    roadmapSessionDetail.innerHTML = "";
    return;
  }

  const durationText = session.duration_minutes ? `${session.duration_minutes} min` : "";
  const dueText = session.due_date ? (String(session.due_date).includes("ago") || session.due_date === "today" ? session.due_date : `Due ${session.due_date}`) : "";
  const focusText = session.focus || session.phaseGoal || "Study focus";
  const status = normalizeRoadmapStatus(session.status);
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
      <span class="status-pill status-${escapeHtml(status)}">${escapeHtml(session.status || "planned")}</span>
    </div>
    <div class="roadmap-detail-steps">
      <strong>How to use this</strong>
      <p>Open Tutor, learn this topic, do one short exercise, then come back and mark it complete.</p>
    </div>
    <div class="roadmap-calendar-panel">
      <label>
        <span>Calendar time</span>
        <input type="datetime-local" data-calendar-start />
      </label>
      <button
        class="ghost-button"
        type="button"
        data-save-calendar-session="true"
        data-session-title="${escapeHtml(session.title)}"
        data-session-focus="${escapeHtml(session.focus || "")}"
        data-session-duration="${escapeHtml(session.duration_minutes || 45)}"
        data-phase-title="${escapeHtml(session.phaseTitle || "")}"
        data-phase-goal="${escapeHtml(session.phaseGoal || "")}"
      >
        Save to Google Calendar
      </button>
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

function renderCurrentRoadmapSummaryCard(roadmap, summary) {
  const title = roadmapDisplayTitle(roadmap);
  const progressText =
    `${summary.completed_sessions}/${summary.total_sessions} sessions done • ` +
    `${roadmapProgressPercent(summary.completed_sessions, summary.total_sessions, summary.completion_rate)}% complete`;
  const description = roadmapShortDescription(roadmap, summary);
  const detailsId = "current-roadmap-details";
  return `
    <section class="current-roadmap-card">
      <div class="current-roadmap-card-main">
        <div>
          <p class="section-label">Current roadmap</p>
          <h4>${escapeHtml(title)} roadmap</h4>
          <p>${escapeHtml(roadmap.goal || "Your active study plan")}</p>
        </div>
        <div class="current-roadmap-card-meta">
          <span>${escapeHtml(description)}</span>
          <strong>${escapeHtml(progressText)}</strong>
        </div>
      </div>
      <button
        class="ghost-button mini-button"
        type="button"
        data-toggle-current-roadmap="true"
        aria-controls="${detailsId}"
        aria-expanded="${currentRoadmapDetailsExpanded ? "true" : "false"}"
      >
        ${currentRoadmapDetailsExpanded ? "Hide roadmap details" : "View roadmap details"}
      </button>
    </section>
  `;
}

function renderCurrentRoadmapDetailsHeader(roadmap, summary) {
  const title = roadmapDisplayTitle(roadmap);
  const progressText =
    `${summary.completed_sessions}/${summary.total_sessions} sessions done • ` +
    `${roadmapProgressPercent(summary.completed_sessions, summary.total_sessions, summary.completion_rate)}% complete`;
  return `
    <div class="current-roadmap-detail-bar">
      <div>
        <p class="section-label">Current roadmap</p>
        <h4>${escapeHtml(title)} roadmap</h4>
      </div>
      <div class="current-roadmap-detail-actions">
        <span>${escapeHtml(progressText)}</span>
        <button
          class="ghost-button mini-button"
          type="button"
          data-toggle-current-roadmap="true"
          aria-expanded="true"
        >
          Hide details
        </button>
      </div>
    </div>
  `;
}

function renderRoadmap(roadmapResult) {
  const roadmap = roadmapResult?.roadmap || null;
  const summary = roadmapResult?.summary || null;
  activeRoadmap = roadmap;
  activeRoadmapSummary = summary;
  refreshContinueLearningCard();

  if (!roadmap || !summary) {
    roadmapMode.textContent = "No roadmap yet";
    roadmapSummary.textContent = "Your next session will appear here.";
    if (viewRoadmapButton) {
      viewRoadmapButton.disabled = true;
    }
    if (previousRoadmapsButton) {
      previousRoadmapsButton.disabled = false;
    }
    if (deleteRoadmapButton) {
      deleteRoadmapButton.disabled = true;
    }
    if (rebuildRoadmapButton) {
      rebuildRoadmapButton.disabled = true;
    }
    if (saveRoadmapTasksButton) {
      saveRoadmapTasksButton.disabled = true;
    }
    currentRoadmapDetailsExpanded = false;
    renderRoadmapSessionDetail(null);
    roadmapBoard.innerHTML = `<p class="mastery-empty">No roadmap yet.</p>`;
    return;
  }

  if (viewRoadmapButton) {
    viewRoadmapButton.disabled = false;
  }
  if (deleteRoadmapButton) {
    deleteRoadmapButton.disabled = false;
  }
  if (rebuildRoadmapButton) {
    rebuildRoadmapButton.disabled = false;
  }
  if (saveRoadmapTasksButton) {
    saveRoadmapTasksButton.disabled = false;
  }
  if (roadmapStatus && /^create your roadmap/i.test(String(roadmapStatus.textContent || "").trim())) {
    roadmapStatus.textContent = "Current roadmap loaded.";
  }

  const nextRoadmapSession = findNextRoadmapSession(roadmap);
  roadmapMode.textContent = `${summary.mode} roadmap`;
  const progressText =
    `${summary.completed_sessions}/${summary.total_sessions} sessions done • ` +
    `${roadmapProgressPercent(summary.completed_sessions, summary.total_sessions, summary.completion_rate)}% complete`;
  if (nextRoadmapSession) {
    roadmapSummary.innerHTML = `
      <div class="roadmap-next-action">
        <div>
          <strong>Next up</strong>
          <p>${escapeHtml(nextRoadmapSession.title)} • Continue in Tutor when you are ready.</p>
        </div>
      </div>
      <p class="roadmap-progress-copy">${escapeHtml(progressText)}</p>
    `;
  } else {
    roadmapSummary.innerHTML = `<p class="roadmap-progress-copy">${escapeHtml(progressText)} • All sessions are done.</p>`;
  }

  const phasesMarkup = roadmap.phases
    .map((phase) => {
      const sessionsMarkup = (phase.sessions || [])
        .map((session) => {
          const sessionKey = buildRoadmapSessionKey(phase.phase_id, session.session_id);
          const status = normalizeRoadmapStatus(session.status);
          return `
            <article
              class="roadmap-session"
              data-session-key="${escapeHtml(sessionKey)}"
              data-session-status="${escapeHtml(status)}"
            >
              <div>
                <strong>${escapeHtml(session.title)}</strong>
                <p>${escapeHtml(session.focus || roadmapDisplayTitle(roadmap))} • ${escapeHtml(session.duration_minutes || 45)} min • due ${escapeHtml(session.due_date || "")}</p>
                <p class="roadmap-session-status">${escapeHtml(session.status || "planned")}</p>
              </div>
              <div class="roadmap-session-actions">
                <button
                  class="mini-button"
                  type="button"
                  data-open-session="true"
                  data-session-key="${escapeHtml(sessionKey)}"
                  data-session-title="${escapeHtml(session.title)}"
                  data-session-focus="${escapeHtml(session.focus || "")}"
                  data-session-duration="${escapeHtml(session.duration_minutes || "")}"
                  data-phase-title="${escapeHtml(phase.title || "")}"
                  data-phase-goal="${escapeHtml(phase.goal || "")}"
                >
                  Open in Tutor
                </button>
                <button class="mini-button${status === "completed" ? " is-active-status" : ""}" type="button" data-phase-id="${escapeHtml(phase.phase_id)}" data-session-id="${escapeHtml(session.session_id)}" data-status="completed">Complete</button>
                <button class="mini-button${status === "missed" ? " is-active-status" : ""}" type="button" data-phase-id="${escapeHtml(phase.phase_id)}" data-session-id="${escapeHtml(session.session_id)}" data-status="missed">Missed</button>
              </div>
            </article>
          `;
        })
        .join("");

      return `
        <section class="roadmap-phase">
          <div class="roadmap-phase-header">
            <div>
              <p class="section-label">${escapeHtml(phase.title || "Phase")}</p>
              <h5>${escapeHtml(phase.goal || "Study phase")}</h5>
            </div>
            <div class="roadmap-kicker">
              ${escapeHtml(phase.checkpoint_type || "checkpoint")}<br />
              due ${escapeHtml(phase.checkpoint_due_date || "")}
            </div>
          </div>
          <p>${escapeHtml(phase.expected_outcome || "")}</p>
          <div class="roadmap-session-list">${sessionsMarkup}</div>
        </section>
      `;
    })
    .join("");

  roadmapBoard.innerHTML = currentRoadmapDetailsExpanded
    ? `
      ${renderCurrentRoadmapDetailsHeader(roadmap, summary)}
      <div id="current-roadmap-details" class="current-roadmap-details">
        ${phasesMarkup}
      </div>
    `
    : renderCurrentRoadmapSummaryCard(roadmap, summary);
  renderRoadmapSessionDetail(null);
  refreshContinueLearningCard();
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
    await refreshSavedRoadmaps();
  } catch {
    renderRoadmap(null);
    await refreshSavedRoadmaps();
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
    materialsLibrary.innerHTML = `<p class="mastery-empty">Upload a file to build your materials library.</p>`;
    updateMaterialsLibrarySummary();
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
    const selectedClass = checked ? " is-selected" : "";
    const kindMeta = material.kind === "image"
      ? `${material.metadata?.width || "?"}x${material.metadata?.height || "?"}`
      : material.kind;
    const sizeLabel = formatFileSize(material.metadata?.size_bytes);
    const meta = [kindMeta, sizeLabel, `added ${formatMaterialTimeLabel(material.created_at)}`]
      .filter(Boolean)
      .join(" • ");
    return `
        <article class="material-card${selectedClass}">
          <header>
            <div>
              <p class="section-label">${material.kind}</p>
              <h5>${material.name}</h5>
            </div>
            <div class="material-card-actions">
              <label class="material-select-label">
                <input class="material-select" type="checkbox" data-material-id="${material.material_id}" ${checked} />
                Use
              </label>
              <button class="mini-button" type="button" data-delete-material="${material.material_id}">Delete</button>
            </div>
          </header>
          <p>${material.summary}</p>
          <p class="material-card-meta">${meta}</p>
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
          ${previousResourcesExpanded ? "Hide" : "Show"} previous resources (${previousMaterials.length})
        </button>
        ${previousResourcesExpanded ? `
          <div class="materials-history">
            ${previousMaterials.map(renderMaterialCard).join("")}
          </div>
        ` : ""}
      </section>
    ` : ""}
  `;
  updateMaterialsLibrarySummary();
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
  const renderEmptyInsights = () => {
    evaluationBoard.innerHTML = `
      <div class="insights-grid">
        <article class="insight-card insight-card-primary">
          <div class="insight-card-head">
            <div>
              <p class="section-label">Snapshot</p>
              <h4>No learning signal yet</h4>
              <p>ArkAI needs one learning action before it can summarize your progress.</p>
            </div>
            <strong class="insight-score">0%</strong>
          </div>
          <div class="insight-meter" aria-hidden="true"><span style="width: 0%"></span></div>
          <div class="insight-status-grid">
            <div class="insight-status-item"><strong>None</strong><span>Diagnostics</span><p>Take a quick check</p></div>
            <div class="insight-status-item"><strong>Missing</strong><span>Roadmap</span><p>Create next steps</p></div>
            <div class="insight-status-item"><strong>Missing</strong><span>Materials</span><p>Upload notes when useful</p></div>
            <div class="insight-status-item"><strong>None</strong><span>Activity</span><p>Finish one tutor session</p></div>
          </div>
        </article>
        <article class="insight-card">
          <p class="section-label">Next focus</p>
          <h4>Start here</h4>
          <p class="state-summary insights-compact-copy">Do one small action so Insights becomes useful.</p>
          <div class="next-focus-list">
            <div class="next-focus-item"><span>1</span><p>Ask the tutor one focused question.</p></div>
            <div class="next-focus-item"><span>2</span><p>Take a quick diagnostic when ready.</p></div>
            <div class="next-focus-item"><span>3</span><p>Create a roadmap after the check.</p></div>
          </div>
        </article>
      </div>
    `;
  };

  if (!snapshot) {
    renderEmptyInsights();
    return;
  }
  const assessmentCount = snapshot.coverage?.assessment_count || 0;
  const mockTestCount = snapshot.coverage?.mock_test_count || 0;
  const progressEvents = snapshot.coverage?.progress_events || 0;
  const roadmapPresent = Boolean(snapshot.coverage?.roadmap_present);
  const groundingAvailable = Boolean(snapshot.coverage?.grounding_available);
  const materialCount = snapshot.coverage?.material_count || 0;
  const tutorSessionCount = snapshot.coverage?.tutor_session_count || 0;
  const tutorMessageCount = snapshot.coverage?.tutor_message_count || 0;
  const masteryPercent = Math.round(Number(snapshot.quality?.overall_mastery_score || 0) * 100);
  const avgAssessment = snapshot.quality?.average_assessment_score;
  const journey = snapshot.journey || {};
  const completedSessions = Number(journey.roadmap_completed_sessions ?? snapshot.quality?.completed_sessions ?? 0);
  const totalSessions = Number(journey.roadmap_total_sessions ?? 0);
  const completionPercent = roadmapProgressPercent(
    completedSessions,
    totalSessions,
    snapshot.quality?.completion_rate,
  );
  const risks = Array.isArray(snapshot.risks) ? snapshot.risks : [];
  const recommendedActions = Array.isArray(snapshot.recommended_actions) ? snapshot.recommended_actions : [];
  const warnings = Array.isArray(snapshot.warnings) ? snapshot.warnings : [];
  const nextSteps = [];

  if (!assessmentCount) {
    nextSteps.push("Take a short diagnostic.");
  }
  if (!roadmapPresent) {
    nextSteps.push("Generate your roadmap.");
  }
  if (!groundingAvailable) {
    nextSteps.push("Upload study materials.");
  }
  if (!progressEvents) {
    nextSteps.push("Finish one study session.");
  }

  const priorityItems = recommendedActions.length ? recommendedActions : warnings.length ? warnings : nextSteps;
  if (!assessmentCount && !progressEvents && !roadmapPresent && !groundingAvailable && !tutorSessionCount) {
    renderEmptyInsights();
    return;
  }
  const readinessScore = [assessmentCount > 0, roadmapPresent, groundingAvailable, progressEvents > 0, tutorSessionCount > 0]
    .filter(Boolean).length;
  const readinessPercent = Math.round((readinessScore / 5) * 100);
  const progressMetric = roadmapPresent ? completionPercent : masteryPercent || readinessPercent;
  const progressLabel = roadmapPresent ? "roadmap complete" : masteryPercent ? "mastery" : "learning signal";
  const keyInsight = journey.behavior_summary
    || (assessmentCount
      ? "Assessment results are now strong enough to guide the next study action."
      : roadmapPresent
        ? "The learner has a plan, but needs an assessment checkpoint to measure retention."
        : groundingAvailable
          ? "Materials are ready; turn them into a mock test to measure exam readiness."
          : "ArkAI needs one measured learning action to make Insights useful.");
  const snapshotItems = [
    {
      label: "Tutor use",
      value: tutorSessionCount ? "Active" : "Not started",
      detail: tutorSessionCount ? `${tutorMessageCount} saved messages` : "Ask one focused question",
    },
    {
      label: "Measured work",
      value: assessmentCount ? `${assessmentCount}` : "Needed",
      detail: assessmentCount ? `${Math.round(Number(avgAssessment ?? 0) * 100)}% assessment average` : "Submit a diagnostic or mock test",
    },
    {
      label: "Roadmap",
      value: roadmapPresent ? "In progress" : "Missing",
      detail: roadmapPresent ? `${completedSessions}/${totalSessions} sessions complete` : "Create next steps",
    },
    {
      label: "Materials",
      value: groundingAvailable ? "Ready" : "Missing",
      detail: groundingAvailable ? `${mockTestCount} mock test${mockTestCount === 1 ? "" : "s"}` : "Upload notes when useful",
    },
  ];

  evaluationBoard.innerHTML = `
    <div class="insights-grid">
      <article class="insight-card insight-card-primary">
        <div class="insight-card-head">
          <div>
            <p class="section-label">Key insight</p>
            <h4>${escapeHtml(journey.current_topic || journey.roadmap_topic || "Learning signal")}</h4>
            <p>${escapeHtml(keyInsight)}</p>
          </div>
          <strong class="insight-score">${progressMetric}%</strong>
        </div>
        <div class="insight-meter" aria-hidden="true">
          <span style="width: ${progressMetric}%"></span>
        </div>
        <p class="state-summary insights-compact-copy">${escapeHtml(progressLabel)}</p>
      </article>
      <article class="insight-card">
        <p class="section-label">Snapshot</p>
        <h4>What ArkAI knows</h4>
        <div class="insight-status-grid">
          ${snapshotItems.map((item) => `
            <div class="insight-status-item">
              <strong>${escapeHtml(item.value)}</strong>
              <span>${escapeHtml(item.label)}</span>
              <p>${escapeHtml(item.detail)}</p>
            </div>
          `).join("")}
        </div>
      </article>
      <article class="insight-card">
        <p class="section-label">Next focus</p>
        <h4>${priorityItems.length ? "Next focus" : "Keep going"}</h4>
        <p class="state-summary insights-compact-copy">${priorityItems.length ? "Highest-impact actions from the current learner data." : "Enough signal. Continue your next session."}</p>
        ${priorityItems.length
      ? `<div class="next-focus-list">${priorityItems.slice(0, 3).map((item, index) => `
              <div class="next-focus-item">
                <span>${index + 1}</span>
                <p>${escapeHtml(item)}</p>
              </div>
            `).join("")}</div>`
      : `<div class="next-focus-list"><div class="next-focus-item"><span>1</span><p>Open your next Tutor session.</p></div></div>`}
        ${risks.length ? `
          <p class="section-label insights-risk-label">Risks to act on</p>
          <div class="next-focus-list">
            ${risks.slice(0, 2).map((item, index) => `
              <div class="next-focus-item">
                <span>${index + 1}</span>
                <p>${escapeHtml(item)}</p>
              </div>
            `).join("")}
          </div>
        ` : ""}
      </article>
    </div>
  `;
}

function renderInterventionPlan(plan) {
  latestInterventionPlan = plan;
  if (!plan) {
    interventionRisk.textContent = "Waiting for insights";
    interventionSummary.textContent = "Refresh to see your current progress and the next best step.";
    refreshOverview();
    return;
  }
  const riskLabelMap = {
    high: "Action needed",
    medium: "Checkpoint needed",
    low: "On track",
  };
  const riskLabel = riskLabelMap[plan.risk_level] || "Review needed";
  const completedSessions = Number(plan.completed_sessions || 0);
  const masteryPercent = Number.isFinite(plan.overall_mastery)
    ? Math.round(Number(plan.overall_mastery) * 100)
    : 0;
  const rawRecommended = (plan.recommended_actions || [])[0] || "Start one focused task.";
  const recommended = rawRecommended.length > 54
    ? `${rawRecommended.slice(0, 51).trim()}...`
    : rawRecommended;
  interventionRisk.textContent = riskLabel;
  interventionSummary.textContent = completedSessions
    ? `Mastery ${masteryPercent}%. ${completedSessions} done. Next: ${recommended}`
    : "Start with one measured action: a Tutor question, diagnostic, or material mock test.";
  refreshOverview();
}

function renderWeeklyReport(report) {
  latestWeeklyReport = report || null;
  if (!report) {
    reportBoard.innerHTML = `<p class="mastery-empty">No weekly report yet. Generate one when you want a shareable summary.</p>`;
    return;
  }
  reportBoard.innerHTML = `
    <article class="material-card">
      <header>
        <div>
          <p class="section-label">Report</p>
          <h5>${escapeHtml(report.title)}</h5>
        </div>
      </header>
      <p>${escapeHtml(report.note_text).replace(/\n/g, "<br />")}</p>
      <div class="inline-actions">
        <button id="save-report-docs-button" class="ghost-button icon-label-button" type="button">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"></path>
            <path d="M17 21v-8H7v8"></path>
            <path d="M7 3v5h8"></path>
          </svg>
          <span>Save to Google Docs</span>
        </button>
      </div>
      <p id="report-save-status" class="state-summary">Save this report to Google Docs when you are ready.</p>
    </article>
  `;
}

async function refreshInsights() {
  const username = getUsername();
  if (!username) {
    renderInterventionPlan(null);
    renderEvaluationSnapshot(null);
    renderWeeklyReport(null);
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
  const roadmapSummary = latestLearnerState?.roadmap_summary;
  const progressBits = [];
  if (masteryScoreValue > 0) {
    progressBits.push(`Mastery ${masteryScoreValue}%`);
  }
  if (roadmapSummary?.phase_count) {
    progressBits.push(`${roadmapSummary.completed_sessions}/${roadmapSummary.total_sessions} roadmap sessions complete`);
  }
  if (latestMaterials.length) {
    progressBits.push(`${latestMaterials.length} study materials ready`);
  }

  if (sidebarProgressSummary) {
    sidebarProgressSummary.textContent = progressBits.join(" • ") || "No saved progress yet.";
  }
}

function getContinueLearningSnapshot() {
  const roadmap = activeRoadmap || latestLearnerState?.roadmap || null;
  const summary = activeRoadmapSummary || latestLearnerState?.roadmap_summary || null;
  if (!roadmap || !summary?.phase_count) {
    return {
      hasRoadmap: false,
      title: "No roadmap yet",
      detail: "Create a roadmap to track your next session.",
      percent: 0,
      action: "Create roadmap",
    };
  }

  const totalSessions = Number(summary.total_sessions || 0);
  const completedSessions = Number(summary.completed_sessions || 0);
  const percent = roadmapProgressPercent(
    completedSessions,
    totalSessions,
    summary.completion_rate,
  );
  const nextSession = summary.next_session?.title
    ? summary.next_session
    : findNextRoadmapSession(roadmap);
  const title = roadmap.topic || roadmap.goal || (roadmap.mode ? `${roadmap.mode} roadmap` : "Current roadmap");
  const detail = nextSession?.title
    ? `Next: ${nextSession.title}`
    : "All roadmap sessions are complete.";

  return {
    hasRoadmap: true,
    title,
    detail: `${detail} • ${completedSessions}/${totalSessions} sessions`,
    percent,
    action: "View roadmap",
  };
}

function refreshContinueLearningCard() {
  if (!sideProgressTitle || !sideProgressDetail || !sideProgressFill || !sideProgressPercent) {
    return;
  }
  const snapshot = getContinueLearningSnapshot();
  sideProgressTitle.textContent = snapshot.title;
  sideProgressDetail.textContent = snapshot.detail;
  sideProgressPercent.textContent = `${snapshot.percent}%`;
  sideProgressFill.style.setProperty("--side-progress", `${snapshot.percent}%`);
  if (sideProgressAction) {
    const actionLabel = sideProgressAction.querySelector(".side-progress-action-label");
    if (actionLabel) {
      actionLabel.textContent = snapshot.action;
    } else {
      sideProgressAction.textContent = snapshot.action;
    }
  }
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
  if (!voiceInputButton) {
    return;
  }
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    setVoiceStatus("Browser speech recognition is not supported here.");
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
    setVoiceStatus("Voice input is listening. Speak your study request.");
  };

  speechRecognition.onend = () => {
    isListening = false;
    voiceInputButton.textContent = "Start voice input";
    if (voiceStatus.textContent.startsWith("Voice input is listening")) {
      setVoiceStatus("");
    }
  };

  speechRecognition.onresult = (event) => {
    const transcript = event.results?.[0]?.[0]?.transcript || "";
    if (!transcript) {
      return;
    }
    promptInput.value = transcript.trim();
    pendingInputMode = "voice";
    setVoiceStatus("Voice transcript captured. Edit if needed, then send.");
    promptInput.focus();
  };

  speechRecognition.onerror = (event) => {
    setVoiceStatus(`Voice input error: ${event.error}`);
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

if (saveAssessmentGoogleDocButton) {
  saveAssessmentGoogleDocButton.addEventListener("click", async () => {
    if (!activeAssessment?.assessment_id) {
      assessmentStatus.textContent = "Create a mock test first.";
      return;
    }

    const currentUsername = getUsername();
    if (!currentUsername) {
      assessmentStatus.textContent = "Sign in with Google before saving documents.";
      openUsernameModal(false);
      return;
    }

    saveAssessmentGoogleDocButton.setAttribute("disabled", "disabled");
    const oldText = saveAssessmentGoogleDocButton.textContent;
    saveAssessmentGoogleDocButton.textContent = "Saving...";

    try {
      const response = await fetch("/api/assessment/save-google-doc", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...buildAuthHeaders(),
        },
        body: JSON.stringify({
          userId: currentUsername,
          idToken: getIdToken(),
          assessmentId: activeAssessment.assessment_id,
          title: activeAssessment.topic || "Mock Test",
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || data.message || "Could not save document.");
      }

      if (data.status === "auth_required") {
        handleGoogleSaveAuthRequired(data.message, assessmentStatus);
        return;
      }

      assessmentStatus.textContent = "Mock test saved to Google Docs!";
      setTimeout(() => {
        assessmentStatus.textContent = "";
      }, 5000);
    } catch (err) {
      assessmentStatus.textContent = err.message;
    } finally {
      saveAssessmentGoogleDocButton.removeAttribute("disabled");
      saveAssessmentGoogleDocButton.textContent = oldText;
    }
  });
}

function ensureIdentity() {
  const username = getUsername();
  if (username) {
    closeUsernameModal();
    return username;
  }
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
          const copyButton = document.createElement("button");
          copyButton.className = "code-copy-button";
          copyButton.type = "button";
          copyButton.title = "Copy code";
          copyButton.setAttribute("aria-label", "Copy code");
          copyButton.dataset.copyCode = element.textContent || "";
          copyButton.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect width="14" height="14" x="8" y="8" rx="2"></rect>
              <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path>
            </svg>
          `;

          pre.parentNode.insertBefore(block, pre);
          block.appendChild(label);
          block.appendChild(copyButton);
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

  } else {
    const p = document.createElement("p");
    p.textContent = body;
    container.appendChild(p);
  }

  return container;
}

async function copyTextToClipboard(text) {
  const value = String(text || "");
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "-999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function buildCopyMessageButton(body = "") {
  const button = document.createElement("button");
  button.className = "message-copy-button";
  button.type = "button";
  button.title = "Copy message";
  button.setAttribute("aria-label", "Copy message");
  button.dataset.copyMessage = body;
  button.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
      stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <rect width="14" height="14" x="8" y="8" rx="2"></rect>
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path>
    </svg>
  `;
  return button;
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
  roleLabel.textContent = role === "user" ? activeSession.displayName || getUsername() || "You" : "ARKAI";

  article.appendChild(roleLabel);
  article.appendChild(buildMessageBody(body));
  article.appendChild(buildCopyMessageButton(body));
  messages.appendChild(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });

  if (role === "agent") {
    lastAgentReply = body;
    if (voiceAutospeak?.checked) {
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
  const fallbackUserId = getFallbackUserId();
  if (authMode !== "firebase" && fallbackUserId) {
    headers["X-Arkais-User"] = fallbackUserId;
  }
  return headers;
}

function isFirebaseUnauthorizedDomainError(error) {
  return String(error?.code || error?.message || "").includes("auth/unauthorized-domain");
}

function localFirebaseAuthUrl() {
  if (window.location.protocol !== "http:") {
    return "";
  }
  if (!["127.0.0.1", "0.0.0.0"].includes(window.location.hostname)) {
    return "";
  }
  const url = new URL(window.location.href);
  url.hostname = "localhost";
  return url.toString();
}

function redirectToLocalhostForFirebaseAuth() {
  const targetUrl = localFirebaseAuthUrl();
  if (!targetUrl) {
    return false;
  }
  if (authHelper) {
    authHelper.textContent = "Google Sign-In works best from localhost in local development. Redirecting...";
  }
  window.location.replace(targetUrl);
  return true;
}

function friendlyFirebaseAuthError(error) {
  if (!isFirebaseUnauthorizedDomainError(error)) {
    return `Google Sign-In failed: ${error.message}`;
  }
  const blockedHost = window.location.hostname || "this domain";
  return `Google Sign-In is blocked because Firebase has not authorized ${blockedHost}. Open the app from localhost for local development, or add ${blockedHost} in Firebase Authentication > Settings > Authorized domains.`;
}

async function createServerSession(idToken) {
  setIdToken(idToken);
  const response = await fetch("/api/auth/session", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
    },
    body: JSON.stringify({ idToken }),
  });
  const data = await parseApiResponse(response);
  if (!response.ok || data.status !== "success") {
    throw new Error(data.error || "Could not create a secure sign-in session.");
  }
  applySession(data);
  shouldClearServerSessionOnFirebaseSignOut = true;
  return data;
}

async function logoutServerSession() {
  isLoggingOutServerSession = true;
  try {
    const response = await fetch("/api/auth/logout", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ resetIdentity: true, resetSession: true }),
    });
    const data = await parseApiResponse(response);
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || "Could not end the secure sign-in session.");
    }
    applySession(data);
    shouldClearServerSessionOnFirebaseSignOut = false;
    setIdToken("");
    return data;
  } finally {
    isLoggingOutServerSession = false;
  }
}

async function bootstrapAuth() {
  try {
    const response = await fetch("/api/config");
    const config = await response.json();
    authMode = config.authMode || "email_fallback";

    if (!config.firebase) {
      updateAuthPill("Guest sessions enabled", true);
      googleSigninButton.disabled = true;
      googleSigninButton.textContent = "Firebase Auth not configured";
      usernameInput.hidden = false;
      if (usernameSubmit) {
        usernameSubmit.textContent = "Continue with email or guest";
      }
      authHelper.textContent =
        "Add Firebase web config env vars to enable Google Sign-In. Until then, each browser keeps its own guest session.";
      return;
    }

    if (redirectToLocalhostForFirebaseAuth()) {
      return;
    }

    usernameInput.hidden = true;
    usernameInput.value = "";
    if (usernameSubmit) {
      usernameSubmit.textContent = "Continue as private guest";
    }
    authHelper.textContent =
      "Use Continue with Google to connect your learner account. Private guest sessions cannot use Google saves.";

    const app = initializeApp(config.firebase);
    firebaseAuthClient = getAuth(app);
    googleProvider = new GoogleAuthProvider();
    googleProvider.setCustomParameters({ prompt: "select_account" });
    googleSavesProvider = new GoogleAuthProvider();
    googleSavesScopes.forEach((scope) => googleSavesProvider.addScope(scope));
    googleSavesProvider.setCustomParameters({ prompt: "select_account consent" });

    onAuthStateChanged(firebaseAuthClient, async (user) => {
      if (!user) {
        const shouldLogoutServerSession =
          shouldClearServerSessionOnFirebaseSignOut && !isLoggingOutServerSession;
        if (shouldLogoutServerSession) {
          try {
            await logoutServerSession();
          } catch (error) {
            console.error("Could not clear server session after Firebase sign-out.", error);
          }
        }
        shouldClearServerSessionOnFirebaseSignOut = false;
        setIdToken("");
        updateAuthPill(activeSession.displayName || "Guest session", true);
        return;
      }

      shouldClearServerSessionOnFirebaseSignOut = true;
      const idToken = await user.getIdToken();
      await createServerSession(idToken);
      closeUsernameModal();
      updateAuthPill(user.email || activeSession.displayName || "Signed in", false);
      await refreshLearnerState();
      await refreshMasteryBoard();
      await refreshRoadmap();
      await refreshMaterials();
      await refreshInsights();
    });

    updateAuthPill("Google Sign-In ready", true);
  } catch (error) {
    updateAuthPill("Auth setup failed", true);
    authHelper.textContent = friendlyFirebaseAuthError(error).replace("Google Sign-In failed", "Firebase Auth could not start");
  }
}

async function submitRoadmapRequest({ forceRebuild = false, revisionReason = "" } = {}) {
  const username = ensureIdentity();
  if (!username) {
    return;
  }

  const topic = roadmapTopicInput.value.trim() || diagnosticTopicInput.value.trim();
  if (!topic) {
    if (roadmapHomeStatus) {
      roadmapHomeStatus.textContent = "Add a topic first.";
    }
    roadmapStatus.textContent = "Add a topic first.";
    roadmapTopicInput.focus();
    return;
  }

  if (roadmapHomeStatus) {
    roadmapHomeStatus.textContent = "Opening roadmap workspace...";
  }
  showPlanWorkspace("roadmap");
  roadmapWorkspace?.classList.remove("showing-previous-roadmaps");
  savedRoadmapsPanel?.classList.add("hidden");
  roadmapStatus.textContent = forceRebuild ? "Rebuilding your roadmap..." : "Creating your roadmap...";
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
      availableTime: getTimeInMinutes(roadmapTimeInput, roadmapTimeUnitSelect)
        || getTimeInMinutes(diagnosticTimeInput, diagnosticTimeUnitSelect),
      deadlineDays: roadmapDeadlineInput.value ? Number(roadmapDeadlineInput.value) : 14,
      startDate: roadmapStartDateInput?.value || "",
      saveToCalendar: Boolean(roadmapCalendarSyncInput?.checked),
      calendarStartTime: roadmapCalendarStartTimeInput?.value || "09:00",
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
      level: roadmapLevelSelect?.value || diagnosticLevelSelect.value,
      forceRebuild,
      revisionReason,
    }),
  });
  const data = await response.json();
  if (!response.ok || data.status !== "success") {
    throw new Error(data.error || data.message || "Could not generate roadmap.");
  }
  currentRoadmapDetailsExpanded = false;
  renderRoadmap(data);
  await refreshSavedRoadmaps();
  roadmapStatus.textContent = data.calendar?.message || "Current roadmap ready.";
  if (data.calendar?.status === "auth_required") {
    handleGoogleSaveAuthRequired(data.calendar.message, roadmapStatus);
  }
  if (roadmapHomeStatus) {
    roadmapHomeStatus.textContent = data.calendar?.message || "Roadmap ready. Use View roadmap anytime.";
  }
  await refreshLearnerState();
  await refreshInsights();
}

async function deleteCurrentRoadmap() {
  const username = ensureIdentity();
  if (!username) {
    return;
  }
  if (!activeRoadmap) {
    roadmapStatus.textContent = "No roadmap to delete.";
    return;
  }

  deleteRoadmapButton.disabled = true;
  roadmapStatus.textContent = "Deleting roadmap...";
  const response = await fetch("/api/roadmap/delete", {
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
    throw new Error(data.error || data.message || "Could not delete roadmap.");
  }

  selectedRoadmapSessionKey = "";
  renderRoadmap(null);
  await refreshSavedRoadmaps();
  showPlanWorkspace("home");
  roadmapStatus.textContent = data.message || "Roadmap deleted.";
  if (roadmapHomeStatus) {
    roadmapHomeStatus.textContent = "Roadmap deleted. Create a new one when ready.";
  }
  await refreshLearnerState();
  await refreshInsights();
}

function buildCalendarTimes(startValue, durationMinutes = 45) {
  if (!startValue) {
    return null;
  }
  const start = new Date(startValue);
  if (Number.isNaN(start.getTime())) {
    return null;
  }
  const minutes = Number(durationMinutes) || 45;
  const end = new Date(start.getTime() + minutes * 60 * 1000);
  return {
    startTime: start.toISOString(),
    endTime: end.toISOString(),
  };
}

function todayDateInputValue() {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60 * 1000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

function setupRoadmapDateControls() {
  if (roadmapStartDateInput) {
    const today = todayDateInputValue();
    roadmapStartDateInput.min = today;
    if (!roadmapStartDateInput.value) {
      roadmapStartDateInput.value = today;
    }
  }
  setupRoadmapTimePicker();
}

function setupRoadmapTimePicker() {
  if (!roadmapCalendarStartTimeInput || !roadmapCalendarTimeInput || !roadmapCalendarTimeOptions || !roadmapCalendarPeriodSelect) {
    if (roadmapCalendarStartTimeInput && !roadmapCalendarStartTimeInput.value) {
      roadmapCalendarStartTimeInput.value = "09:00";
    }
    return;
  }

  const timeOptions = [];
  for (let hour = 1; hour <= 12; hour += 1) {
    for (let minute = 0; minute < 60; minute += 15) {
      timeOptions.push(`${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`);
    }
  }

  const parseTimeText = (value) => {
    const raw = String(value || "").trim().replace(/\s+/g, "");
    const compact = raw.match(/^(\d{1,2})(\d{2})$/);
    const colon = raw.match(/^(\d{1,2})(?::(\d{1,2}))?$/);
    const match = compact || colon;
    if (!match) {
      return null;
    }
    const hour = Number(match[1]);
    const minute = Number(match[2] ?? 0);
    if (!Number.isInteger(hour) || !Number.isInteger(minute) || hour < 1 || hour > 12 || minute < 0 || minute > 59) {
      return null;
    }
    return {
      hour,
      minute,
      label: `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`,
    };
  };

  const syncHiddenValue = ({ normalizeInput = false } = {}) => {
    const parsed = parseTimeText(roadmapCalendarTimeInput.value);
    if (!parsed) {
      return false;
    }
    const period = roadmapCalendarPeriodSelect.value === "PM" ? "PM" : "AM";
    let hour24 = parsed.hour % 12;
    if (period === "PM") {
      hour24 += 12;
    }
    roadmapCalendarStartTimeInput.value = `${String(hour24).padStart(2, "0")}:${String(parsed.minute).padStart(2, "0")}`;
    if (normalizeInput) {
      roadmapCalendarTimeInput.value = parsed.label;
    }
    return true;
  };

  const hideOptions = () => {
    roadmapCalendarTimeOptions.classList.add("hidden");
    roadmapCalendarTimeInput.setAttribute("aria-expanded", "false");
  };

  const showOptions = () => {
    const query = String(roadmapCalendarTimeInput.value || "").trim();
    const filtered = timeOptions.filter((value) => (
      value.startsWith(query) || value.replace(/^0/, "").startsWith(query)
    )).slice(0, 12);
    const visibleOptions = filtered.length ? filtered : timeOptions.slice(0, 12);
    roadmapCalendarTimeOptions.innerHTML = "";
    visibleOptions.forEach((value) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "roadmap-time-option";
      button.textContent = value;
      button.setAttribute("role", "option");
      button.addEventListener("mousedown", (event) => {
        event.preventDefault();
        roadmapCalendarTimeInput.value = value;
        syncHiddenValue({ normalizeInput: true });
        hideOptions();
      });
      roadmapCalendarTimeOptions.appendChild(button);
    });
    roadmapCalendarTimeOptions.classList.remove("hidden");
    roadmapCalendarTimeInput.setAttribute("aria-expanded", "true");
  };

  const currentValue = String(roadmapCalendarStartTimeInput.value || "09:00").slice(0, 5);
  const [currentHourText, currentMinuteText] = currentValue.split(":");
  const currentHour = Math.max(0, Math.min(23, Number(currentHourText) || 9));
  const currentMinute = Math.max(0, Math.min(59, Number(currentMinuteText) || 0));
  const currentPeriod = currentHour >= 12 ? "PM" : "AM";
  const currentHour12 = currentHour % 12 || 12;
  roadmapCalendarTimeInput.value = `${String(currentHour12).padStart(2, "0")}:${String(currentMinute).padStart(2, "0")}`;
  roadmapCalendarPeriodSelect.value = currentPeriod;
  syncHiddenValue({ normalizeInput: true });

  roadmapCalendarTimeInput.addEventListener("focus", showOptions);
  roadmapCalendarTimeInput.addEventListener("input", () => {
    syncHiddenValue();
    showOptions();
  });
  roadmapCalendarTimeInput.addEventListener("blur", () => {
    if (!syncHiddenValue({ normalizeInput: true })) {
      roadmapCalendarTimeInput.value = "09:00";
      roadmapCalendarPeriodSelect.value = "AM";
      roadmapCalendarStartTimeInput.value = "09:00";
    }
    window.setTimeout(hideOptions, 120);
  });
  roadmapCalendarPeriodSelect.addEventListener("change", () => {
    syncHiddenValue({ normalizeInput: true });
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".roadmap-time-picker")) {
      hideOptions();
    }
  });
}

async function saveRoadmapToGoogleTasks() {
  const username = ensureIdentity();
  if (!username) {
    return;
  }
  if (!activeRoadmap) {
    roadmapStatus.textContent = "Create a roadmap first.";
    return;
  }

  saveRoadmapTasksButton.disabled = true;
  const oldText = saveRoadmapTasksButton.textContent;
  saveRoadmapTasksButton.textContent = "Saving...";
  roadmapStatus.textContent = "Saving roadmap sessions to Google Tasks...";
  try {
    const response = await fetch("/api/roadmap/save-google-tasks", {
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
    if (!response.ok || !["success", "auth_required"].includes(data.status)) {
      throw new Error(data.error || data.message || "Could not save roadmap tasks.");
    }
    if (data.status === "auth_required") {
      handleGoogleSaveAuthRequired(data.message, roadmapStatus);
      return;
    }
    roadmapStatus.textContent = data.message || "Roadmap saved to Google Tasks.";
  } catch (error) {
    roadmapStatus.textContent = error.message;
  } finally {
    saveRoadmapTasksButton.disabled = false;
    saveRoadmapTasksButton.textContent = oldText;
  }
}

async function saveRoadmapSessionToCalendar(button) {
  const username = ensureIdentity();
  if (!username) {
    return;
  }
  const panel = button.closest(".roadmap-calendar-panel");
  const startInput = panel?.querySelector("[data-calendar-start]");
  const times = buildCalendarTimes(startInput?.value, button.dataset.sessionDuration);
  if (!times) {
    roadmapStatus.textContent = "Choose a date and time first.";
    startInput?.focus();
    return;
  }

  button.disabled = true;
  const oldText = button.textContent;
  button.textContent = "Saving...";
  roadmapStatus.textContent = "Saving study session to Google Calendar...";
  try {
    const response = await fetch("/api/roadmap/session/save-calendar", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: username,
        idToken: getIdToken(),
        title: button.dataset.sessionTitle || "Roadmap study session",
        focus: button.dataset.sessionFocus || "",
        phaseTitle: button.dataset.phaseTitle || "",
        phaseGoal: button.dataset.phaseGoal || "",
        startTime: times.startTime,
        endTime: times.endTime,
      }),
    });
    const data = await response.json();
    if (!response.ok || !["success", "auth_required"].includes(data.status)) {
      throw new Error(data.error || data.message || "Could not save calendar event.");
    }
    if (data.status === "auth_required") {
      handleGoogleSaveAuthRequired(data.message, roadmapStatus);
      return;
    }
    roadmapStatus.textContent = data.message || "Study session saved to Google Calendar.";
  } catch (error) {
    roadmapStatus.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = oldText;
  }
}

async function saveSavedRoadmapSessionReminder(button) {
  const username = ensureIdentity();
  if (!username) {
    return;
  }
  const dueDate = String(button.dataset.sessionDue || "").trim();
  if (!dueDate) {
    roadmapStatus.textContent = "This session needs a due date before ArkAI can set a reminder.";
    return;
  }
  const reminderStart = new Date(`${dueDate}T09:00:00`);
  if (Number.isNaN(reminderStart.getTime())) {
    roadmapStatus.textContent = "Could not read that session due date.";
    return;
  }
  const durationMinutes = Number(button.dataset.sessionDuration || 45) || 45;
  const reminderEnd = new Date(reminderStart.getTime() + durationMinutes * 60 * 1000);

  button.disabled = true;
  const oldText = button.textContent;
  button.textContent = "Saving...";
  roadmapStatus.textContent = "Saving study reminder to Google Calendar...";
  try {
    const response = await fetch("/api/roadmap/session/save-calendar", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        userId: username,
        idToken: getIdToken(),
        title: button.dataset.sessionTitle || "Roadmap study session",
        focus: button.dataset.sessionFocus || "",
        phaseTitle: button.dataset.phaseTitle || "",
        phaseGoal: button.dataset.phaseGoal || "",
        startTime: reminderStart.toISOString(),
        endTime: reminderEnd.toISOString(),
      }),
    });
    const data = await response.json();
    if (!response.ok || !["success", "auth_required"].includes(data.status)) {
      throw new Error(data.error || data.message || "Could not save reminder.");
    }
    if (data.status === "auth_required") {
      handleGoogleSaveAuthRequired(data.message, roadmapStatus);
      return;
    }
    roadmapStatus.textContent = data.message || "Study reminder saved to Google Calendar.";
  } catch (error) {
    roadmapStatus.textContent = error.message || "Could not save reminder.";
  } finally {
    button.disabled = false;
    button.textContent = oldText;
  }
}

async function readFileAsDataUrl(file) {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read file."));
    reader.readAsDataURL(file);
  });
}

function validateTutorAttachmentFile(file) {
  const baseError = validateSelectedFile(file, { fieldLabel: "Tutor attachment" });
  if (baseError) {
    return baseError;
  }
  const lowerName = String(file?.name || "").toLowerCase();
  const supported = [".txt", ".md", ".csv", ".json", ".html", ".css", ".js", ".py"]
    .some((suffix) => lowerName.endsWith(suffix));
  const mime = String(file?.type || "");
  if (!supported && !mime.startsWith("text/")) {
    return "Tutor attachments currently support text, notes, code, CSV, JSON, HTML, CSS, JS, and Python files.";
  }
  return null;
}

function getTutorAttachmentTotalBytes(items = pendingTutorAttachments) {
  return items.reduce((total, item) => total + Number(item.file?.size || 0), 0);
}

function renderTutorAttachments() {
  if (!tutorAttachmentsTray) {
    return;
  }
  tutorAttachmentsTray.innerHTML = "";
  tutorAttachmentsTray.classList.toggle("hidden", pendingTutorAttachments.length === 0);
  for (const attachment of pendingTutorAttachments) {
    const chip = document.createElement("div");
    chip.className = "tutor-attachment-chip";

    const label = document.createElement("span");
    label.textContent = `${attachment.file.name}${formatFileSize(attachment.file.size) ? ` - ${formatFileSize(attachment.file.size)}` : ""}`;
    chip.appendChild(label);

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.setAttribute("aria-label", `Remove ${attachment.file.name}`);
    removeButton.dataset.removeTutorAttachment = attachment.id;
    removeButton.textContent = "Remove";
    chip.appendChild(removeButton);

    tutorAttachmentsTray.appendChild(chip);
  }
}

function addTutorAttachments(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) {
    return;
  }

  const nextAttachments = [...pendingTutorAttachments];
  for (const file of files) {
    if (nextAttachments.length >= maxTutorAttachmentCount) {
      setVoiceStatus(`Attach up to ${maxTutorAttachmentCount} files per Tutor message.`);
      break;
    }
    const validationError = validateTutorAttachmentFile(file);
    if (validationError) {
      setVoiceStatus(validationError);
      continue;
    }
    if (getTutorAttachmentTotalBytes(nextAttachments) + Number(file.size || 0) > maxTutorAttachmentTotalBytes) {
      setVoiceStatus(`Keep Tutor attachments under ${formatFileSize(maxTutorAttachmentTotalBytes)} total.`);
      continue;
    }
    nextAttachments.push({
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      file,
    });
  }

  pendingTutorAttachments = nextAttachments;
  renderTutorAttachments();
}

function clearTutorAttachments() {
  pendingTutorAttachments = [];
  if (tutorAttachmentInput) {
    tutorAttachmentInput.value = "";
  }
  renderTutorAttachments();
}

async function buildTemporaryAttachmentPayloads() {
  const payloads = [];
  for (const attachment of pendingTutorAttachments) {
    const file = attachment.file;
    payloads.push({
      name: file.name,
      mimeType: file.type || "text/plain",
      sizeBytes: Number(file.size || 0),
      dataBase64: await readFileAsDataUrl(file),
    });
  }
  return payloads;
}

async function readFileAsText(file) {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read file."));
    reader.readAsText(file);
  });
}

if (newSessionButton) {
  newSessionButton.addEventListener("click", async () => {
    await clearSessionState();
  });
}

promptInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey) {
    return;
  }

  event.preventDefault();
  submitButton.click();
});

promptInput.addEventListener("input", () => {
  autoresizePrompt();
});

messages.addEventListener("click", async (event) => {
  const codeCopyButton = event.target.closest("[data-copy-code]");
  if (codeCopyButton) {
    try {
      await copyTextToClipboard(codeCopyButton.dataset.copyCode || "");
      codeCopyButton.classList.add("is-copied");
      codeCopyButton.setAttribute("aria-label", "Copied");
      codeCopyButton.title = "Copied";
      setTimeout(() => {
        codeCopyButton.classList.remove("is-copied");
        codeCopyButton.setAttribute("aria-label", "Copy code");
        codeCopyButton.title = "Copy code";
      }, 1200);
    } catch {
      codeCopyButton.setAttribute("aria-label", "Copy failed");
      codeCopyButton.title = "Copy failed";
    }
    return;
  }

  const copyButton = event.target.closest("[data-copy-message]");
  if (copyButton) {
    try {
      await copyTextToClipboard(copyButton.dataset.copyMessage || "");
      copyButton.classList.add("is-copied");
      copyButton.setAttribute("aria-label", "Copied");
      copyButton.title = "Copied";
      setTimeout(() => {
        copyButton.classList.remove("is-copied");
        copyButton.setAttribute("aria-label", "Copy message");
        copyButton.title = "Copy message";
      }, 1200);
    } catch {
      copyButton.setAttribute("aria-label", "Copy failed");
      copyButton.title = "Copy failed";
    }
    return;
  }

  const starterButton = event.target.closest("[data-starter-prompt]");
  if (!starterButton) {
    return;
  }
  promptInput.value = starterButton.textContent.replace(/\s+/g, " ").trim() || starterButton.dataset.starterPrompt || "";
  autoresizePrompt();
  promptInput.focus();
  promptInput.setSelectionRange(promptInput.value.length, promptInput.value.length);
});

if (authPill) {
  authPill.addEventListener("click", () => {
    toggleProfileDropdown();
  });
}

if (headerChangeAccount) {
  headerChangeAccount.addEventListener("click", async () => {
    await openAccountSwitcher();
  });
}

if (showHistoryButton) {
  showHistoryButton.addEventListener("click", async () => {
    await openHistoryModal();
  });
}

if (closeHistoryButton) {
  closeHistoryButton.addEventListener("click", () => {
    closeHistoryModal();
  });
}

if (historyModal) {
  historyModal.addEventListener("click", (event) => {
    if (event.target === historyModal) {
      closeHistoryModal();
    }
  });
}

if (historyListModal) {
  historyListModal.addEventListener("click", async (event) => {
    const deleteAllButton = event.target.closest("[data-chat-session-delete-all]");
    if (deleteAllButton) {
      try {
        await deleteAllChatSessionsFromHistory();
        await openHistoryModal();
      } catch (error) {
        setVoiceStatus(error.message || "Could not delete saved chats.");
      }
      return;
    }

    const deleteButton = event.target.closest("[data-chat-session-delete]");
    if (deleteButton) {
      try {
        await deleteChatSessionFromHistory(deleteButton.dataset.chatSessionDelete || "");
        await openHistoryModal();
      } catch (error) {
        setVoiceStatus(error.message || "Could not delete saved chat.");
      }
      return;
    }

    const openButton = event.target.closest("[data-chat-session-open]");
    if (!openButton) {
      return;
    }

    try {
      await loadChatSession(openButton.dataset.chatSessionOpen || "");
    } catch (error) {
      setVoiceStatus(error.message || "Could not open saved chat.");
    }
  });
}

if (shareChatButton) {
  shareChatButton.addEventListener("click", async () => {
    const transcript = buildShareTranscript();
    if (!transcript) {
      setVoiceStatus("No chat history to share yet.");
      return;
    }

    try {
      if (navigator.share) {
        await navigator.share({
          title: "ARKAI session",
          text: transcript,
        });
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(transcript);
      } else {
        throw new Error("Sharing is not available in this browser.");
      }
      setVoiceStatus("Chat transcript ready to share.");
    } catch (error) {
      setVoiceStatus(error.message || "Could not share this chat yet.");
    }
  });
}

document.addEventListener("click", (event) => {
  if (!profileDropdown || !authPill) {
    return;
  }
  if (profileDropdown.contains(event.target) || authPill.contains(event.target)) {
    return;
  }
  closeProfileDropdown();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeProfileDropdown();
    closeHistoryModal();
  }
});

googleSigninButton.addEventListener("click", async () => {
  if (!firebaseAuthClient || !googleProvider) {
    openUsernameModal(true);
    return;
  }

  try {
    const result = await signInWithPopup(firebaseAuthClient, googleProvider);
    if (result?.user) {
      const idToken = await result.user.getIdToken();
      await createServerSession(idToken);
      closeUsernameModal();
      updateAuthPill(result.user.email || activeSession.displayName || "Signed in", false);
      const status = await refreshGoogleSavesStatus();
      if (!status.connected && authHelper) {
        authHelper.textContent = "Signed in. Use Connect under Google saves when you want Docs, Tasks, and Calendar saves.";
      }
    }
    promptInput.focus();
  } catch (error) {
    if (isFirebaseUnauthorizedDomainError(error) && redirectToLocalhostForFirebaseAuth()) {
      return;
    }
    authHelper.textContent = friendlyFirebaseAuthError(error);
  }
});

usernameForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  usernameInput.setCustomValidity("");
  const fallbackUserId = sanitizeUsername(usernameInput.value || "");
  const useNamedFallback = Boolean(fallbackUserId);
  if (useNamedFallback && authMode === "firebase") {
    usernameInput.setCustomValidity("Use Continue with Google to sign in, or leave this empty for a private guest session.");
    usernameInput.reportValidity();
    return;
  }
  if (useNamedFallback && !isValidEmail(fallbackUserId)) {
    usernameInput.setCustomValidity("Use an email address, or leave this empty for a private guest session.");
    usernameInput.reportValidity();
    return;
  }
  if (useNamedFallback) {
    setFallbackUserId(fallbackUserId);
  } else {
    setFallbackUserId("");
  }
  await refreshSession({
    resetIdentity: true,
    resetSession: true,
    userId: useNamedFallback ? fallbackUserId : "",
  });
  setIdToken("");
  updateAuthPill(activeSession.displayName || (useNamedFallback ? fallbackUserId : "Guest session"), true);
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

function isRoadmapStatusCreateAction() {
  return /^create your roadmap\.?$/i.test(String(roadmapStatus?.textContent || "").trim());
}

function triggerRoadmapStatusCreate() {
  if (!isRoadmapStatusCreateAction()) {
    return;
  }
  generateRoadmapButton?.click();
}

if (roadmapStatus) {
  roadmapStatus.addEventListener("click", triggerRoadmapStatusCreate);
  roadmapStatus.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    event.preventDefault();
    triggerRoadmapStatusCreate();
  });
}

rebuildRoadmapButton?.addEventListener("click", async () => {
  setActiveView("plan");
  try {
    await submitRoadmapRequest({ forceRebuild: true, revisionReason: "manual recovery rebuild" });
  } catch (error) {
    roadmapStatus.textContent = error.message;
  }
});

if (viewRoadmapButton) {
  viewRoadmapButton.addEventListener("click", () => {
    setActiveView("plan");
    showPlanWorkspace("roadmap");
    savedRoadmapsPanel?.classList.add("hidden");
    roadmapWorkspace?.classList.remove("showing-previous-roadmaps");
    roadmapWorkspace?.scrollTo({ top: 0, behavior: "smooth" });
  });
}

if (previousRoadmapsButton) {
  previousRoadmapsButton.addEventListener("click", async () => {
    setActiveView("plan");
    showPlanWorkspace("roadmap");
    await refreshSavedRoadmaps({ showPanel: true });
  });
}

closeSavedRoadmapsButton?.addEventListener("click", () => {
  selectedSavedRoadmapId = "";
  savedRoadmapsPanel?.classList.add("hidden");
  roadmapWorkspace?.classList.remove("showing-previous-roadmaps");
  roadmapWorkspace?.scrollTo({ top: 0, behavior: "smooth" });
});

deleteAllSavedRoadmapsButton?.addEventListener("click", async () => {
  try {
    await deleteAllSavedRoadmaps();
  } catch (error) {
    if (roadmapStatus) {
      roadmapStatus.textContent = error.message || "Could not delete saved roadmaps.";
    }
  }
});

savedRoadmapsList?.addEventListener("click", async (event) => {
  const backButton = event.target.closest("[data-back-to-saved-roadmaps]");
  if (backButton) {
    selectedSavedRoadmapId = "";
    renderSavedRoadmaps();
    return;
  }

  const viewButton = event.target.closest("[data-view-saved-roadmap]");
  if (viewButton) {
    selectedSavedRoadmapId = viewButton.dataset.viewSavedRoadmap || "";
    renderSavedRoadmaps();
    savedRoadmapsPanel?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  const openSavedSessionButton = event.target.closest("[data-open-saved-session]");
  if (openSavedSessionButton) {
    openRoadmapSession({
      title: openSavedSessionButton.dataset.sessionTitle,
      focus: openSavedSessionButton.dataset.sessionFocus,
      duration_minutes: openSavedSessionButton.dataset.sessionDuration,
      phaseTitle: openSavedSessionButton.dataset.phaseTitle,
      phaseGoal: openSavedSessionButton.dataset.phaseGoal,
    });
    return;
  }

  const statusButton = event.target.closest("[data-saved-session-status]");
  if (statusButton) {
    await updateSavedRoadmapSessionStatus(statusButton);
    return;
  }

  const reminderButton = event.target.closest("[data-remind-saved-session]");
  if (reminderButton) {
    await saveSavedRoadmapSessionReminder(reminderButton);
    return;
  }

  const deleteButton = event.target.closest("[data-delete-saved-roadmap]");
  if (!deleteButton) {
    return;
  }
  try {
    await deleteSavedRoadmap(deleteButton.dataset.deleteSavedRoadmap);
  } catch (error) {
    if (roadmapStatus) {
      roadmapStatus.textContent = error.message || "Could not remove saved roadmap.";
    }
  }
});

if (sideProgressAction) {
  sideProgressAction.addEventListener("click", () => {
    setActiveView("plan");
    showPlanWorkspace(getContinueLearningSnapshot().hasRoadmap ? "roadmap" : "home");
  });
}

if (sidebarToggleButton) {
  sidebarToggleButton.addEventListener("click", () => {
    setSidebarCollapsed(!document.body.classList.contains("sidebar-collapsed"));
  });
}

if (deleteRoadmapButton) {
  deleteRoadmapButton.addEventListener("click", async () => {
    const confirmed = window.confirm("Delete your current roadmap? This removes the saved roadmap for this account.");
    if (!confirmed) {
      return;
    }
    try {
      await deleteCurrentRoadmap();
    } catch (error) {
      roadmapStatus.textContent = error.message;
    } finally {
      if (deleteRoadmapButton && activeRoadmap) {
        deleteRoadmapButton.disabled = false;
      }
    }
  });
}

document.querySelectorAll("[data-plan-back]").forEach((button) => {
  button.addEventListener("click", () => {
    showPlanWorkspace("home");
  });
});

refreshInsightsButton?.addEventListener("click", async () => {
  setActiveView("insights");
  await refreshInsights();
});

generateReportButton.addEventListener("click", async () => {
  setActiveView("insights");
  showInsightsWorkspace("report");
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

document.querySelectorAll("[data-insights-back]").forEach((button) => {
  button.addEventListener("click", () => {
    showInsightsWorkspace("home");
  });
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
      handleGoogleSaveAuthRequired(data.message, statusNode);
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

uploadMaterialButton.addEventListener("click", async () => {
  setActiveView("materials");
  const username = ensureIdentity();
  if (!username) {
    return;
  }

  const file = materialFileInput.files?.[0] || null;
  const incomingBytes = Number(file?.size || 0);
  const fileValidationError = validateSelectedFile(file, { fieldLabel: "Uploaded file" });
  if (fileValidationError) {
    materialsStatus.textContent = fileValidationError;
    return;
  }
  if (!file) {
    materialsStatus.textContent = "Choose a file first.";
    return;
  }
  if (getCurrentLibraryUsageBytes() + incomingBytes > maxMaterialLibrarySizeBytes) {
    materialsStatus.textContent = `Library is full. Keep total materials under ${formatFileSize(maxMaterialLibrarySizeBytes)}.`;
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
        name: file.name,
        mimeType: file.type || "application/octet-stream",
        dataBase64,
        pastedText: "",
      }),
    });
    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.error || data.message || "Could not upload material.");
    }
    materialsStatus.textContent = `${data.material.name} is ready.`;
    materialFileInput.value = "";
    const dropZoneTitle = document.querySelector("#drop-zone .drop-zone-title");
    if (dropZoneTitle) {
      dropZoneTitle.textContent = "Drop file or browse";
    }
    updateUploadMaterialButtonState();
    await refreshMaterials();
    await refreshInsights();
  } catch (error) {
    materialsStatus.textContent = error.message;
  } finally {
    updateUploadMaterialButtonState();
  }
});

materialFileInput.addEventListener("change", () => {
  updateUploadMaterialButtonState();
});

if (askMaterialsButton) {
  askMaterialsButton.addEventListener("click", async () => {
    setActiveView("materials");
    const username = ensureIdentity();
    if (!username) {
      return;
    }

    const query = materialQueryInput?.value?.trim() || promptInput.value.trim();
    if (!query) {
      materialsStatus.textContent = "Type one question first.";
      materialQueryInput?.focus();
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
}

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
  const sampleStyleValidationError = validateSelectedFile(sampleStyleFile, { fieldLabel: "Sample exam file" });
  if (sampleStyleValidationError) {
    materialsStatus.textContent = sampleStyleValidationError;
    return;
  }
  createMaterialsMockTestButton.disabled = true;
  materialsStatus.textContent = "Creating mock test from your material...";
  try {
    const sampleStyleFileDataBase64 = sampleStyleFile ? await readFileAsDataUrl(sampleStyleFile) : "";
    const sampleStylePayload = [
      materialsMockStyleInput?.value?.trim() || "",
      sampleStyleFile ? `Uploaded sample exam: ${sampleStyleFile.name}` : "",
    ].filter(Boolean).join("\n\n");
    const structureText = materialsMockStructureInput.value.trim();

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
        topic: materialQueryInput?.value?.trim() || latestMaterials.find((material) => selectedMaterialIds.has(material.material_id))?.name || "Uploaded materials",
        level: diagnosticLevelSelect.value,
        goal: "Practice from uploaded materials",
        questionCount: parseMockQuestionCount(structureText, 5),
        structure: structureText,
        sampleStyle: sampleStylePayload,
        sampleStyleFileName: sampleStyleFile?.name || "",
        sampleStyleFileMimeType: sampleStyleFile?.type || "",
        sampleStyleFileDataBase64,
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
    showPlanWorkspace("diagnostic");
    assessmentStatus.textContent = "Mock test ready from your materials. Submit it, save it to Google Docs, or download it from Materials.";
    materialsStatus.textContent = "Mock test ready. Download it when you are ready.";
    materialsMockStyleFileInput.value = "";
    setActiveView("plan");
    setActiveNavigation("materials");
  } catch (error) {
    materialsStatus.textContent = error.message;
  } finally {
    createMaterialsMockTestButton.disabled = false;
  }
});

materialsMockBackButton?.addEventListener("click", () => {
  setActiveView("materials");
  showPlanWorkspace("home");
  materialsStatus.textContent = activeAssessment?.assessment_type === "mock_test"
    ? "Mock test is ready. Download it when you are ready."
    : "Upload notes, then create a mock test.";
});

downloadMaterialsMockTestButton?.addEventListener("click", () => {
  downloadActiveAssessmentPdf();
});

startDiagnosticButton.addEventListener("click", async () => {
  setActiveView("plan");
  const username = ensureIdentity();
  if (!username) {
    return;
  }

  const topic = diagnosticTopicInput.value.trim() || roadmapTopicInput.value.trim();
  if (!topic) {
    if (diagnosticHomeStatus) {
      diagnosticHomeStatus.textContent = "Choose a topic first.";
    }
    assessmentStatus.textContent = "Choose a topic first so the diagnostic can be personalized.";
    roadmapTopicInput.focus();
    return;
  }
  diagnosticTopicInput.value = topic;
  if (!diagnosticGoalInput.value.trim() && roadmapGoalInput.value.trim()) {
    diagnosticGoalInput.value = roadmapGoalInput.value.trim();
  }
  if (!diagnosticTimeInput.value && roadmapTimeInput.value) {
    diagnosticTimeInput.value = roadmapTimeInput.value;
    diagnosticTimeUnitSelect.value = roadmapTimeUnitSelect.value;
  }

  startDiagnosticButton.disabled = true;
  if (diagnosticHomeStatus) {
    diagnosticHomeStatus.textContent = "Opening diagnostic workspace...";
  }
  showPlanWorkspace("diagnostic");
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
        availableTime: getTimeInMinutes(diagnosticTimeInput, diagnosticTimeUnitSelect),
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
    if (diagnosticHomeStatus) {
      diagnosticHomeStatus.textContent = "Diagnostic ready in the focused workspace.";
    }
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
  const toggleCurrentRoadmapButton = event.target.closest("[data-toggle-current-roadmap]");
  if (toggleCurrentRoadmapButton) {
    currentRoadmapDetailsExpanded = !currentRoadmapDetailsExpanded;
    renderRoadmap({ roadmap: activeRoadmap, summary: activeRoadmapSummary });
    if (currentRoadmapDetailsExpanded) {
      document.getElementById("current-roadmap-details")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    return;
  }

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
  const calendarButton = event.target.closest("[data-save-calendar-session]");
  if (calendarButton) {
    saveRoadmapSessionToCalendar(calendarButton);
    return;
  }

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

saveRoadmapTasksButton?.addEventListener("click", () => {
  saveRoadmapToGoogleTasks();
});

connectGoogleSavesButton?.addEventListener("click", () => {
  connectGoogleSaves({ askFirst: true, forceReconnect: googleSavesConnected });
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

focusTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    setActiveView(tab.dataset.viewTarget);
    if (tab.dataset.viewTarget === "plan") {
      showPlanWorkspace("home");
    }
    if (tab.dataset.viewTarget === "insights") {
      showInsightsWorkspace("home");
    }
  });
});

setupTimeControl(diagnosticTimeInput, diagnosticTimeUnitSelect);
setupTimeControl(roadmapTimeInput, roadmapTimeUnitSelect);
setupRoadmapDateControls();

if (voiceInputButton) {
  voiceInputButton.addEventListener("click", () => {
    if (!speechRecognition) {
      setVoiceStatus("Voice recognition is not available in this browser.");
      return;
    }
    if (isListening) {
      speechRecognition.stop();
      return;
    }
    speechRecognition.start();
  });
}

if (voiceReplyButton) {
  voiceReplyButton.addEventListener("click", () => {
    if (!lastAgentReply) {
      setVoiceStatus("No tutor reply available to speak yet.");
      return;
    }
    speakText(lastAgentReply.replace(/[#*_`>-]/g, " "));
    setVoiceStatus("Speaking the latest tutor reply.");
  });
}

if (attachTutorFileButton && tutorAttachmentInput) {
  attachTutorFileButton.addEventListener("click", () => {
    tutorAttachmentInput.click();
  });

  tutorAttachmentInput.addEventListener("change", () => {
    addTutorAttachments(tutorAttachmentInput.files);
    tutorAttachmentInput.value = "";
  });
}

if (tutorAttachmentsTray) {
  tutorAttachmentsTray.addEventListener("click", (event) => {
    const removeButton = event.target.closest("[data-remove-tutor-attachment]");
    if (!removeButton) {
      return;
    }
    pendingTutorAttachments = pendingTutorAttachments.filter(
      (attachment) => attachment.id !== removeButton.dataset.removeTutorAttachment
    );
    renderTutorAttachments();
  });
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const username = ensureIdentity();
  if (!username) {
    return;
  }

  let userPrompt = promptInput.value.trim();
  if (!userPrompt && !pendingTutorAttachments.length) {
    promptInput.focus();
    return;
  }
  if (!userPrompt) {
    userPrompt = "Please help me understand the attached file.";
  }
  if (isGoogleSavePrompt(userPrompt) && !requestGoogleSaveSetupFromChat()) {
    return;
  }

  let temporaryAttachments = [];
  try {
    temporaryAttachments = await buildTemporaryAttachmentPayloads();
  } catch (error) {
    setVoiceStatus(error.message || "Could not read attached file.");
    return;
  }

  const attachmentNames = pendingTutorAttachments.map((attachment) => attachment.file.name);
  appendMessage(
    "user",
    attachmentNames.length
      ? `${userPrompt}\n\nAttached: ${attachmentNames.join(", ")}`
      : userPrompt
  );
  promptInput.value = "";

  const payload = {
    message: userPrompt,
    sessionId: getSessionId(),
    userId: username,
    idToken: getIdToken(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
    selectedMaterialIds: [...selectedMaterialIds],
    inputMode: pendingInputMode,
    temporaryAttachments,
    clientMessages: buildClientChatMessages(),
  };
  pendingInputMode = "text";
  clearTutorAttachments();

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
    if (data.session) {
      applySession(data.session);
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
await refreshSession();
setupVoiceRecognition();
setSidebarCollapsed(window.localStorage.getItem(sidebarCollapsedStorageKey) === "1");
setActiveView(window.localStorage.getItem(activeViewStorageKey) || "tutor");
showPlanWorkspace("home");
showInsightsWorkspace("home");
updateAuthPill(
  getIdToken() ? (activeSession.displayName || "Signed in") : (activeSession.displayName || "Guest session"),
  !getIdToken()
);
restoreSession();
autoresizePrompt();
await refreshLearnerState();
await refreshMasteryBoard();
await refreshRoadmap();
updateUploadMaterialButtonState();
await refreshMaterials();
await refreshInsights();
