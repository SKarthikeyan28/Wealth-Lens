"use client";

import { useState } from "react";

import { ApiError, apiGet } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { useRequireAuth } from "@/lib/useRequireAuth";

// Every field is a backend `float`/`int` → a JS number (NO Decimal strings here).
// Money values are numbers; formatMoney takes a string, so we wrap with String().
type YearBand = {
  year: number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
};
type Projection = {
  probability: number;
  goal_amount: number;
  years: number;
  initial_wealth: number;
  annual_contribution: number;
  mean_return: number;
  volatility: number;
  n_sims: number;
  seed: number;
  bands: YearBand[];
};

type ResultState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; data: Projection };

const DEFAULTS = {
  goal_amount: "200000",
  years: "10",
  initial_wealth: "100000",
  annual_contribution: "12000",
  seed: "42",
};

export default function ProjectionPage() {
  const ready = useRequireAuth();

  const [form, setForm] = useState(DEFAULTS);
  const [result, setResult] = useState<ResultState>({ kind: "idle" });

  if (!ready) {
    return (
      <p role="status" className="p-6">
        Loading…
      </p>
    );
  }

  function update(key: keyof typeof DEFAULTS, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setResult({ kind: "loading" });
    const params = new URLSearchParams({
      goal_amount: form.goal_amount,
      years: form.years,
      initial_wealth: form.initial_wealth,
      annual_contribution: form.annual_contribution,
      seed: form.seed,
    });
    try {
      const data = await apiGet<Projection>(
        `/api/v1/projection/goal?${params.toString()}`,
        true,
      );
      setResult({ kind: "ok", data });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Projection failed";
      setResult({ kind: "error", message });
    }
  }

  return (
    <section className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Goal projection</h1>
      <p className="mt-2 text-zinc-600">
        Monte-Carlo simulation of your wealth using your risk-optimal portfolio’s
        return and volatility. Same seed reproduces the same draw.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 grid gap-4 sm:grid-cols-2">
        <Field
          label="Goal amount (SGD)"
          value={form.goal_amount}
          onChange={(v) => update("goal_amount", v)}
        />
        <Field
          label="Years"
          value={form.years}
          onChange={(v) => update("years", v)}
        />
        <Field
          label="Starting amount (SGD)"
          value={form.initial_wealth}
          onChange={(v) => update("initial_wealth", v)}
        />
        <Field
          label="Annual savings (SGD)"
          value={form.annual_contribution}
          onChange={(v) => update("annual_contribution", v)}
        />
        <Field
          label="Seed"
          value={form.seed}
          onChange={(v) => update("seed", v)}
        />
        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={result.kind === "loading"}
            className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {result.kind === "loading" ? "Simulating…" : "Run projection"}
          </button>
        </div>
      </form>

      {result.kind === "loading" && (
        <p role="status" className="mt-8 text-zinc-500">
          Simulating…
        </p>
      )}

      {result.kind === "error" && (
        <p role="alert" className="mt-8 text-red-700">
          {result.message}
        </p>
      )}

      {result.kind === "ok" && <ProjectionResult data={result.data} />}
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-zinc-600">{label}</span>
      <input
        type="number"
        inputMode="numeric"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-zinc-300 px-3 py-2 tabular-nums"
      />
    </label>
  );
}

function ProjectionResult({ data }: { data: Projection }) {
  const {
    probability,
    mean_return,
    volatility,
    n_sims,
    seed,
    bands,
  } = data;

  // Fan-chart geometry for the aria-hidden SVG: p10..p90 area + p50 median line.
  const W = 480;
  const H = 200;
  const PAD = 8;
  const maxYear = bands[bands.length - 1].year;
  const lo = Math.min(...bands.map((b) => b.p10));
  const hi = Math.max(...bands.map((b) => b.p90));
  const sx = (year: number) =>
    maxYear === 0 ? W / 2 : PAD + (year / maxYear) * (W - 2 * PAD);
  const sy = (v: number) =>
    hi === lo ? H / 2 : PAD + (1 - (v - lo) / (hi - lo)) * (H - 2 * PAD);
  // Area polygon: p90 left→right along the top, p10 right→left along the bottom.
  const top = bands.map((b) => `${sx(b.year)},${sy(b.p90)}`);
  const bottom = [...bands].reverse().map((b) => `${sx(b.year)},${sy(b.p10)}`);
  const areaPoints = [...top, ...bottom].join(" ");
  const medianPoints = bands.map((b) => `${sx(b.year)},${sy(b.p50)}`).join(" ");

  return (
    <div className="mt-10 grid gap-6">
      <div className="rounded-lg border border-zinc-200 p-5">
        <p className="text-3xl font-semibold tabular-nums">
          {(probability * 100).toFixed(0)}% chance of reaching your goal
        </p>
        <p className="mt-3 text-sm text-zinc-600">
          Assumes a {(mean_return * 100).toFixed(1)}% annual return,{" "}
          {(volatility * 100).toFixed(1)}% volatility, {n_sims.toLocaleString()}{" "}
          simulations, seed {seed} (change the seed to see a different random draw;
          same seed reproduces).
        </p>
      </div>

      <div className="rounded-lg border border-zinc-200 p-5">
        <h2 className="text-sm font-medium text-zinc-500">
          Projected wealth by year
        </h2>

        {/* Decorative fan chart; the table below is the accessible source of truth. */}
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="mt-4 h-48 w-full"
          aria-hidden="true"
          role="presentation"
        >
          <polygon points={areaPoints} fill="#bfdbfe" opacity={0.6} />
          <polyline
            points={medianPoints}
            fill="none"
            stroke="#1d4ed8"
            strokeWidth={1.5}
          />
        </svg>

        <table className="mt-4 w-full text-sm tabular-nums">
          <caption className="sr-only">
            Projected wealth percentile bands by year: pessimistic (p10), median
            (p50), and optimistic (p90).
          </caption>
          <thead>
            <tr className="text-left text-xs text-zinc-500">
              <th scope="col" className="pb-1 font-medium">
                Year
              </th>
              <th scope="col" className="pb-1 font-medium">
                Pessimistic (p10)
              </th>
              <th scope="col" className="pb-1 font-medium">
                Median (p50)
              </th>
              <th scope="col" className="pb-1 font-medium">
                Optimistic (p90)
              </th>
            </tr>
          </thead>
          <tbody>
            {bands.map((b) => (
              <tr key={b.year} className="border-t border-zinc-100">
                <td className="py-1">{b.year}</td>
                <td className="py-1">{formatMoney(String(b.p10), "SGD")}</td>
                <td className="py-1">{formatMoney(String(b.p50), "SGD")}</td>
                <td className="py-1">{formatMoney(String(b.p90), "SGD")}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p className="mt-4 text-xs text-zinc-500">
          Model-based estimates. Educational simulation, not investment advice.
        </p>
      </div>
    </div>
  );
}
