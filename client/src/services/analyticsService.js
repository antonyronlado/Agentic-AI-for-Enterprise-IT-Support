const API_URL = import.meta.env.VITE_AI_ENGINE_URL || "http://localhost:8000";

async function fetchAPI(endpoint, options = {}) {
  const res = await fetch(`${API_URL}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`Analytics API [${endpoint}] ${res.status}`);
  return res.json();
}

export const getAnalyticsOverview = () => fetchAPI("/analytics/overview");
export const getAnalyticsTrends = () => fetchAPI("/analytics/trends");
export const getTrendIntelligence = () => fetchAPI("/analytics/trend-intelligence");
export const getResolutionPerf = () => fetchAPI("/analytics/resolution-perf");
