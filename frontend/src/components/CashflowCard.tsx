"use client";

import { formatMoney, formatPercent } from "@/lib/format";
import { useAuthedQuery } from "@/lib/useAuthedQuery";

// Backend Decimals serialize as JSON strings (see formatMoney); only `float`
// (years_to_fi) and `int` (window_months) arrive as real numbers.
type CashflowSummary = {
  base_currency: string;
  as_of: string;
  window_months: number;
  savings_rate: string | null; // Decimal fraction, e.g. "0.4" = 40%
  monthly_expenses: string;
  runway_months: string | null; // Decimal months
  annual_expenses: string;
  fi_number: string;
  years_to_fi: number | null; // float
  withdrawal_rate: string; // Decimal, e.g. "0.04"
  annual_real_return: string; // Decimal, e.g. "0.05"
};

const DASH = "—";

export function CashflowCard() {
  const state = useAuthedQuery<CashflowSummary>(
    "/api/v1/dashboard/cashflow-summary?base=SGD&months=12",
  );

  return (
    <div className="rounded-lg border border-zinc-200 p-5">
      <h2 className="text-sm font-medium text-zinc-500">Cash flow / FI</h2>

      {state.kind === "loading" && (
        <p role="status" className="mt-2 text-zinc-500">
          Loading…
        </p>
      )}
      {state.kind === "error" && (
        <p role="alert" className="mt-2 text-red-700">
          Couldn’t load cash flow: {state.message}
        </p>
      )}
      {state.kind === "ok" && (
        <>
          <dl className="mt-3 grid grid-cols-2 gap-4">
            <div>
              <dt className="text-xs text-zinc-500">Savings rate</dt>
              <dd className="mt-1 text-2xl font-semibold tabular-nums">
                {state.data.savings_rate === null
                  ? DASH
                  : `${(Number(state.data.savings_rate) * 100).toFixed(0)}%`}
              </dd>
              {state.data.savings_rate === null && (
                <p className="mt-1 text-xs text-zinc-500">No income recorded</p>
              )}
            </div>

            <div>
              <dt className="text-xs text-zinc-500">Emergency runway</dt>
              <dd className="mt-1 text-2xl font-semibold tabular-nums">
                {state.data.runway_months === null
                  ? DASH
                  : `${Number(state.data.runway_months).toFixed(1)} months`}
              </dd>
              {state.data.runway_months === null && (
                <p className="mt-1 text-xs text-zinc-500">No expenses recorded</p>
              )}
            </div>

            <div>
              <dt className="text-xs text-zinc-500">Years to FI</dt>
              <dd className="mt-1 text-2xl font-semibold tabular-nums">
                {state.data.years_to_fi === null
                  ? DASH
                  : `${state.data.years_to_fi.toFixed(1)} years`}
              </dd>
              {state.data.years_to_fi === null && (
                <p className="mt-1 text-xs text-zinc-500">
                  Not reachable at current savings
                </p>
              )}
            </div>

            <div>
              <dt className="text-xs text-zinc-500">FI number (target)</dt>
              <dd className="mt-1 text-2xl font-semibold tabular-nums">
                {formatMoney(state.data.fi_number, state.data.base_currency)}
              </dd>
            </div>
          </dl>

          <p className="mt-4 text-xs text-zinc-500">
            Projected at {formatPercent(state.data.withdrawal_rate)} withdrawal rate
            and {formatPercent(state.data.annual_real_return)} real return.
          </p>
        </>
      )}
    </div>
  );
}
