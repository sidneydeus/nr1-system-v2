const API_BASE_URL =
  window.NR1_API_BASE_URL ??
  (window.location.protocol === "file:" ? "http://127.0.0.1:8000" : window.location.origin);

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers ?? {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const error = new Error(
      typeof payload === "string"
        ? payload
        : payload?.detail || payload?.message || "Request failed",
    );
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

export function createSession() {
  return request("/sessions", { method: "POST" });
}

export function sendMessage(sessionId, message) {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      message,
    }),
  });
}

export function getSession(sessionId) {
  return request(`/sessions/${encodeURIComponent(sessionId)}`);
}
