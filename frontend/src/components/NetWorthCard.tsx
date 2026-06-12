"use client";

import { formatMoney } from "@/lib/format";
import { useAuthedQuery } from "@/lib/useAuthedQuery";

type NetWorth = { base_currency: string; as_of: string; total: string };

export function NetWorthCard() {
  const state = useAuthedQuery<NetWorth>("/api/v1/dashboard/net-worth?base=SGD");

  return (
    <div className="rounded-lg border border-zinc-200 p-5">
      <h2 className="text-sm font-medium text-zinc-500">Net worth</h2>
      {state.kind === "loading" && (
        <p role="status" className="mt-2 text-zinc-500">
          Loading…
        </p>
      )}
      {state.kind === "error" && (
        <p role="alert" className="mt-2 text-red-700">
          Couldn’t load net worth: {state.message}
        </p>
      )}
      {state.kind === "ok" && (
        <>
          <p className="mt-2 text-3xl font-semibold tabular-nums">
            {formatMoney(state.data.total, state.data.base_currency)}
          </p>
          <p className="mt-1 text-xs text-zinc-500">as of {state.data.as_of}</p>
        </>
      )}
    </div>
  );
}
