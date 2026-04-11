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

const sessionStorageKey = "arkai-session-id";
const usernameStorageKey = "arkai-user-email";
const historyStorageKeyPrefix = "arkai-history-";
const requestTimeoutMs = 90000;

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

function openUsernameModal(prefill = true) {
  usernameModal.classList.add("open");
  usernameModal.setAttribute("aria-hidden", "false");
  usernameInput.value = prefill ? getUsername() : "";
  usernameInput.setCustomValidity("");
  usernameInput.focus();
  usernameInput.select();
}

function ensureUsername() {
  const username = getUsername();
  if (username) {
    usernameModal.classList.remove("open");
    usernameModal.setAttribute("aria-hidden", "true");
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
        const langClass = Array.from(element.classList).find(c => c && c.startsWith('language-'));
        if (langClass) {
          const lang = langClass.replace('language-', '');
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

  if (!skipSave) {
    saveHistoryItem(role, body);
  }
}

seedButton.addEventListener("click", () => {
  promptInput.value = "Teach me loops with one example and one exercise.";
});

if (newSessionButton) {
  newSessionButton.addEventListener("click", () => {
    clearSessionState();
  });
}

changeGmailButton.addEventListener("click", () => {
  openUsernameModal(true);
});

promptInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey) {
    return;
  }

  event.preventDefault();
  submitButton.click();
});

usernameForm.addEventListener("submit", (event) => {
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
  usernameModal.classList.remove("open");
  usernameModal.setAttribute("aria-hidden", "true");
  promptInput.focus();
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const username = ensureUsername();
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
  };

  submitButton.disabled = true;
  submitButton.classList.add("loading");

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), requestTimeoutMs);

  fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    signal: controller.signal,
    body: JSON.stringify(payload),
  })
    .then(async (response) => {
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Request failed.");
      }
      appendMessage("agent", data.reply);
    })
    .catch((error) => {
      const message =
        error.name === "AbortError"
          ? "Request timed out after 90 seconds."
          : error.message;
      appendMessage("agent", `Request failed: ${message}`);
    })
    .finally(() => {
      window.clearTimeout(timeoutId);
      submitButton.disabled = false;
      submitButton.classList.remove("loading");
    });
});

ensureUsername();
restoreSession();

