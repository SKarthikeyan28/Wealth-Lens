"use client";

import { useRouter } from "next/navigation";

import { AllocationChart } from "@/components/AllocationChart";
import { CashflowCard } from "@/components/CashflowCard";
import { NetWorthCard } from "@/components/NetWorthCard";
import { clearTokens } from "@/lib/auth";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function DashboardPage() {
  const ready = useRequireAuth();
  const router = useRouter();

  if (!ready) {
    return (
      <p role="status" className="p-6">
        Loading…
      </p>
    );
  }

  function signOut() {
    clearTokens();
    router.replace("/login");
  }

  return (
    <section className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <button
          onClick={signOut}
          className="rounded border border-zinc-300 px-3 py-1.5 text-sm"
        >
          Sign out
        </button>
      </div>
      <div className="mt-8 grid gap-6">
        <NetWorthCard />
        <AllocationChart />
        <CashflowCard />
      </div>
    </section>
  );
}
