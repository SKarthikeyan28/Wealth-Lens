"use client";

import { useCallback, useEffect, useState } from "react";

import { HoldingsManager } from "@/components/HoldingsManager";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { useRequireAuth } from "@/lib/useRequireAuth";

type AccountType = "CASH" | "BROKERAGE" | "CPF_OA" | "CPF_SA" | "CPF_MA" | "SRS";
type Account = {
  id: string;
  name: string;
  account_type: AccountType;
  currency: string;
  cash_balance: string;
  created_at: string;
};

const ACCOUNT_TYPES: AccountType[] = ["CASH", "BROKERAGE", "CPF_OA", "CPF_SA", "CPF_MA", "SRS"];
const inputCls = "rounded border border-zinc-300 px-3 py-2";

function AccountRow({
  account,
  onChanged,
  onError,
}: {
  account: Account;
  onChanged: () => Promise<void>;
  onError: (msg: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(account.name);
  const [currency, setCurrency] = useState(account.currency);
  const [cashBalance, setCashBalance] = useState(account.cash_balance);
  const [busy, setBusy] = useState(false);

  async function onSave() {
    setBusy(true);
    try {
      await apiPatch(
        `/api/v1/accounts/${account.id}`,
        { name, currency, cash_balance: cashBalance },
        true,
      );
      setEditing(false);
      await onChanged();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to update account");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete() {
    if (!window.confirm("Delete this account? This cannot be undone.")) return;
    try {
      await apiDelete(`/api/v1/accounts/${account.id}`, true);
      await onChanged();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to delete account");
    }
  }

  return (
    <li className="rounded-lg border border-zinc-200 p-4">
      {editing ? (
        <div className="grid gap-2 text-sm sm:grid-cols-3">
          <label className="flex flex-col gap-1">
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
          </label>
          <label className="flex flex-col gap-1">
            Currency
            <input
              maxLength={3}
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              className={inputCls}
            />
          </label>
          <label className="flex flex-col gap-1">
            Cash balance
            <input
              type="number"
              min="0"
              step="0.01"
              value={cashBalance}
              onChange={(e) => setCashBalance(e.target.value)}
              className={inputCls}
            />
          </label>
          <div className="flex gap-2 sm:col-span-3">
            <button
              type="button"
              onClick={onSave}
              disabled={busy}
              className="rounded bg-zinc-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
            >
              {busy ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="rounded border border-zinc-300 px-3 py-1.5 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-medium">{account.name}</p>
            <p className="text-xs text-zinc-500">
              {account.account_type} · {account.currency}
            </p>
            <p className="mt-1 tabular-nums">
              {formatMoney(account.cash_balance, account.currency)}
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="rounded border border-zinc-300 px-3 py-1 text-sm"
            >
              Edit
            </button>
            <button
              type="button"
              onClick={onDelete}
              className="rounded border border-zinc-300 px-3 py-1 text-sm text-red-700 hover:bg-red-50"
            >
              Delete
            </button>
          </div>
        </div>
      )}

      {account.account_type === "BROKERAGE" && (
        <HoldingsManager accountId={account.id} defaultCurrency={account.currency} />
      )}
    </li>
  );
}

export default function AccountsPage() {
  const ready = useRequireAuth();
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [accountType, setAccountType] = useState<AccountType>("CASH");
  const [currency, setCurrency] = useState("SGD");
  const [cashBalance, setCashBalance] = useState("0");
  const [busy, setBusy] = useState(false);

  // setState lives in .then/.catch closures (deferred) — React 19 forbids sync
  // setState in effects, and the lint rule treats await-based setState as sync.
  const reload = useCallback(() => {
    return apiGet<Account[]>("/api/v1/accounts", true)
      .then((rows) => {
        setError(null);
        setAccounts(rows);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load accounts");
        setAccounts([]);
      });
  }, []);

  useEffect(() => {
    if (ready) void reload();
  }, [ready, reload]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await apiPost(
        "/api/v1/accounts",
        { name, account_type: accountType, currency, cash_balance: cashBalance },
        true,
      );
      setName("");
      setCashBalance("0");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create account");
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
    <section className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Accounts</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Add your cash, brokerage, CPF and SRS accounts. These feed your net worth, allocation and
        runway. Add holdings to a brokerage account to drive the risk and projection tools.
      </p>

      {error && (
        <p role="alert" className="mt-4 rounded bg-red-50 p-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <form
        onSubmit={onCreate}
        className="mt-6 grid gap-3 rounded-lg border border-zinc-200 p-4 text-sm sm:grid-cols-2"
      >
        <label className="flex flex-col gap-1">
          Name
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputCls}
          />
        </label>
        <label className="flex flex-col gap-1">
          Type
          <select
            value={accountType}
            onChange={(e) => setAccountType(e.target.value as AccountType)}
            className={inputCls}
          >
            {ACCOUNT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Currency
          <input
            required
            maxLength={3}
            value={currency}
            onChange={(e) => setCurrency(e.target.value.toUpperCase())}
            className={inputCls}
          />
        </label>
        <label className="flex flex-col gap-1">
          Cash balance
          <input
            type="number"
            min="0"
            step="0.01"
            value={cashBalance}
            onChange={(e) => setCashBalance(e.target.value)}
            className={inputCls}
          />
        </label>
        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-zinc-900 px-4 py-2 text-white disabled:opacity-50"
          >
            {busy ? "Adding…" : "Add account"}
          </button>
        </div>
      </form>

      <div className="mt-8">
        {accounts === null ? (
          <p role="status" className="text-zinc-500">
            Loading accounts…
          </p>
        ) : accounts.length === 0 ? (
          <p className="text-zinc-500">No accounts yet. Add your first one above.</p>
        ) : (
          <ul className="grid gap-4">
            {accounts.map((a) => (
              <AccountRow key={a.id} account={a} onChanged={reload} onError={setError} />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
