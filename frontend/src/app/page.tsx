import { HealthStatus } from "@/components/HealthStatus";

export default function Home() {
  return (
    <section className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">Wealth-Lens</h1>
      <p className="mt-2 text-zinc-600">SG Personal Finance Optimizer.</p>
      <div className="mt-8 rounded-lg border border-zinc-200 p-4">
        <h2 className="text-sm font-medium text-zinc-500">Backend connectivity</h2>
        <HealthStatus />
      </div>
    </section>
  );
}
