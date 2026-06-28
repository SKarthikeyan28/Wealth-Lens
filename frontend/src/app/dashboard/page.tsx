"use client";

import { AllocationChart } from "@/components/AllocationChart";
import { CashflowCard } from "@/components/CashflowCard";
import { NetWorthCard } from "@/components/NetWorthCard";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function DashboardPage() {
  const ready = useRequireAuth();

  if (!ready) {
    return (
      <p role="status" className="p-6">
        Loading…
      </p>
    );
  }

  return (
    <section className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
      <div className="mt-8 grid gap-6">
        <NetWorthCard />
        <AllocationChart />
        <CashflowCard />
      </div>
    </section>
  );
}
