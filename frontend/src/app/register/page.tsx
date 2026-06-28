"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiPost } from "@/lib/api";
import { setTokens } from "@/lib/auth";

type UserResponse = { id: string; email: string; created_at: string };
type LoginResponse = {
  requires_2fa: boolean;
  access_token: string | null;
  refresh_token: string | null;
  pre_auth_token: string | null;
};

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onRegister(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setBusy(true);
    try {
      // 1. Create the account. Returns the user record, NOT tokens.
      await apiPost<UserResponse>("/api/v1/auth/register", { email, password });

      // 2. Immediately log in so the user lands authenticated, not back at a form.
      const res = await apiPost<LoginResponse>("/api/v1/auth/login", { email, password });
      if (res.access_token && res.refresh_token) {
        setTokens(res.access_token, res.refresh_token);
        router.replace("/dashboard");
      } else {
        // A fresh account shouldn't require 2FA, but route there defensively.
        router.replace("/login");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto max-w-sm px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">Create account</h1>

      {error && (
        <p role="alert" className="mt-4 rounded bg-red-50 p-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <form onSubmit={onRegister} className="mt-6 flex flex-col gap-4">
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
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded border border-zinc-300 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Confirm password
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="rounded border border-zinc-300 px-3 py-2"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="rounded bg-zinc-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className="mt-4 text-sm text-zinc-600">
        Already have an account?{" "}
        <Link href="/login" className="underline">
          Sign in
        </Link>
      </p>
    </section>
  );
}
