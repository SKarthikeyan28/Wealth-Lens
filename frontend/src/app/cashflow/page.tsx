"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { useRequireAuth } from "@/lib/useRequireAuth";

type IncomeSource = "SALARY" | "BONUS" | "DIVIDEND" | "MISC";
type Income = {
  id: string;
  source_type: IncomeSource;
  amount: string;
  currency: string;
  received_on: string;
  note: string | null;
};
type Expense = {
  id: string;
  category: string;
  amount: string;
  currency: string;
  spent_on: string;
  note: string | null;
};

const INCOME_SOURCES: IncomeSource[] = ["SALARY", "BONUS", "DIVIDEND", "MISC"];
const inputCls = "rounded border border-zinc-300 px-3 py-2";
const today = () => new Date().toISOString().slice(0, 10);

export default function CashflowPage() {
  const ready = useRequireAuth();
  const [income, setIncome] = useState<Income[] | null>(null);
  const [expenses, setExpenses] = useState<Expense[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // income form
  const [sourceType, setSourceType] = useState<IncomeSource>("SALARY");
  const [incAmount, setIncAmount] = useState("");
  const [incCurrency, setIncCurrency] = useState("SGD");
  const [receivedOn, setReceivedOn] = useState(today());
  const [incNote, setIncNote] = useState("");
  const [incBusy, setIncBusy] = useState(false);

  // expense form
  const [category, setCategory] = useState("");
  const [expAmount, setExpAmount] = useState("");
  const [expCurrency, setExpCurrency] = useState("SGD");
  const [spentOn, setSpentOn] = useState(today());
  const [expNote, setExpNote] = useState("");
  const [expBusy, setExpBusy] = useState(false);

  // setState lives in .then/.catch closures (deferred) — React 19 forbids sync
  // setState in effects, and the lint rule treats await-based setState as sync.
  const reload = useCallback(() => {
    return Promise.all([
      apiGet<Income[]>("/api/v1/income", true),
      apiGet<Expense[]>("/api/v1/expenses", true),
    ])
      .then(([inc, exp]) => {
        setError(null);
        setIncome(inc);
        setExpenses(exp);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load cashflow");
        setIncome([]);
        setExpenses([]);
      });
  }, []);

  useEffect(() => {
    if (ready) void reload();
  }, [ready, reload]);

  async function onAddIncome(e: React.FormEvent) {
    e.preventDefault();
    setIncBusy(true);
    setError(null);
    try {
      await apiPost(
        "/api/v1/income",
        {
          source_type: sourceType,
          amount: incAmount,
          currency: incCurrency,
          received_on: receivedOn,
          note: incNote || null,
        },
        true,
      );
      setIncAmount("");
      setIncNote("");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add income");
    } finally {
      setIncBusy(false);
    }
  }

  async function onAddExpense(e: React.FormEvent) {
    e.preventDefault();
    setExpBusy(true);
    setError(null);
    try {
      await apiPost(
        "/api/v1/expenses",
        {
          category,
          amount: expAmount,
          currency: expCurrency,
          spent_on: spentOn,
          note: expNote || null,
        },
        true,
      );
      setCategory("");
      setExpAmount("");
      setExpNote("");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add expense");
    } finally {
      setExpBusy(false);
    }
  }

  async function onDelete(kind: "income" | "expenses", id: string) {
    if (!window.confirm("Delete this entry?")) return;
    setError(null);
    try {
      await apiDelete(`/api/v1/${kind}/${id}`, true);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete entry");
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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Cashflow</h1>
        <Link href="/import" className="rounded border border-zinc-300 px-3 py-1.5 text-sm">
          Import expenses (CSV)
        </Link>
      </div>
      <p className="mt-1 text-sm text-zinc-600">
        Record income and expenses. These drive your savings rate, emergency runway and years-to-FI.
      </p>

      {error && (
        <p role="alert" className="mt-4 rounded bg-red-50 p-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        {/* Income */}
        <div>
          <h2 className="text-lg font-medium">Income</h2>
          <form onSubmit={onAddIncome} className="mt-3 grid gap-2 text-sm">
            <label className="flex flex-col gap-1">
              Source
              <select
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value as IncomeSource)}
                className={inputCls}
              >
                {INCOME_SOURCES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex flex-col gap-1">
                Amount
                <input
                  required
                  type="number"
                  min="0"
                  step="0.01"
                  value={incAmount}
                  onChange={(e) => setIncAmount(e.target.value)}
                  className={inputCls}
                />
              </label>
              <label className="flex flex-col gap-1">
                Currency
                <input
                  required
                  maxLength={3}
                  value={incCurrency}
                  onChange={(e) => setIncCurrency(e.target.value.toUpperCase())}
                  className={inputCls}
                />
              </label>
            </div>
            <label className="flex flex-col gap-1">
              Received on
              <input
                required
                type="date"
                value={receivedOn}
                onChange={(e) => setReceivedOn(e.target.value)}
                className={inputCls}
              />
            </label>
            <label className="flex flex-col gap-1">
              Note (optional)
              <input value={incNote} onChange={(e) => setIncNote(e.target.value)} className={inputCls} />
            </label>
            <button
              type="submit"
              disabled={incBusy}
              className="mt-1 rounded bg-zinc-900 px-4 py-2 text-white disabled:opacity-50"
            >
              {incBusy ? "Adding…" : "Add income"}
            </button>
          </form>

          <ul className="mt-4 grid gap-2">
            {income === null ? (
              <li role="status" className="text-sm text-zinc-500">
                Loading…
              </li>
            ) : income.length === 0 ? (
              <li className="text-sm text-zinc-500">No income recorded yet.</li>
            ) : (
              income.map((i) => (
                <li
                  key={i.id}
                  className="flex items-center justify-between rounded border border-zinc-200 px-3 py-2 text-sm"
                >
                  <span>
                    <span className="tabular-nums">{formatMoney(i.amount, i.currency)}</span>{" "}
                    <span className="text-zinc-500">
                      · {i.source_type} · {i.received_on}
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={() => onDelete("income", i.id)}
                    className="text-red-700 hover:underline"
                  >
                    Delete
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>

        {/* Expenses */}
        <div>
          <h2 className="text-lg font-medium">Expenses</h2>
          <form onSubmit={onAddExpense} className="mt-3 grid gap-2 text-sm">
            <label className="flex flex-col gap-1">
              Category
              <input
                required
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className={inputCls}
              />
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex flex-col gap-1">
                Amount
                <input
                  required
                  type="number"
                  min="0"
                  step="0.01"
                  value={expAmount}
                  onChange={(e) => setExpAmount(e.target.value)}
                  className={inputCls}
                />
              </label>
              <label className="flex flex-col gap-1">
                Currency
                <input
                  required
                  maxLength={3}
                  value={expCurrency}
                  onChange={(e) => setExpCurrency(e.target.value.toUpperCase())}
                  className={inputCls}
                />
              </label>
            </div>
            <label className="flex flex-col gap-1">
              Spent on
              <input
                required
                type="date"
                value={spentOn}
                onChange={(e) => setSpentOn(e.target.value)}
                className={inputCls}
              />
            </label>
            <label className="flex flex-col gap-1">
              Note (optional)
              <input value={expNote} onChange={(e) => setExpNote(e.target.value)} className={inputCls} />
            </label>
            <button
              type="submit"
              disabled={expBusy}
              className="mt-1 rounded bg-zinc-900 px-4 py-2 text-white disabled:opacity-50"
            >
              {expBusy ? "Adding…" : "Add expense"}
            </button>
          </form>

          <ul className="mt-4 grid gap-2">
            {expenses === null ? (
              <li role="status" className="text-sm text-zinc-500">
                Loading…
              </li>
            ) : expenses.length === 0 ? (
              <li className="text-sm text-zinc-500">No expenses recorded yet.</li>
            ) : (
              expenses.map((x) => (
                <li
                  key={x.id}
                  className="flex items-center justify-between rounded border border-zinc-200 px-3 py-2 text-sm"
                >
                  <span>
                    <span className="tabular-nums">{formatMoney(x.amount, x.currency)}</span>{" "}
                    <span className="text-zinc-500">
                      · {x.category} · {x.spent_on}
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={() => onDelete("expenses", x.id)}
                    className="text-red-700 hover:underline"
                  >
                    Delete
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      </div>
    </section>
  );
}
