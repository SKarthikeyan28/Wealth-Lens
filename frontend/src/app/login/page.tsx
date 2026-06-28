"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiPost } from "@/lib/api";
import { setTokens } from "@/lib/auth";

type LoginResponse = {
  requires_2fa: boolean;
  access_token: string | null;
  refresh_token: string | null;
  pre_auth_token: string | null;
};
type TokenResponse = { access_token: string; refresh_token: string };

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [preAuth, setPreAuth] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await apiPost<LoginResponse>("/api/v1/auth/login", { email, password });
      if (res.requires_2fa) {
        setPreAuth(res.pre_auth_token);
      } else if (res.access_token && res.refresh_token) {
        setTokens(res.access_token, res.refresh_token);
        router.replace("/dashboard");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function onVerify(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await apiPost<TokenResponse>("/api/v1/auth/totp/verify", {
        pre_auth_token: preAuth,
        totp_code: totp,
      });
      setTokens(res.access_token, res.refresh_token);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto max-w-sm px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>

      {error && (
        <p role="alert" className="mt-4 rounded bg-red-50 p-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {preAuth === null ? (
        <form onSubmit={onLogin} className="mt-6 flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm">
            Email
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded border border-zinc-300 px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Password
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded border border-zinc-300 px-3 py-2"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-zinc-900 px-4 py-2 text-white disabled:opacity-50"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <p className="text-sm text-zinc-600">
            No account yet?{" "}
            <Link href="/register" className="underline">
              Create one
            </Link>
          </p>
        </form>
      ) : (
        <form onSubmit={onVerify} className="mt-6 flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm">
            Authenticator code
            <input
              inputMode="numeric"
              required
              autoComplete="one-time-code"
              value={totp}
              onChange={(e) => setTotp(e.target.value)}
              className="rounded border border-zinc-300 px-3 py-2"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-zinc-900 px-4 py-2 text-white disabled:opacity-50"
          >
            {busy ? "Verifying…" : "Verify"}
          </button>
        </form>
      )}
    </section>
  );
}
