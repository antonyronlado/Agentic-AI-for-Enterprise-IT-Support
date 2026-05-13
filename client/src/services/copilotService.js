const API_URL = import.meta.env.VITE_AI_ENGINE_URL || "http://localhost:8000";

export async function getCopilotSuggestions({ ticket_id, title, description, analysis, risk }) {
  const res = await fetch(`${API_URL}/copilot/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticket_id, title, description, analysis, risk }),
  });
  if (!res.ok) throw new Error(`Copilot API ${res.status}`);
  return res.json();
}

export async function uploadMultimodalFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_URL}/multimodal/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}
