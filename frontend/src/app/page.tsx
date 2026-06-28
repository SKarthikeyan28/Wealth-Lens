import Link from "next/link";

import { HealthStatus } from "@/components/HealthStatus";

const FEATURES = [
  "Dashboard — net worth, allocation, cashflow",
  "Accounts — cash, brokerage, CPF, SRS + holdings",
  "Risk — questionnaire, optimal allocation, frontier",
  "Projection — Monte-Carlo goal probability",
];

export default function Home() {
  return (
    <section className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">Wealth-Lens</h1>
      <p className="mt-2 max-w-prose text-zinc-600">
        An educational Singapore personal-finance optimizer. Track net worth across currencies,
        profile your risk appetite (CRRA utility), find an optimal allocation, and run Monte-Carlo
        goal projections. Simulation only — not financial advice.
      </p>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link href="/register" className="rounded bg-zinc-900 px-4 py-2 text-sm text-white">
          Create account
        </Link>
        <Link href="/login" className="rounded border border-zinc-300 px-4 py-2 text-sm">
          Sign in
        </Link>
      </div>

      <ul className="mt-8 grid gap-2 text-sm text-zinc-600 sm:grid-cols-2">
        {FEATURES.map((f) => (
          <li key={f} className="rounded border border-zinc-200 p-3">
            {f}
          </li>
        ))}
      </ul>

      <div className="mt-8 rounded-lg border border-zinc-200 p-4">
        <h2 className="text-sm font-medium text-zinc-500">Backend connectivity</h2>
        <HealthStatus />
      </div>
    </section>
  );
}
