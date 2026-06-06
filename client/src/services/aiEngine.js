const API_URL = import.meta.env.VITE_AI_ENGINE_URL || "http://localhost:8000";

export function getToken() {
  return localStorage.getItem("nexus_token") || null;
}

export function setToken(token) {
  if (token) localStorage.setItem("nexus_token", token);
  else localStorage.removeItem("nexus_token");
}

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
    let errMsg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      errMsg = body.detail || body.error || errMsg;
    } catch (e) {
      // ignore
    }
    throw new Error(errMsg);
  }
  return res.json();
}

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

export function getMe() {
  return fetchAPI("/auth/me");
}

export function requestPasswordResetOTP(email) {
  return fetchAPI("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function verifyOTP(email, otp) {
  return fetchAPI("/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify({ email, otp }),
  });
}

export function resetPassword(email, newPassword) {
  return fetchAPI("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ email, new_password: newPassword }),
  });
}

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

export function confirmPasswordReset(ticketId, { userId, passwordResetMode = "auto", preferredPassword = null }) {
  return fetchAPI(`/tickets/${ticketId}/password-reset/confirm`, {
    method: "POST",
    body: JSON.stringify({
      allow: true,
      userId,
      passwordResetMode,
      preferredPassword,
    }),
  });
}

export function getLogs(limit = 100, ticketId = null) {
  const params = new URLSearchParams({ limit: Math.min(limit, 500) });
  if (ticketId) params.set("ticket_id", ticketId);
  return fetchAPI(`/logs?${params.toString()}`);
}

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

export function getRemediationActions() {
  return fetchAPI("/automation/actions");
}

export function approveAction(actionId) {
  return fetchAPI(`/automation/approve/${actionId}`, { method: "POST" });
}

export function rejectAction(actionId) {
  return fetchAPI(`/automation/reject/${actionId}`, { method: "POST" });
}

export function rollbackAction(actionId) {
  return fetchAPI(`/automation/rollback/${actionId}`, { method: "POST" });
}

export function learnFromTicket(ticketId, title, description, steps, result, category) {
  return fetchAPI("/learn", {
    method: "POST",
    body: JSON.stringify({ ticket_id: ticketId, title, description, steps, result, category }),
  });
}

export async function getWebsites() {
  try {
    const res = await fetch(`${API_URL}/websites/public`, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}