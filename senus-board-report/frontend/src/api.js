import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE });

export const api = {
  periods: () => client.get("/api/financials/periods").then((r) => r.data),
  corporateFacts: () => client.get("/api/financials/corporate-facts").then((r) => r.data),
  kpiTargets: () => client.get("/api/financials/kpi-targets").then((r) => r.data),
  growth: () => client.get("/api/financials/growth").then((r) => r.data),
  profitability: () => client.get("/api/financials/profitability").then((r) => r.data),
  cashLiquidity: () => client.get("/api/financials/cash-liquidity").then((r) => r.data),
  solvency: () => client.get("/api/financials/solvency").then((r) => r.data),
  returns: () => client.get("/api/financials/returns").then((r) => r.data),
  insight: (section) => client.get(`/api/insights/${section}`).then((r) => r.data),
  regenerateInsight: (section) => client.post(`/api/insights/${section}/generate`).then((r) => r.data),

  // Live document ingestion — upload a new filing, review the AI extraction,
  // then commit it into the database.
  listDocuments: () => client.get("/api/documents").then((r) => r.data),
  extractDocument: (formData) =>
    client.post("/api/documents/extract", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data),
  commitDocument: (documentId, extraction) =>
    client.post(`/api/documents/${documentId}/commit`, { extraction }).then((r) => r.data),
  discardDocument: (documentId) =>
    client.delete(`/api/documents/${documentId}`).then((r) => r.data),
};

export default api;