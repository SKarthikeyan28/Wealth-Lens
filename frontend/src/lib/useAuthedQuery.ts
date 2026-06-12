"use client";

import { useEffect, useState } from "react";

import { ApiError, apiGet } from "./api";

export type QueryState<T> =
  | { kind: "loading" }
  | { kind: "error"; message: string; status?: number }
  | { kind: "ok"; data: T };

export function useAuthedQuery<T>(path: string): QueryState<T> {
  const [state, setState] = useState<QueryState<T>>({ kind: "loading" });

  useEffect(() => {
    let active = true; // guard against setState after unmount / path change
    apiGet<T>(path, true)
      .then((data) => {
        if (active) setState({ kind: "ok", data });
      })
      .catch((e) => {
        if (!active) return;
        const message = e instanceof Error ? e.message : "Failed to load";
        const status = e instanceof ApiError ? e.status : undefined;
        setState({ kind: "error", message, status });
      });
    return () => {
      active = false;
    };
  }, [path]);

  return state;
}
