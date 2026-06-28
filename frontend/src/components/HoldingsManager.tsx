"use client";

import { useCallback, useEffect, useState } from "react";

import { apiDelete, apiGet, apiPost } from "@/lib/api";

type AssetClass = "EQUITY" | "ETF" | "REIT" | "BOND" | "PRECIOUS_METAL" | "CASH_EQUIVALENT";
type Holding = {
  id: string;
  account_id: string;
  security_id: string;
  quantity: string;
  avg_cost: string;
  created_at: string;
};

const ASSET_CLASSES: AssetClass[] = [
  "EQUITY",
  "ETF",
  "REIT",
  "BOND",
  "PRECIOUS_METAL",
  "CASH_EQUIVALENT",
];

const inputCls = "rounded border border-zinc-300 px-3 py-2";

export function HoldingsManager({
  accountId,
  defaultCurrency,
}: {
  accountId: string;
  defaultCurrency: string;
}) {
  const [holdings, setHoldings] = useState<Holding[] | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [ticker, setTicker] = useState("");
  const [exchange, setExchange] = useState("");
  const [assetClass, setAssetClass] = useState<AssetClass>("ETF");
  const [currency, setCurrency] = useState(defaultCurrency);
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [avgCost, setAvgCost] = useState("");
  const [busy, setBusy] = useState(false);

  // setState lives in .then/.catch closures (deferred) — React 19 forbids sync
  // setState in effects, and the lint rule treats await-based setState as sync.
  const reload = useCallback(() => {
    return apiGet<Holding[]>(`/api/v1/holdings?account_id=${accountId}`, true)
      .then((rows) => {
        setError(null);
        setHoldings(rows);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load holdings");
        setHoldings([]);
      });
  }, [accountId]);

  useEffect(() => {
    if (open && holdings === null) void reload();
  }, [open, holdings, reload]);

  async function onAdd(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await apiPost(
        "/api/v1/holdings",
        {
          account_id: accountId,
          ticker,
          exchange: exchange || null,
          asset_class: assetClass,
          currency,
          name: name || null,
          quantity,
          avg_cost: avgCost,
        },
        true,
      );
      setTicker("");
      setExchange("");
      setName("");
      setQuantity("");
      setAvgCost("");
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add holding");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: string) {
    if (!window.confirm("Remove this holding?")) return;
    setError(null);
    try {
      await apiDelete(`/api/v1/holdings/${id}`, true);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to remove holding");
    }
  }

  return (
    <div className="mt-4 border-t border-zinc-100 pt-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="text-sm font-medium text-zinc-700 underline"
        aria-expanded={open}
      >
        {open ? "Hide holdings" : "Manage holdings"}
      </button>

      {open && (
        <div className="mt-3">
          {error && (
            <p role="alert" className="mb-2 rounded bg-red-50 p-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <form onSubmit={onAdd} className="grid gap-2 text-sm sm:grid-cols-3">
            <label className="flex flex-col gap-1">
              Ticker
              <input
                required
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className={inputCls}
              />
            </label>
            <label className="flex flex-col gap-1">
              Exchange (optional)
              <input
                value={exchange}
                onChange={(e) => setExchange(e.target.value.toUpperCase())}
                className={inputCls}
              />
            </label>
            <label className="flex flex-col gap-1">
              Asset class
              <select
                value={assetClass}
                onChange={(e) => setAssetClass(e.target.value as AssetClass)}
                className={inputCls}
              >
                {ASSET_CLASSES.map((c) => (
                  <option key={c} value={c}>
                    {c}
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
              Name (optional)
              <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
            </label>
            <label className="flex flex-col gap-1">
              Quantity
              <input
                required
                type="number"
                min="0"
                step="any"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className={inputCls}
              />
            </label>
            <label className="flex flex-col gap-1">
              Avg cost
              <input
                required
                type="number"
                min="0"
                step="any"
                value={avgCost}
                onChange={(e) => setAvgCost(e.target.value)}
                className={inputCls}
              />
            </label>
            <div className="sm:col-span-3">
              <button
                type="submit"
                disabled={busy}
                className="rounded bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                {busy ? "Adding…" : "Add holding"}
              </button>
            </div>
          </form>

          <div className="mt-4">
            {holdings === null ? (
              <p role="status" className="text-sm text-zinc-500">
                Loading holdings…
              </p>
            ) : holdings.length === 0 ? (
              <p className="text-sm text-zinc-500">No holdings in this account yet.</p>
            ) : (
              <ul className="grid gap-2">
                {holdings.map((h) => (
                  <li
                    key={h.id}
                    className="flex items-center justify-between rounded border border-zinc-200 px-3 py-2 text-sm"
                  >
                    <span className="tabular-nums">
                      {h.quantity} units @ {h.avg_cost}
                    </span>
                    <button
                      type="button"
                      onClick={() => onDelete(h.id)}
                      className="text-red-700 hover:underline"
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
