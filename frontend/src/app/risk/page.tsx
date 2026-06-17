"use client";

import { useEffect, useState } from "react";

import { RiskAllocation } from "@/components/RiskAllocation";
import { RiskFrontier } from "@/components/RiskFrontier";
import { RiskQuestionnaire } from "@/components/RiskQuestionnaire";
import { ApiError, apiGet, apiPost } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

// crra_gamma, crra_gamma_low, crra_gamma_high are backend Decimals → JSON strings;
// wrap in Number(...) before any arithmetic / .toFixed. assessed_at is an ISO string.
type RiskProfile = {
  crra_gamma: string;
  crra_gamma_low: string;
  crra_gamma_high: string;
  assessed_at: string;
};

type ProfileState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "none" } // 404 → no profile yet, show questionnaire
  | { kind: "ok"; profile: RiskProfile };

export default function RiskPage() {
  const ready = useRequireAuth();

  const [state, setState] = useState<ProfileState>({ kind: "loading" });
  // When true, force the questionnaire view even if a profile exists ("Retake").
  const [retaking, setRetaking] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    let active = true;
    apiGet<RiskProfile>("/api/v1/risk/profile", true)
      .then((profile) => {
        if (active) setState({ kind: "ok", profile });
      })
      .catch((e) => {
        if (!active) return;
        if (e instanceof ApiError && e.status === 404) {
          setState({ kind: "none" });
          return;
        }
        const message = e instanceof Error ? e.message : "Failed to load";
        setState({ kind: "error", message });
      });
    return () => {
      active = false;
    };
  }, [ready]);

  if (!ready) {
    return (
      <p role="status" className="p-6">
        Loading…
      </p>
    );
  }

  async function handleSubmit(answers: boolean[]) {
    setSubmitError(null);
    setSubmitting(true);
    try {
      const profile = await apiPost<RiskProfile>(
        "/api/v1/risk/assessment",
        { answers },
        true,
      );
      setRetaking(false);
      setState({ kind: "ok", profile });
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  const showQuestionnaire =
    state.kind === "none" || (state.kind === "ok" && retaking);

  return (
    <section className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Risk profile</h1>
      <p className="mt-2 text-zinc-600">
        A short questionnaire estimates your risk aversion and an optimal asset mix.
      </p>

      {state.kind === "loading" && (
        <p role="status" className="mt-8 text-zinc-500">
          Loading…
        </p>
      )}

      {state.kind === "error" && (
        <p role="alert" className="mt-8 text-red-700">
          Couldn’t load your risk profile: {state.message}
        </p>
      )}

      {showQuestionnaire && (
        <div className="mt-8">
          <RiskQuestionnaire
            onSubmit={handleSubmit}
            submitting={submitting}
            submitError={submitError}
          />
        </div>
      )}

      {state.kind === "ok" && !retaking && (
        <div className="mt-8 grid gap-6">
          <div className="rounded-lg border border-zinc-200 p-5">
            <div className="flex items-start justify-between gap-4">
              <h2 className="text-sm font-medium text-zinc-500">Your risk aversion</h2>
              <button
                onClick={() => {
                  setSubmitError(null);
                  setRetaking(true);
                }}
                className="rounded border border-zinc-300 px-3 py-1.5 text-sm"
              >
                Retake questionnaire
              </button>
            </div>
            <p className="mt-3 text-2xl font-semibold tabular-nums">
              γ ≈ {Number(state.profile.crra_gamma).toFixed(2)}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              Band {Number(state.profile.crra_gamma_low).toFixed(2)}–
              {Number(state.profile.crra_gamma_high).toFixed(2)}. Higher γ means more
              risk-averse.
            </p>
          </div>

          <RiskAllocation />

          <RiskFrontier />
        </div>
      )}
    </section>
  );
}
