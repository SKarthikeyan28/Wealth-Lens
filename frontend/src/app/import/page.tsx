"use client";

import Link from "next/link";
import { useState } from "react";

import { apiUpload } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

type Receipt = {
  id: string;
  source: string;
  filename: string;
  total_rows: number;
  inserted: number;
  skipped_duplicates: number;
  failed: number;
  errors: Record<string, unknown>[];
  created_at: string;
};

export default function ImportPage() {
  const ready = useRequireAuth();
  const [file, setFile] = useState<File | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    setReceipt(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await apiUpload<Receipt>("/api/v1/imports/expenses", fd, true);
      setReceipt(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  if (!ready) {
    return (
      <p role="status" className="p-6">
        Loading…
      </p>
    );
  }

  return (
    <section className="mx-auto max-w-2xl px-6 py-12">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Import expenses</h1>
        <Link href="/cashflow" className="rounded border border-zinc-300 px-3 py-1.5 text-sm">
          Back to cashflow
        </Link>
      </div>
      <p className="mt-1 text-sm text-zinc-600">
        Upload a CSV of expenses. Imports are idempotent — re-uploading the same file skips rows
        that were already imported, so you can safely retry.
      </p>

      {error && (
        <p role="alert" className="mt-4 rounded bg-red-50 p-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <form onSubmit={onSubmit} className="mt-6 flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm"
        />
        <button
          type="submit"
          disabled={busy || !file}
          className="rounded bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {busy ? "Importing…" : "Import"}
        </button>
      </form>

      {receipt && (
        <div className="mt-8 rounded-lg border border-zinc-200 p-5">
          <h2 className="text-sm font-medium text-zinc-500">Import receipt</h2>
          <p className="mt-1 text-sm text-zinc-600">{receipt.filename}</p>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-zinc-500">Total rows</dt>
              <dd className="tabular-nums">{receipt.total_rows}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Imported</dt>
              <dd className="tabular-nums text-green-700">{receipt.inserted}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Skipped (dupes)</dt>
              <dd className="tabular-nums">{receipt.skipped_duplicates}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Failed</dt>
              <dd className="tabular-nums text-red-700">{receipt.failed}</dd>
            </div>
          </dl>

          {receipt.errors.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-medium text-zinc-700">Row errors</h3>
              <ul className="mt-2 grid gap-1 text-xs text-red-700">
                {receipt.errors.map((err, i) => (
                  <li key={i} className="font-mono">
                    {JSON.stringify(err)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
