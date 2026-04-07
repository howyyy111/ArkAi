const chatForm = document.getElementById("chat-form");
const messages = document.getElementById("messages");
const promptInput = document.getElementById("prompt");
const seedButton = document.getElementById("seed-button");
const changeGmailButton = document.getElementById("change-gmail-button");
const submitButton = document.getElementById("submit-button");
const usernameModal = document.getElementById("username-modal");
const usernameForm = document.getElementById("username-form");
const usernameInput = document.getElementById("username-input");

const sessionStorageKey = "arkais-session-id";
const usernameStorageKey = "arkais-user-email";
const requestTimeoutMs = 90000;

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

function extractLinks(text) {
  const matches = text.match(/https?:\/\/[^\s`]+/g) || [];
  return [...new Set(matches)];
}

function stripLinks(text, links) {
  let nextText = text;
  for (const link of links) {
    nextText = nextText.replaceAll(link, "").trim();
  }
  return nextText.replace(/\n{3,}/g, "\n\n").trim();
}

function appendInlineCode(element, text) {
  const parts = text.split(/(`[^`]+`)/g);

  for (const part of parts) {
    if (!part) {
      continue;
    }

    if (part.startsWith("`") && part.endsWith("`")) {
      const code = document.createElement("code");
      code.textContent = part.slice(1, -1);
      element.appendChild(code);
      continue;
    }

    element.appendChild(document.createTextNode(part));
  }
}

function linkLabel(url, index) {
  if (url.includes("accounts.google.com") || url.includes("oauth")) {
    return "Continue with Google";
  }
  return index === 0 ? "Open link" : `Open link ${index + 1}`;
}

function highlightCodeBlock(codeElement, language) {
  if (!window.hljs) {
    return;
  }

  if (language) {
    codeElement.classList.add(`language-${language}`);
  }

  window.hljs.highlightElement(codeElement);
}

function buildMessageBody(body) {
  const container = document.createElement("div");
  container.className = "message-body";

  const links = extractLinks(body);
  const text = stripLinks(body, links);
  const tokens = text.split(/```([\w+-]*)\n?([\s\S]*?)```/g);

  if (text) {
    for (let index = 0; index < tokens.length; index += 1) {
      if (index % 3 === 2) {
        const codeText = tokens[index].trim();
        if (!codeText) {
          continue;
        }

        const language = (tokens[index - 1] || "").trim();
        const block = document.createElement("div");
        block.className = "code-block";

        if (language) {
          const label = document.createElement("div");
          label.className = "code-language";
          label.textContent = language;
          block.appendChild(label);
        }

        const pre = document.createElement("pre");
        const code = document.createElement("code");
        code.textContent = codeText;
        highlightCodeBlock(code, language);
        pre.appendChild(code);
        block.appendChild(pre);
        container.appendChild(block);
        continue;
      }

      if (index % 3 !== 0) {
        continue;
      }

      for (const paragraph of tokens[index].split(/\n{2,}/)) {
        const normalized = paragraph.trim();
        if (!normalized) {
          continue;
        }

        const p = document.createElement("p");
        p.className = "message-paragraph";
        appendInlineCode(p, normalized);
        container.appendChild(p);
      }
    }
  }

  for (const [index, url] of links.entries()) {
    const anchor = document.createElement("a");
    anchor.className = "message-link";
    anchor.href = url;
    anchor.target = "_blank";
    anchor.rel = "noreferrer";
    anchor.textContent = linkLabel(url, index);
    container.appendChild(anchor);
  }

  if (!text && links.length === 0) {
    const p = document.createElement("p");
    p.className = "message-paragraph";
    p.textContent = body;
    container.appendChild(p);
  }

  return container;
}

function appendMessage(role, body) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const roleLabel = document.createElement("p");
  roleLabel.className = "message-role";
  roleLabel.textContent = role === "user" ? getUsername() || "You" : "ARKAIS";

  article.appendChild(roleLabel);
  article.appendChild(buildMessageBody(body));
  messages.appendChild(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });
}

seedButton.addEventListener("click", () => {
  promptInput.value = "Teach me loops with one example and one exercise.";
});

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
  submitButton.textContent = "Sending...";

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
      submitButton.textContent = "Send to agent";
    });
});

ensureUsername();
