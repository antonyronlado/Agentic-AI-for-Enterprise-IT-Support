import { getToken } from './aiEngine';

const API_URL = import.meta.env.VITE_AI_ENGINE_URL || "http://localhost:8000";

function authHeaders(extra = {}) {
  const token = getToken();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

export async function getCopilotSuggestions({ ticket_id, title, description, analysis, risk }) {
  const res = await fetch(`${API_URL}/copilot/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ ticket_id, title, description, analysis, risk }),
  });
  if (!res.ok) {
    let msg = `Copilot API ${res.status}`;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export async function uploadMultimodalFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  // Note: do NOT set Content-Type — browser sets multipart/form-data with boundary automatically
  const res = await fetch(`${API_URL}/multimodal/upload`, {
    method: "POST",
    headers: authHeaders(),   // adds Authorization header only
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}
