import { getToken } from './aiEngine';

const API_URL = import.meta.env.VITE_AI_ENGINE_URL || "http://localhost:8000";

async function fetchAPI(endpoint, options = {}) {
  const token = getToken();
  const res = await fetch(`${API_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  });
  if (!res.ok) {
    let msg = `Analytics API [${endpoint}] ${res.status}`;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export const getAnalyticsOverview  = () => fetchAPI("/analytics/overview");
export const getAnalyticsTrends    = () => fetchAPI("/analytics/trends");
export const getTrendIntelligence  = () => fetchAPI("/analytics/trend-intelligence");
export const getResolutionPerf     = () => fetchAPI("/analytics/resolution-perf");
