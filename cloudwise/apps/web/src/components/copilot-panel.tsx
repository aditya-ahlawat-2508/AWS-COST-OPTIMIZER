"use client";

import { useState } from "react";
import { Sparkles, Send } from "lucide-react";
import { api, ApiError } from "@/lib/api";

type ChatTurn = { role: "user" | "assistant"; text: string; warnings?: string[] };

export function CopilotPanel({ getToken }: { getToken: () => Promise<string | null> }) {
  const [turns, setTurns] = useState<ChatTurn[]>([
    { role: "assistant", text: "Ask me about your AWS spend — I only answer from what's actually in your account." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    const message = input.trim();
    if (!message || loading) return;
    setInput("");
    setError(null);
    setTurns((t) => [...t, { role: "user", text: message }]);
    setLoading(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Not signed in");
      const response = await api.copilotChat(token, message);
      setTurns((t) => [...t, { role: "assistant", text: response.text, warnings: response.grounding_warnings }]);
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 503
          ? "The copilot isn't configured yet (no ANTHROPIC_API_KEY set on the backend)."
          : "Something went wrong asking the copilot.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3 text-sm font-medium">
        <Sparkles size={16} className="text-accent" />
        AI copilot
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-4 text-sm">
        {turns.map((turn, i) => (
          <div key={i} className={turn.role === "user" ? "text-right" : ""}>
            <div
              className={
                turn.role === "user"
                  ? "inline-block rounded-lg bg-accent px-3 py-2 text-accent-foreground"
                  : "inline-block rounded-lg bg-surface-2 px-3 py-2"
              }
            >
              {turn.text}
            </div>
            {turn.warnings && turn.warnings.length > 0 && (
              <div className="mt-1 text-xs text-warning">
                ⚠ {turn.warnings.join("; ")}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-xs text-muted">Thinking…</div>}
        {error && <div className="text-xs text-danger">{error}</div>}
      </div>
      <div className="flex items-center gap-2 border-t border-border p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask about your AWS spend…"
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent"
        />
        <button
          onClick={send}
          disabled={loading}
          className="rounded-md bg-accent p-2 text-accent-foreground disabled:opacity-50"
          aria-label="Send"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
