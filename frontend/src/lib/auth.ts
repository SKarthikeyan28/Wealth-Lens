const ACCESS_KEY = "wl_access_token";
const REFRESH_KEY = "wl_refresh_token";

// `storage` events only fire in OTHER tabs, never the tab that wrote the change.
// We dispatch this same-tab event so useRequireAuth reacts to login/logout here.
export const AUTH_EVENT = "wl-auth-change";

function notify(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(AUTH_EVENT));
}

// NOTE: localStorage is readable by any script → XSS-exposed. An httpOnly cookie
// would resist XSS but needs backend cookie issuance + CSRF handling. For this
// educational JSON-token API, localStorage is the pragmatic choice.
export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
  notify();
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null; // no localStorage on the server
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  notify();
}
