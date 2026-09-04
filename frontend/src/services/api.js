const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

/**
 * Thin wrapper around fetch() that:
 * - prefixes every call with the configured API base URL
 * - parses JSON responses
 * - throws an Error with a useful message on non-2xx responses, so callers
 *   can catch one consistent error type regardless of which endpoint failed
 */
async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let body = null;
  try {
    body = await response.json();
  } catch {
    // Response had no JSON body (e.g. network-level failure) -- body stays null.
  }

  if (!response.ok) {
    // FastAPI validation errors (422) put details in body.detail as an array;
    // other errors (404/500/503) put a plain string in body.detail.
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg).join("; ")
      : detail || `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return body;
}

export function getHealthDb() {
  return request("/health/db");
}

function withStatement(path, statementId) {
  return `${path}?statement_id=${encodeURIComponent(statementId)}`;
}

export function getAnalyticsSummary(statementId) {
  return request(withStatement("/api/analytics/summary", statementId));
}

export function getAnalyticsByStatus(statementId) {
  return request(withStatement("/api/analytics/by-status", statementId));
}

export function getAnalyticsByCategory(statementId) {
  return request(withStatement("/api/analytics/by-category", statementId));
}

export function getAnalyticsByDate(statementId) {
  return request(withStatement("/api/analytics/by-date", statementId));
}

export function predictRisk(payload) {
  return request("/api/ml/predict-risk", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Uploads a statement PDF for import. Deliberately does NOT go through
 * request() above -- multipart/form-data uploads must NOT set a
 * "Content-Type: application/json" header (the browser needs to set its
 * own multipart boundary header), and a non-JSON-shaped success case
 * doesn't apply here anyway since the response is always JSON.
 */
export async function importStatementPdf(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/import/pdf`, {
    method: "POST",
    body: formData,
  });

  let body = null;
  try {
    body = await response.json();
  } catch {
    // no JSON body
  }

  if (!response.ok) {
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg).join("; ")
      : detail || `Upload failed with status ${response.status}`;
    throw new Error(message);
  }

  return body;
}