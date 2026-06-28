import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Single-flight refresh: if several requests 401 at once (the dashboard fires
// parallel fetches), they share ONE refresh call. Refresh tokens ROTATE, so
// independent refreshes would invalidate each other and spuriously log the user
// out. Returns the new access token, or null if refresh failed (tokens cleared).
let refreshInFlight: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) {
    clearTokens(); // refresh token expired/revoked → force re-login
    return null;
  }
  const body = (await res.json()) as { access_token: string; refresh_token: string };
  setTokens(body.access_token, body.refresh_token);
  return body.access_token;
}

function refreshOnce(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

async function request<T>(
  path: string,
  init: RequestInit,
  auth: boolean,
  retry = true,
): Promise<T> {
  const headers: Record<string, string> = {};
  // JSON content-type only for string (JSON) bodies. FormData uploads must NOT
  // set it — the browser adds the multipart boundary itself.
  if (typeof init.body === "string") headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  // Access token likely expired → refresh once, then retry the original request.
  if (res.status === 401 && auth && retry) {
    const newToken = await refreshOnce();
    if (newToken) return request<T>(path, init, auth, false);
    // refresh failed (tokens already cleared) → fall through and throw the 401
  }

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = (await res.json()) as { message?: string };
      if (body.message) message = body.message; // backend error schema {code, message, detail}
    } catch {
      // non-JSON error body; keep the default message
    }
    throw new ApiError(res.status, message);
  }

  // 204 No Content (deletes, logout) → nothing to parse.
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export function apiGet<T>(path: string, auth = false): Promise<T> {
  return request<T>(path, { method: "GET" }, auth);
}

export function apiPost<T>(path: string, body: unknown, auth = false): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body) }, auth);
}

export function apiPatch<T>(path: string, body: unknown, auth = false): Promise<T> {
  return request<T>(path, { method: "PATCH", body: JSON.stringify(body) }, auth);
}

export function apiDelete<T = void>(path: string, auth = false, body?: unknown): Promise<T> {
  const init: RequestInit = { method: "DELETE" };
  if (body !== undefined) init.body = JSON.stringify(body);
  return request<T>(path, init, auth);
}

export function apiUpload<T>(path: string, formData: FormData, auth = false): Promise<T> {
  return request<T>(path, { method: "POST", body: formData }, auth);
}

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();
  // Best-effort server-side revocation (/auth/logout returns 204, no body to
  // parse). Clear local tokens no matter what so the user always gets logged out.
  if (refreshToken) {
    try {
      await fetch(`${API_BASE}/api/v1/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      // network error — fall through and clear locally
    }
  }
  clearTokens();
}

export { API_BASE };
