const ACCESS_KEY = "wl_access_token";
const REFRESH_KEY = "wl_refresh_token";

// NOTE: localStorage is readable by any script → XSS-exposed. An httpOnly cookie
// would resist XSS but needs backend cookie issuance + CSRF handling. For this
// educational JSON-token API, localStorage is the pragmatic choice.
export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null; // no localStorage on the server
  return localStorage.getItem(ACCESS_KEY);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}
