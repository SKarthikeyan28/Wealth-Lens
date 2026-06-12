"use client";

import { formatMoney, formatPercent } from "@/lib/format";
import { useAuthedQuery } from "@/lib/useAuthedQuery";

type Slice = { asset_class: string; value: string; weight: string };
type Allocation = { base_currency: string; as_of: string; total: string; slices: Slice[] };

export function AllocationChart() {
  const state = useAuthedQuery<Allocation>("/api/v1/dashboard/allocation?base=SGD");

  return (
    <div className="rounded-lg border border-zinc-200 p-5">
      <h2 className="text-sm font-medium text-zinc-500">Allocation</h2>

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
          No positions yet. Add an account or holding to see your allocation.
        </p>
      )}
      {state.kind === "ok" && state.data.slices.length > 0 && (
        <ul className="mt-3 flex flex-col gap-3">
          {state.data.slices.map((s) => (
            <li key={s.asset_class}>
              <div className="flex justify-between text-sm">
                <span>{s.asset_class}</span>
                <span className="tabular-nums">
                  {formatMoney(s.value, state.data.base_currency)} · {formatPercent(s.weight)}
                </span>
              </div>
              {/* Decorative bar; the numbers above are the accessible source of truth. */}
              <div className="mt-1 h-2 rounded bg-zinc-100" aria-hidden="true">
                <div
                  className="h-2 rounded bg-zinc-800"
                  style={{ width: formatPercent(s.weight) }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
