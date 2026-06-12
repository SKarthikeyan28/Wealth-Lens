"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

type Ping = { status: string; version: string };
type State =
  | { kind: "loading" }
  | { kind: "ok"; data: Ping }
  | { kind: "error"; message: string };

export function HealthStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    apiGet<Ping>("/api/v1/ping")
      .then((data) => setState({ kind: "ok", data }))
      .catch((e) =>
        setState({ kind: "error", message: e instanceof Error ? e.message : "Unknown error" }),
      );
  }, []);

  if (state.kind === "loading") return <p role="status">Checking API…</p>;
  if (state.kind === "error") return <p role="alert">API unreachable: {state.message}</p>;
  return <p>API reachable — backend version {state.data.version}.</p>;
}
