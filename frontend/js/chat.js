import { createSession, getSession, sendMessage } from "./api.js";

const STORAGE_KEY = "nr1.sessionId";

const state = {
  sessionId: null,
  status: "loading",
  sending: false,
};

const elements = {};

document.addEventListener("DOMContentLoaded", () => {
  elements.form = document.getElementById("chatForm");
  elements.input = document.getElementById("messageInput");
  elements.sendButton = document.getElementById("sendButton");
  elements.finishButton = document.getElementById("finishButton");
  elements.messageList = document.getElementById("messageList");
  elements.typing = document.getElementById("typingIndicator");
  elements.alertArea = document.getElementById("alertArea");
  elements.sessionStatus = document.getElementById("sessionStatus");
  elements.sessionLabel = document.getElementById("sessionLabel");

  bindEvents();
  autosizeTextarea();
  bootConversation();
});

function bindEvents() {
  elements.form.addEventListener("submit", onSubmit);
  elements.finishButton.addEventListener("click", onFinish);
  elements.input.addEventListener("input", () => {
    autosizeTextarea();
  });
  elements.input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      elements.form.requestSubmit();
    }
  });
}

async function bootConversation() {
  const savedSessionId = window.localStorage.getItem(STORAGE_KEY);

  if (savedSessionId) {
    try {
      const snapshot = await getSession(savedSessionId);
      hydrateFromSnapshot(snapshot);
      return;
    } catch (error) {
      window.localStorage.removeItem(STORAGE_KEY);
      if (error.status !== 404) {
        showAlert("Não foi possível comunicar com o servidor.\nTente novamente.");
        setComposerEnabled(false);
        setSessionState("indisponível", "danger");
        return;
      }
    }
  }

  await startNewSession();
}

async function startNewSession(options = {}) {
  const { preserveAlert = false } = options;
  try {
    setSessionState("Inicializando...", "neutral");
    const response = await createSession();
    state.sessionId = response.session_id;
    state.status = response.status;
    window.localStorage.setItem(STORAGE_KEY, state.sessionId);
    setFinishButtonVisible(false);
    clearConversation({ preserveAlert });
    renderMessage({
      role: "assistant",
      content: response.assistant_message,
      created_at: new Date().toISOString(),
    });
    setSessionState(response.status === "complete" ? "Sessão concluída" : "Sessão ativa", response.status === "complete" ? "complete" : "active");
    setComposerEnabled(true);
  } catch (error) {
    showAlert("Não foi possível comunicar com o servidor.\nTente novamente.");
    setComposerEnabled(false);
    setSessionState("indisponível", "danger");
  }
}

function hydrateFromSnapshot(snapshot) {
  state.sessionId = snapshot.session_id;
  state.status = snapshot.status;
  window.localStorage.setItem(STORAGE_KEY, state.sessionId);
  clearConversation();

  for (const message of snapshot.messages) {
    renderMessage(message);
  }

  const isComplete = snapshot.status === "complete";
  setSessionState(isComplete ? "Sessão concluída" : "Sessão ativa", isComplete ? "complete" : "active");
  setComposerEnabled(!isComplete);
  setFinishButtonVisible(isComplete);
}

function clearConversation(options = {}) {
  const { preserveAlert = false } = options;
  elements.messageList.replaceChildren();
  hideTyping();
  if (!preserveAlert) {
    clearAlert();
  }
  scrollToBottom();
}

async function onSubmit(event) {
  event.preventDefault();
  if (state.sending) {
    return;
  }

  const message = elements.input.value.trim();
  if (!message) {
    return;
  }

  if (!state.sessionId) {
    await startNewSession();
    if (!state.sessionId) {
      return;
    }
  }

  renderMessage({
    role: "user",
    content: message,
    created_at: new Date().toISOString(),
  });

  elements.input.value = "";
  autosizeTextarea();
  setSendingState(true);

  try {
    const response = await sendMessage(state.sessionId, message);
    state.status = response.status;
    renderMessage({
      role: "assistant",
      content: response.assistant_message,
      created_at: new Date().toISOString(),
    });
    setSessionState(
      response.status === "complete" ? "Sessão concluída" : "Sessão ativa",
      response.status === "complete" ? "complete" : "active",
    );
    const isComplete = response.status === "complete";
    setComposerEnabled(!isComplete);
    setFinishButtonVisible(isComplete);
  } catch (error) {
    if (error.status === 404) {
      window.localStorage.removeItem(STORAGE_KEY);
      state.sessionId = null;
      clearConversation({ preserveAlert: true });
      showAlert("Sua sessão anterior não foi encontrada. Iniciamos uma nova conversa.");
      await startNewSession({ preserveAlert: true });
      return;
    }

    showAlert("Não foi possível comunicar com o servidor.\nTente novamente.");
  } finally {
    setSendingState(false);
    if (state.status === "complete") {
      setComposerEnabled(false);
    }
  }
}

async function onFinish() {
  if (state.sending) {
    return;
  }

  window.localStorage.removeItem(STORAGE_KEY);
  state.sessionId = null;
  state.status = "loading";
  setFinishButtonVisible(false);
  clearConversation();
  await startNewSession();
}

function renderMessage(message) {
  const row = document.createElement("div");
  row.className = `message-row ${message.role === "user" ? "user" : "assistant"}`;

  const bubble = document.createElement("article");
  bubble.className = `message-bubble ${message.role === "user" ? "user" : "assistant"}`;

  const content = document.createElement("div");
  content.className = "message-content";
  content.textContent = message.content;

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = formatTime(message.created_at);

  bubble.append(content, meta);
  row.appendChild(bubble);
  elements.messageList.appendChild(row);
  scrollToBottom();
}

function setSendingState(isSending) {
  state.sending = isSending;
  elements.input.disabled = isSending;
  elements.sendButton.disabled = isSending;
  if (isSending) {
    showTyping();
  } else {
    hideTyping();
    elements.input.focus();
  }
}

function setComposerEnabled(enabled) {
  elements.input.disabled = !enabled;
  elements.sendButton.disabled = !enabled;
}

function setFinishButtonVisible(visible) {
  elements.finishButton.classList.toggle("d-none", !visible);
}

function showTyping() {
  elements.typing.classList.remove("d-none");
  scrollToBottom();
}

function hideTyping() {
  elements.typing.classList.add("d-none");
}

function setSessionState(label, tone) {
  elements.sessionLabel.textContent = state.sessionId
    ? `Sessão ${state.sessionId.slice(0, 8)}`
    : "Aguardando sessão";
  elements.sessionStatus.textContent = label;
  elements.sessionStatus.classList.remove("is-complete", "is-danger");
  if (tone === "complete") {
    elements.sessionStatus.classList.add("is-complete");
  }
  if (tone === "danger") {
    elements.sessionStatus.classList.add("is-danger");
  }
}

function showAlert(message) {
  elements.alertArea.replaceChildren();

  const alert = document.createElement("div");
  alert.className = "alert alert-danger alert-dismissible fade show";
  alert.setAttribute("role", "alert");

  const text = document.createElement("div");
  text.textContent = message;
  alert.appendChild(text);

  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn-close";
  button.setAttribute("data-bs-dismiss", "alert");
  button.setAttribute("aria-label", "Fechar");

  alert.appendChild(button);
  elements.alertArea.appendChild(alert);
}

function clearAlert() {
  elements.alertArea.replaceChildren();
}

function autosizeTextarea() {
  const textarea = elements.input;
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    elements.messageList.scrollTop = elements.messageList.scrollHeight;
  });
}

function formatTime(value) {
  const date = value ? new Date(value) : new Date();
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
