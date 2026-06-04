const API_URL = import.meta.env.VITE_AI_ENGINE_URL || "http://localhost:8000";

// ── Token helpers ─────────────────────────────────────────────────────────
export function getToken() {
  return localStorage.getItem("nexus_token") || null;
}

export function setToken(token) {
  if (token) localStorage.setItem("nexus_token", token);
  else localStorage.removeItem("nexus_token");
}

// ── Base fetch with auth header ────────────────────────────────────────────
async function fetchAPI(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    // Parse error details without exposing raw server internals to the UI
    let errMsg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      errMsg = body.detail || body.error || errMsg;
    } catch {
      // ignore parse errors
    }
    throw new Error(errMsg);
  }
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────
export function login(username, password) {
  return fetchAPI("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function register(username, email, password) {
  return fetchAPI("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });
}

/** Validate the stored token and get fresh user profile from server */
export function getMe() {
  return fetchAPI("/auth/me");
}

// ── Tickets ───────────────────────────────────────────────────────────────
export function getTickets(userId, role = "user") {
  const query = userId ? `?userId=${userId}&role=${role}` : `?role=${role}`;
  return fetchAPI(`/tickets${query}`);
}

export function createTicket(ticketData) {
  return fetchAPI("/tickets", { method: "POST", body: JSON.stringify(ticketData) });
}

export function updateTicket(ticketId, updateData) {
  return fetchAPI(`/tickets/${ticketId}`, {
    method: "PUT",
    body: JSON.stringify(updateData),
  });
}

export function deleteTicket(ticketId) {
  return fetchAPI(`/tickets/${ticketId}`, { method: "DELETE" });
}

export function submitFeedback(ticketId, rating, comment = null) {
  return fetchAPI(`/tickets/${ticketId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ rating, comment }),
  });
}

// ── Logs ──────────────────────────────────────────────────────────────────
export function getLogs(limit = 100, ticketId = null) {
  const params = new URLSearchParams({ limit: Math.min(limit, 500) });
  if (ticketId) params.set("ticket_id", ticketId);
  return fetchAPI(`/logs?${params.toString()}`);
}

// ── Incidents ─────────────────────────────────────────────────────────────
export function getIncidents() {
  return fetchAPI("/incidents");
}

export function triggerClustering() {
  return fetchAPI("/incidents/cluster", { method: "POST" });
}

export function resolveIncident(id) {
  return fetchAPI(`/incidents/${id}/resolve`, { method: "PUT" });
}

export function getKBArticles() {
  return fetchAPI("/incidents/kb/articles");
}

export function generateKBArticle(ticketId) {
  return fetchAPI("/incidents/kb/articles/generate", {
    method: "POST",
    body: JSON.stringify({ ticket_id: ticketId }),
  });
}

export function submitKBFeedback(articleId, rating) {
  return fetchAPI(`/incidents/kb/articles/${articleId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ rating }),
  });
}

// ── Automation ────────────────────────────────────────────────────────────
export function getRemediationActions() {
  return fetchAPI("/automation/actions");
}

export function approveAction(actionId) {
  // approved_by is now determined server-side from the auth token
  return fetchAPI(`/automation/approve/${actionId}`, { method: "POST" });
}

export function rejectAction(actionId) {
  return fetchAPI(`/automation/reject/${actionId}`, { method: "POST" });
}

export function rollbackAction(actionId) {
  return fetchAPI(`/automation/rollback/${actionId}`, { method: "POST" });
}

// ── Learning ──────────────────────────────────────────────────────────────
export function learnFromTicket(ticketId, title, description, steps, result, category) {
  return fetchAPI("/learn", {
    method: "POST",
    body: JSON.stringify({ ticket_id: ticketId, title, description, steps, result, category }),
  });
}
