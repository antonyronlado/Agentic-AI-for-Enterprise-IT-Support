const API_URL = import.meta.env.VITE_AI_ENGINE_URL || "http://localhost:8000";

async function fetchAPI(endpoint, options = {}) {
  const res = await fetch(`${API_URL}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API [${endpoint}] ${res.status}: ${err}`);
  }
  return res.json();
}

export function getTickets(userId, role = "user") {
  const query = userId ? `?userId=${userId}&role=${role}` : `?role=${role}`;
  return fetchAPI(`/tickets${query}`);
}

export function createTicket(ticketData) {
  return fetchAPI("/tickets", { method: "POST", body: JSON.stringify(ticketData) });
}

export function updateTicket(ticketId, updateData) {
  return fetchAPI(`/tickets/${ticketId}`, { method: "PUT", body: JSON.stringify(updateData) });
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

export function login(username, password) {
  return fetchAPI("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
}

export function register(username, email, password) {
  return fetchAPI("/auth/register", { method: "POST", body: JSON.stringify({ username, email, password }) });
}

export function getLogs(limit = 100, ticketId = null) {
  const params = new URLSearchParams({ limit });
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
  return fetchAPI("/incidents/kb/articles/generate", { method: "POST", body: JSON.stringify({ ticket_id: ticketId }) });
}

export function submitKBFeedback(articleId, rating) {
  return fetchAPI(`/incidents/kb/articles/${articleId}/feedback`, { method: "POST", body: JSON.stringify({ rating }) });
}

export function getRemediationActions() {
  return fetchAPI("/automation/actions");
}

export function approveAction(actionId, approvedBy = "admin") {
  return fetchAPI(`/automation/approve/${actionId}`, { method: "POST", body: JSON.stringify({ approved_by: approvedBy }) });
}

export function rejectAction(actionId, approvedBy = "admin") {
  return fetchAPI(`/automation/reject/${actionId}`, { method: "POST", body: JSON.stringify({ approved_by: approvedBy }) });
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
