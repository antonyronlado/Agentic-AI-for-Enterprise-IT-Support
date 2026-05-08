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
  return fetchAPI("/tickets", {
    method: "POST",
    body: JSON.stringify(ticketData),
  });
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

export function getLogs(limit = 100, ticketId = null) {
  const params = new URLSearchParams({ limit });
  if (ticketId) params.set("ticket_id", ticketId);
  return fetchAPI(`/logs?${params.toString()}`);
}
