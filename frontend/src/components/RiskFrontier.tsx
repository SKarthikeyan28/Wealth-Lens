"use client";

import { useAuthedQuery } from "@/lib/useAuthedQuery";

// All numeric fields are backend `float` → JS numbers and are fractions
// (0.052 = 5.2%); render as percents via (x * 100).toFixed(1).
// EXCEPTION: crra_gamma is a backend Decimal → JSON string; wrap in Number()
// before any arithmetic / .toFixed.
type FrontierPoint = { expected_return: number; volatility: number };
type Frontier = {
  frontier: FrontierPoint[];
  user_return: number | null;
  user_volatility: number | null;
  optimal_return: number | null;
  optimal_volatility: number | null;
  crra_gamma: string | null;
};

const pct = (x: number) => (x * 100).toFixed(1);

// Best return achievable at or below the user's risk: the frontier point with
// the largest volatility that is still <= the user's volatility.
function bestAtOrBelow(
  frontier: FrontierPoint[],
  userVol: number,
): FrontierPoint | null {
  let best: FrontierPoint | null = null;
  for (const p of frontier) {
    if (p.volatility <= userVol) {
      if (best === null || p.volatility > best.volatility) best = p;
    }
  }
  return best;
}

export function RiskFrontier() {
  const state = useAuthedQuery<Frontier>("/api/v1/risk/frontier");

  return (
    <div className="rounded-lg border border-zinc-200 p-5">
      <h2 className="text-sm font-medium text-zinc-500">Efficient frontier</h2>

      {state.kind === "loading" && (
        <p role="status" className="mt-2 text-zinc-500">
          Loading…
        </p>
      )}
      {state.kind === "error" && (
        <p role="alert" className="mt-2 text-red-700">
          Couldn’t load frontier: {state.message}
        </p>
      )}
      {state.kind === "ok" && state.data.frontier.length === 0 && (
        <p className="mt-2 text-zinc-500">
          No frontier available. Add market data to see the efficient frontier.
        </p>
      )}
      {state.kind === "ok" && state.data.frontier.length > 0 && (
        <FrontierBody data={state.data} />
      )}
    </div>
  );
}

function FrontierBody({ data }: { data: Frontier }) {
  const {
    frontier,
    user_return,
    user_volatility,
    optimal_return,
    optimal_volatility,
    crra_gamma,
  } = data;

  const hasUser = user_return !== null && user_volatility !== null;
  const match = hasUser ? bestAtOrBelow(frontier, user_volatility) : null;
  const hasOptimal =
    optimal_return !== null && optimal_volatility !== null && crra_gamma !== null;

  // Plot geometry for the aria-hidden SVG. Build the domain from every plotted
  // point so the user/optimal markers can never fall outside the viewBox.
  const vols = frontier.map((p) => p.volatility);
  const rets = frontier.map((p) => p.expected_return);
  if (hasUser) {
    vols.push(user_volatility);
    rets.push(user_return);
  }
  if (hasOptimal) {
    vols.push(optimal_volatility);
    rets.push(optimal_return);
  }
  const minV = Math.min(...vols);
  const maxV = Math.max(...vols);
  const minR = Math.min(...rets);
  const maxR = Math.max(...rets);
  const W = 320;
  const H = 160;
  const PAD = 8;
  const sx = (v: number) =>
    maxV === minV ? W / 2 : PAD + ((v - minV) / (maxV - minV)) * (W - 2 * PAD);
  // y is inverted: higher return → smaller y (toward the top).
  const sy = (r: number) =>
    maxR === minR ? H / 2 : PAD + (1 - (r - minR) / (maxR - minR)) * (H - 2 * PAD);
  const linePoints = frontier.map((p) => `${sx(p.volatility)},${sy(p.expected_return)}`).join(" ");

  return (
    <>
      {/* Text-first gap message — the point of the feature. */}
      {hasUser && match ? (
        <p className="mt-3 text-sm text-zinc-700">
          Your portfolio: {pct(user_return)}% return at {pct(user_volatility)}%
          volatility. At that risk level the efficient frontier offers up to{" "}
          {pct(match.expected_return)}% — a gap of{" "}
          {pct(match.expected_return - user_return)} percentage points you’re
          leaving on the table by being off the frontier.
        </p>
      ) : hasUser ? (
        <p className="mt-3 text-sm text-zinc-700">
          Your portfolio: {pct(user_return)}% return at {pct(user_volatility)}%
          volatility, below the lowest-risk point on the frontier.
        </p>
      ) : (
        <p className="mt-3 text-sm text-zinc-700">
          Add holdings to see how your portfolio compares to the frontier.
        </p>
      )}

      {hasOptimal && (
        <p className="mt-2 text-sm text-zinc-700">
          Your risk-optimal portfolio (γ ≈ {Number(crra_gamma).toFixed(2)}):{" "}
          {pct(optimal_return)}% return at {pct(optimal_volatility)}% volatility.
        </p>
      )}

      {/* Decorative chart for sighted users; the table below is the accessible
          source of truth. */}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="mt-4 h-40 w-full"
        aria-hidden="true"
        role="presentation"
      >
        <polyline
          points={linePoints}
          fill="none"
          stroke="#27272a"
          strokeWidth={1.5}
        />
        {frontier.map((p, i) => (
          <circle
            key={i}
            cx={sx(p.volatility)}
            cy={sy(p.expected_return)}
            r={2}
            fill="#27272a"
          />
        ))}
        {hasUser && (
          <circle
            cx={sx(user_volatility)}
            cy={sy(user_return)}
            r={5}
            fill="#dc2626"
          />
        )}
        {hasOptimal && (
          <rect
            x={sx(optimal_volatility) - 4}
            y={sy(optimal_return) - 4}
            width={8}
            height={8}
            fill="#2563eb"
          />
        )}
      </svg>

      {/* Accessible curve: a table a screen reader can read point by point. */}
      <table className="mt-4 w-full text-sm tabular-nums">
        <caption className="sr-only">
          Efficient frontier points: volatility and expected return.
        </caption>
        <thead>
          <tr className="text-left text-xs text-zinc-500">
            <th scope="col" className="pb-1 font-medium">
              Volatility
            </th>
            <th scope="col" className="pb-1 font-medium">
              Expected return
            </th>
          </tr>
        </thead>
        <tbody>
          {frontier.map((p, i) => (
            <tr key={i} className="border-t border-zinc-100">
              <td className="py-1">{pct(p.volatility)}%</td>
              <td className="py-1">{pct(p.expected_return)}%</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="mt-4 text-xs text-zinc-500">
        Annualised, model-based estimates. Educational simulation, not investment
        advice.
      </p>
    </>
  );
}
