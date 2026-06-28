"use client";

import { useRouter } from "next/navigation";
import { useEffect, useSyncExternalStore } from "react";

import { getAccessToken, AUTH_EVENT } from "./auth";

function subscribe(callback: () => void): () => void {
  window.addEventListener("storage", callback); // cross-tab changes
  window.addEventListener(AUTH_EVENT, callback); // same-tab login/logout
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(AUTH_EVENT, callback);
  };
}

function serverSnapshot(): string | null {
  return null; // localStorage doesn't exist during SSR
}

/**
 * Redirects to /login if there's no token. Returns true once a token is present.
 *
 * Uses useSyncExternalStore (not useEffect + setState) — the React-blessed way to
 * read browser-only state like localStorage. The server snapshot is always null,
 * so SSR/hydration is consistent; after hydration the real token is read. The
 * effect only performs the redirect side effect.
 */
export function useRequireAuth(): boolean {
  const router = useRouter();
  const token = useSyncExternalStore(subscribe, getAccessToken, serverSnapshot);

  useEffect(() => {
    if (token === null) {
      router.replace("/login");
    }
  }, [token, router]);

  return token !== null;
}
