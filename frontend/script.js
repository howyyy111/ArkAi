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
const roadmapBoard = document.getElementById("roadmap-board");
const materialFileInput = document.getElementById("material-file");
const materialTextInput = document.getElementById("material-text");
const materialQueryInput = document.getElementById("material-query");
const uploadMaterialButton = document.getElementById("upload-material-button");
const askMaterialsButton = document.getElementById("ask-materials-button");
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
let selectedMaterialIds = new Set();
let lastAgentReply = "";
let speechRecognition = null;
let isListening = false;
let pendingInputMode = "text";
let latestLearnerState = null;
let latestMaterials = [];
let latestInterventionPlan = null;

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
    stateSummary.textContent = "Sign in to start building your long-term learner profile.";
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

  const topics = mastery?.topics || [];
  if (!topics.length) {
    masteryTopics.innerHTML = `<p class="mastery-empty">No mastery data yet. Complete a diagnostic to populate this.</p>`;
    return;
  }

  masteryTopics.innerHTML = topics
    .slice(0, 4)
    .map((topic) => {
      const score = Math.round((topic.score || 0) * 100);
      return `
        <article class="mastery-topic">
          <strong>${topic.topic}</strong>
          <p>${topic.label} • ${score}% • ${topic.assessments_taken || 0} assessments</p>
          <div class="mastery-bar"><span style="width: ${score}%"></span></div>
        </article>
      `;
    })
    .join("");
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

function renderRoadmap(roadmapResult) {
  const roadmap = roadmapResult?.roadmap || null;
  const summary = roadmapResult?.summary || null;
  activeRoadmap = roadmap;

  if (!roadmap || !summary) {
    roadmapMode.textContent = "No roadmap yet";
    roadmapSummary.textContent = "Your roadmap will appear here after generation.";
    roadmapBoard.innerHTML = `<p class="mastery-empty">No roadmap data yet. Create one to see milestones and sessions.</p>`;
    return;
  }

  roadmapMode.textContent = `${summary.mode} mode`;
  const nextSession = summary.next_session?.title ? `Next: ${summary.next_session.title}` : "All sessions currently updated.";
  roadmapSummary.textContent =
    `${summary.completed_sessions}/${summary.total_sessions} sessions completed • ` +
    `${summary.missed_sessions} missed • ${Math.round((summary.completion_rate || 0) * 100)}% complete • ` +
    `${nextSession}` +
    (summary.revision_reason ? ` • revision: ${summary.revision_reason}` : "");

  roadmapBoard.innerHTML = roadmap.phases
    .map((phase) => {
      const sessionsMarkup = (phase.sessions || [])
        .map(
          (session) => `
            <article class="roadmap-session">
              <div>
                <strong>${session.title}</strong>
                <p>${session.focus} • ${session.duration_minutes} min • due ${session.due_date}</p>
                <p>Status: ${session.status}</p>
              </div>
              <div class="roadmap-session-actions">
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
    materialsSelectionSummary.textContent = "No materials selected yet.";
    return;
  }
  materialsSelectionSummary.textContent = `${selectedMaterialIds.size} material(s) selected for grounded tutoring and chat context.`;
}

function renderMaterials(materials = []) {
  latestMaterials = materials;
  if (!materials.length) {
    materialsLibrary.innerHTML = `<p class="mastery-empty">No materials yet. Upload a file or pasted text to begin.</p>`;
    updateMaterialsSelectionSummary();
    refreshOverview();
    return;
  }

  const validIds = new Set(materials.map((material) => material.material_id));
  selectedMaterialIds = new Set([...selectedMaterialIds].filter((id) => validIds.has(id)));

  materialsLibrary.innerHTML = materials
    .map((material) => {
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
            <input class="material-select" type="checkbox" data-material-id="${material.material_id}" ${checked} />
          </header>
          <p>${material.summary}</p>
          <p>${meta} • added ${material.created_at || "recently"}</p>
        </article>
      `;
    })
    .join("");
  updateMaterialsSelectionSummary();
  refreshOverview();
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
    evaluationBoard.innerHTML = `<p class="mastery-empty">No evaluation snapshot yet.</p>`;
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
    interventionSummary.textContent = "Refresh insights to see learner risk level and recommended interventions.";
    refreshOverview();
    return;
  }
  interventionRisk.textContent = `${plan.risk_level} risk`;
  interventionSummary.textContent = `${plan.summary} Recommended: ${(plan.recommended_actions || []).slice(0, 2).join(" ")}`;
  refreshOverview();
}

