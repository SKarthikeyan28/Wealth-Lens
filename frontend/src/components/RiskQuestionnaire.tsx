"use client";

import { useEffect, useState } from "react";

import { ApiError, apiGet } from "@/lib/api";

// All four fields are backend `float` → arrive as JS numbers (NOT Decimal strings).
type LadderQuestion = {
  gamble_high: number;
  gamble_low: number;
  sure_amount: number;
  gamma_cut: number;
};

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; questions: LadderQuestion[] };

type Props = {
  // answers[i] === true means the user chose the SURE amount (Option B),
  // matching the backend's `answers[i] is True means SURE`.
  onSubmit: (answers: boolean[]) => void;
  submitting: boolean;
  submitError: string | null;
};

export function RiskQuestionnaire({ onSubmit, submitting, submitError }: Props) {
  const [state, setState] = useState<State>({ kind: "loading" });
  // null = not yet answered; true = chose sure; false = chose gamble.
  const [choices, setChoices] = useState<(boolean | null)[]>([]);

  useEffect(() => {
    let active = true;
    apiGet<LadderQuestion[]>("/api/v1/risk/ladder", true)
      .then((questions) => {
        if (!active) return;
        setState({ kind: "ok", questions });
        setChoices(questions.map(() => null));
      })
      .catch((e) => {
        if (!active) return;
        const message =
          e instanceof ApiError || e instanceof Error ? e.message : "Failed to load";
        setState({ kind: "error", message });
      });
    return () => {
      active = false;
    };
  }, []);

  if (state.kind === "loading") {
    return (
      <p role="status" className="mt-2 text-zinc-500">
        Loading…
      </p>
    );
  }
  if (state.kind === "error") {
    return (
      <p role="alert" className="mt-2 text-red-700">
        Couldn’t load the questionnaire: {state.message}
      </p>
    );
  }

  const allAnswered =
    choices.length === state.questions.length && choices.every((c) => c !== null);

  function choose(index: number, sure: boolean) {
    setChoices((prev) => {
      const next = [...prev];
      next[index] = sure;
      return next;
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!allAnswered) return;
    onSubmit(choices.map((c) => c === true));
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 flex flex-col gap-6">
      <p className="text-sm text-zinc-600">
        For each pair, pick the option you’d prefer. There are no right answers —
        your choices reveal how much risk you’re comfortable taking.
      </p>

      {state.questions.map((q, i) => {
        const name = `q-${i}`;
        return (
          <fieldset key={i} className="rounded-lg border border-zinc-200 p-4">
            <legend className="px-1 text-sm font-medium text-zinc-500">
              Question {i + 1}
            </legend>
            <div className="mt-1 flex flex-col gap-2">
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name={name}
                  checked={choices[i] === false}
                  onChange={() => choose(i, false)}
                  className="mt-0.5"
                />
                <span>
                  <span className="font-medium">Option A:</span> a 50/50 chance of $
                  {q.gamble_high.toFixed(0)} or ${q.gamble_low.toFixed(0)}
                </span>
              </label>
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name={name}
                  checked={choices[i] === true}
                  onChange={() => choose(i, true)}
                  className="mt-0.5"
                />
                <span>
                  <span className="font-medium">Option B:</span> a guaranteed $
                  {q.sure_amount.toFixed(0)}
                </span>
              </label>
            </div>
          </fieldset>
        );
      })}

      {submitError && (
        <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">
          {submitError}
        </p>
      )}

      <button
        type="submit"
        disabled={!allAnswered || submitting}
        className="self-start rounded bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {submitting ? "Calculating…" : "See my risk profile"}
      </button>
    </form>
  );
}
