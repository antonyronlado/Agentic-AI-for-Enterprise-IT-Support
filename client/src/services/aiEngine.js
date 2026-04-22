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

export function getTickets(userId) {
  const query = userId ? `?userId=${userId}` : '';
  return fetchAPI(`/tickets${query}`);
}

export function createTicket(ticketData) {
  return fetchAPI(`/tickets`, {
    method: "POST",
    body: JSON.stringify(ticketData),
  });
}

export function deleteTicket(ticketId) {
  return fetchAPI(`/tickets/${ticketId}`, {
    method: "DELETE",
  });
}

export function updateTicket(ticketId, updateData) {
  return fetchAPI(`/tickets/${ticketId}`, {
    method: "PUT",
    body: JSON.stringify(updateData),
  });
}

// Keeping original analyze/assess/resolve for backward compatibility if needed, 
// though tickets are now analyzed on creation.
export function analyzeTicket(description, title = "") {
  return fetchAPI("/analyze", { 
    method: "POST", 
    body: JSON.stringify({ description, title }) 
  });
}

export function assessRisk(ticket) {
  return fetchAPI("/assess-risk", {
    method: "POST",
    body: JSON.stringify({
      title: ticket.title || "",
      description: ticket.description || "",
      category: ticket.category || "other",
      priority: ticket.priority || "medium",
    }),
  });
}

export function resolveTicket(ticket) {
  return fetchAPI("/resolve", {
    method: "POST",
    body: JSON.stringify({
      title: ticket.title || "",
      description: ticket.description || "",
      analysis: ticket.analysis || null,
      riskAssessment: ticket.riskAssessment || null,
    }),
  });
}