function renderWeeklyReport(report) {
  if (!report) {
    reportBoard.innerHTML = `<p class="mastery-empty">No weekly report generated yet.</p>`;
    return;
  }
  reportBoard.innerHTML = `
    <article class="material-card">
      <header>
        <div>
          <p class="section-label">Weekly report</p>
          <h5>${report.title}</h5>
        </div>
      </header>
      <p>${report.note_text.replace(/\n/g, "<br />")}</p>
    </article>
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
    : "Upload notes or images for grounding.";

  overviewRisk.textContent = latestInterventionPlan?.risk_level || "Unknown";
  overviewRiskCaption.textContent = latestInterventionPlan?.triggers?.length
    ? latestInterventionPlan.triggers.join(" • ")
    : "Refresh insights to evaluate learner risk.";

  overviewBlurb.textContent = latestLearnerState?.recommended_next_action
    || "Track mastery, roadmap momentum, grounded materials, and intervention risk from one place.";
}

function renderSystemStatus(status) {
  if (!status) {
    systemStackTitle.textContent = "Unavailable";
    systemStackSummary.textContent = "System status could not be loaded.";
    systemReadinessBoard.innerHTML = `<p class="mastery-empty">No system status loaded yet.</p>`;
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
    demoPitchCopy.textContent = "Demo kit unavailable.";
    demoMetricsBoard.innerHTML = `<p class="mastery-empty">No demo metrics yet.</p>`;
    demoPersonasBoard.innerHTML = `<p class="mastery-empty">No demo personas loaded yet.</p>`;
    demoScriptBoard.innerHTML = `<p class="mastery-empty">No demo script loaded yet.</p>`;
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
    .join("") || `<p class="mastery-empty">No demo personas loaded yet.</p>`;

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
    .join("") || `<p class="mastery-empty">No demo script loaded yet.</p>`;
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
      const optionsMarkup = question.options
        .map(
          (option, optionIndex) => `
            <label class="option-row">
              <input type="radio" name="${question.question_id}" value="${String.fromCharCode(65 + optionIndex)}" />
              <span><strong>${String.fromCharCode(65 + optionIndex)}.</strong> ${option}</span>
            </label>
          `
        )
        .join("");

      return `
        <section class="diagnostic-question">
          <h5>Question ${index + 1}</h5>
          <p>${question.prompt}</p>
          <div class="options-list">${optionsMarkup}</div>
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
          <p>${item.is_correct ? "Correct" : `Needs review • correct answer: ${item.correct_answer}`}</p>
          <p>${item.explanation}</p>
        </article>
      `
    )
    .join("");

  diagnosticResult.innerHTML = `
    <article class="result-card">
      <strong>Score: ${Math.round((result.score || 0) * 100)}%</strong>
      <p>${result.correct_count}/${result.question_count} correct</p>
      <p>Weak concepts: ${weakConcepts}</p>
      <p>${result.recommended_next_action}</p>
    </article>
    ${questionCards}
  `;
  diagnosticResult.classList.remove("hidden");
}

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
    materialsStatus.textContent = "Choose a file or paste study text first.";
    return;
  }

  uploadMaterialButton.disabled = true;
  materialsStatus.textContent = "Uploading material...";
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
    materialsStatus.textContent = `Uploaded ${data.material.name}.`;
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
    materialsStatus.textContent = "Ask a question about your materials first.";
    materialQueryInput.focus();
    return;
  }

  materialsStatus.textContent = "Grounding tutor answer from selected materials...";
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
    materialsStatus.textContent = "Grounded answer ready.";
    await refreshLearnerState();
    await refreshInsights();
  } catch (error) {
    materialsStatus.textContent = error.message;
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
    const selected = diagnosticForm.querySelector(`input[name="${question.question_id}"]:checked`);
    if (selected) {
      answers[question.question_id] = selected.value;
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
    await refreshLearnerState();
    await refreshMasteryBoard();
    await refreshRoadmap();
    await refreshInsights();
  } catch (error) {
    assessmentStatus.textContent = error.message;
  }
});

roadmapBoard.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-phase-id][data-session-id][data-status]");
  if (!button) {
    return;
  }

  roadmapStatus.textContent = "Updating roadmap session...";
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
    roadmapStatus.textContent = data.message || "Roadmap updated.";
    await refreshLearnerState();
    await refreshMasteryBoard();
    await refreshInsights();
  } catch (error) {
    roadmapStatus.textContent = error.message;
  }
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
