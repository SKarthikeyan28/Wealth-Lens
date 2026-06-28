"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { clearTokens } from "@/lib/auth";
import { useRequireAuth } from "@/lib/useRequireAuth";

const inputCls = "rounded border border-zinc-300 px-3 py-2 text-sm";

function TwoFactorSection() {
  const [enrol, setEnrol] = useState<{ provisioning_uri: string; secret: string } | null>(null);
  const [code, setCode] = useState("");
  const [recovery, setRecovery] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onEnrol() {
    setBusy(true);
    setError(null);
    try {
      const res = await apiPost<{ provisioning_uri: string; secret: string }>(
        "/api/v1/auth/totp/enroll",
        {},
        true,
      );
      setEnrol(res);
      setRecovery(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start enrolment");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirm(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await apiPost<{ recovery_codes: string[] }>(
        "/api/v1/auth/totp/confirm",
        { totp_code: code },
        true,
      );
      setRecovery(res.recovery_codes);
      setEnrol(null);
      setCode("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid code");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-zinc-200 p-5">
      <h2 className="text-lg font-medium">Two-factor authentication</h2>
      <p className="mt-1 text-sm text-zinc-600">
        Add a time-based one-time password (TOTP) from an authenticator app for a second login
        factor.
      </p>

      {error && (
        <p role="alert" className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {!enrol && !recovery && (
        <button
          type="button"
          onClick={onEnrol}
          disabled={busy}
          className="mt-3 rounded bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {busy ? "Starting…" : "Enable 2FA"}
        </button>
      )}

      {enrol && (
        <div className="mt-4 text-sm">
          <p className="text-zinc-600">
            Add this secret to your authenticator app, then enter the 6-digit code to confirm.
          </p>
          <p className="mt-2">
            Secret: <code className="rounded bg-zinc-100 px-2 py-1 font-mono">{enrol.secret}</code>
          </p>
          <p className="mt-1 break-all text-xs text-zinc-500">{enrol.provisioning_uri}</p>
          <form onSubmit={onConfirm} className="mt-3 flex flex-wrap items-end gap-2">
            <label className="flex flex-col gap-1">
              Authenticator code
              <input
                required
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className={inputCls}
              />
            </label>
            <button
              type="submit"
              disabled={busy}
              className="rounded bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {busy ? "Confirming…" : "Confirm"}
            </button>
          </form>
        </div>
      )}

      {recovery && (
        <div className="mt-4 text-sm">
          <p className="font-medium text-green-700">2FA enabled.</p>
          <p className="mt-1 text-zinc-600">
            Save these one-time recovery codes somewhere safe — they are shown only once.
          </p>
          <ul className="mt-2 grid grid-cols-2 gap-1 font-mono text-xs">
            {recovery.map((c) => (
              <li key={c} className="rounded bg-zinc-100 px-2 py-1">
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function DataSection() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [password, setPassword] = useState("");

  async function onExport() {
    setBusy(true);
    setError(null);
    try {
      const data = await apiGet<unknown>("/api/v1/account/export", true);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "wealth-lens-export.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(e: React.FormEvent) {
    e.preventDefault();
    if (!window.confirm("Permanently delete your account? This cannot be undone.")) return;
    setBusy(true);
    setError(null);
    try {
      await apiDelete("/api/v1/account", true, { password });
      clearTokens();
      router.replace("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Deletion failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-zinc-200 p-5">
      <h2 className="text-lg font-medium">Your data</h2>
      <p className="mt-1 text-sm text-zinc-600">
        Export everything we hold about you, or delete your account. Deletion removes your data while
        preserving the immutable audit trail required for integrity.
      </p>

      {error && (
        <p role="alert" className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={onExport}
        disabled={busy}
        className="mt-3 rounded border border-zinc-300 px-4 py-2 text-sm disabled:opacity-50"
      >
        {busy ? "Working…" : "Export my data (JSON)"}
      </button>

      <form onSubmit={onDelete} className="mt-6 border-t border-zinc-100 pt-4">
        <h3 className="text-sm font-medium text-red-700">Delete account</h3>
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1 text-sm">
            Confirm with your password
            <input
              required
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputCls}
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-red-700 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            Delete account
          </button>
        </div>
      </form>
    </div>
  );
}

export default function SettingsPage() {
  const ready = useRequireAuth();

  if (!ready) {
    return (
      <p role="status" className="p-6">
        Loading…
      </p>
    );
  }

  return (
    <section className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      <div className="mt-8 grid gap-6">
        <TwoFactorSection />
        <DataSection />
      </div>
    </section>
  );
}
