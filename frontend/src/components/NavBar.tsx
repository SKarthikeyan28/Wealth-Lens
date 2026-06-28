"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSyncExternalStore } from "react";

import { logout } from "@/lib/api";
import { getAccessToken, AUTH_EVENT } from "@/lib/auth";

function subscribe(callback: () => void): () => void {
  window.addEventListener("storage", callback); // cross-tab
  window.addEventListener(AUTH_EVENT, callback); // same-tab login/logout
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(AUTH_EVENT, callback);
  };
}

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/accounts", label: "Accounts" },
  { href: "/cashflow", label: "Cashflow" },
  { href: "/risk", label: "Risk" },
  { href: "/projection", label: "Projection" },
  { href: "/chat", label: "Chat" },
  { href: "/settings", label: "Settings" },
];

export function NavBar() {
  const router = useRouter();
  // Server snapshot is null (logged-out) — matches useRequireAuth, so no
  // hydration mismatch; the real token is read after hydration.
  const token = useSyncExternalStore(subscribe, getAccessToken, () => null);
  const authed = token !== null;

  async function onLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <header className="border-b border-zinc-200">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-6 py-3">
        <Link href={authed ? "/dashboard" : "/"} className="font-semibold tracking-tight">
          Wealth-Lens
        </Link>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
          {authed ? (
            <>
              {NAV_LINKS.map((l) => (
                <Link key={l.href} href={l.href} className="text-zinc-600 hover:text-zinc-900">
                  {l.label}
                </Link>
              ))}
              <button
                type="button"
                onClick={onLogout}
                className="rounded border border-zinc-300 px-3 py-1 hover:bg-zinc-50"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-zinc-600 hover:text-zinc-900">
                Sign in
              </Link>
              <Link href="/register" className="rounded bg-zinc-900 px-3 py-1 text-white">
                Create account
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
