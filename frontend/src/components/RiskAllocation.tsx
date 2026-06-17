"use client";

import { formatPercent } from "@/lib/format";
import { useAuthedQuery } from "@/lib/useAuthedQuery";

// crra_gamma is a backend Decimal → JSON string. expected_return, volatility and
// each slice weight are backend `float` → JS numbers.
type Slice = { ticker: string; weight: number };
type Allocation = {
  crra_gamma: string;
  expected_return: number;
  volatility: number;
  slices: Slice[];
};

export function RiskAllocation() {
  const state = useAuthedQuery<Allocation>("/api/v1/risk/allocation");

  return (
    <div className="rounded-lg border border-zinc-200 p-5">
      <h2 className="text-sm font-medium text-zinc-500">Optimal allocation</h2>

      {state.kind === "loading" && (
        <p role="status" className="mt-2 text-zinc-500">
          Loading…
        </p>
      )}
      {state.kind === "error" && (
        <p role="alert" className="mt-2 text-red-700">
          Couldn’t load allocation: {state.message}
        </p>
      )}
      {state.kind === "ok" && state.data.slices.length === 0 && (
        <p className="mt-2 text-zinc-500">
          No allocation available. Add market data or holdings to see your optimal
          mix.
        </p>
      )}
      {state.kind === "ok" && state.data.slices.length > 0 && (
        <>
          <dl className="mt-3 grid grid-cols-2 gap-4">
            <div>
              <dt className="text-xs text-zinc-500">Expected return (annual)</dt>
              <dd className="mt-1 text-2xl font-semibold tabular-nums">
                {(state.data.expected_return * 100).toFixed(1)}%
              </dd>
            </div>
            <div>
              <dt className="text-xs text-zinc-500">Volatility (annual)</dt>
              <dd className="mt-1 text-2xl font-semibold tabular-nums">
                {(state.data.volatility * 100).toFixed(1)}%
              </dd>
            </div>
          </dl>

          <ul className="mt-4 flex flex-col gap-3">
            {state.data.slices.map((s) => (
              <li key={s.ticker}>
                <div className="flex justify-between text-sm">
                  <span>{s.ticker}</span>
                  <span className="tabular-nums">{formatPercent(String(s.weight))}</span>
                </div>
                {/* Decorative bar; the numbers above are the accessible source of truth. */}
                <div className="mt-1 h-2 rounded bg-zinc-100" aria-hidden="true">
                  <div
                    className="h-2 rounded bg-zinc-800"
                    style={{ width: formatPercent(String(s.weight)) }}
                  />
                </div>
              </li>
            ))}
          </ul>

          <p className="mt-4 text-xs text-zinc-500">
            Annualised, model-based estimates for risk aversion γ ≈{" "}
            {Number(state.data.crra_gamma).toFixed(2)}. Educational simulation, not
            investment advice.
          </p>
        </>
      )}
    </div>
  );
}
