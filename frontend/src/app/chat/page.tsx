"use client";

import { useState } from "react";

import { apiPost } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

type Message = { role: "you" | "assistant"; text: string };

export default function ChatPage() {
  const ready = useRequireAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSend(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    setMessages((m) => [...m, { role: "you", text: q }]);
    setQuestion("");
    setBusy(true);
    setError(null);
    try {
      const res = await apiPost<{ answer: string }>(
        "/api/v1/chat",
        { question: q, base: "SGD" },
        true,
      );
      setMessages((m) => [...m, { role: "assistant", text: res.answer }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setBusy(false);
    }
  }

  if (!ready) {
    return (
      <p role="status" className="p-6">
        Loading…
      </p>
    );
  }

  return (
    <section className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Assistant</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Ask about your finances. For your privacy, only derived summaries — never your raw
        transactions — are sent to the model. This is educational analysis, not financial advice.
      </p>

      {error && (
        <p role="alert" className="mt-4 rounded bg-red-50 p-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="mt-6 grid gap-3">
        {messages.length === 0 && (
          <p className="text-sm text-zinc-500">
            No messages yet. Try “What’s my savings rate?” or “How am I tracking to FI?”
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "you"
                ? "ml-auto max-w-[85%] rounded-lg bg-zinc-900 px-3 py-2 text-sm text-white"
                : "mr-auto max-w-[85%] rounded-lg border border-zinc-200 px-3 py-2 text-sm whitespace-pre-wrap"
            }
          >
            {m.text}
          </div>
        ))}
        {busy && (
          <p role="status" className="mr-auto text-sm text-zinc-500">
            Thinking…
          </p>
        )}
      </div>

      <form onSubmit={onSend} className="mt-6 flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question…"
          maxLength={1000}
          className="flex-1 rounded border border-zinc-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={busy || question.trim().length === 0}
          className="rounded bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </section>
  );
}
