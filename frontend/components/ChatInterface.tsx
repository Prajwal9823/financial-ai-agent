"use client";

import { FormEvent, useState } from "react";
import { api, ResearchResponse } from "@/lib/api";

interface Turn {
  query: string;
  response?: ResearchResponse;
  error?: string;
}

const STATUS_ICON: Record<string, string> = { success: "✓", error: "✗", skipped: "–" };

export default function ChatInterface() {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const query = input.trim();
    if (!query) return;
    setInput("");
    setLoading(true);
    const turn: Turn = { query };
    setTurns((prev) => [...prev, turn]);

    try {
      const response = await api.research(query);
      setTurns((prev) => prev.map((t) => (t === turn ? { ...t, response } : t)));
    } catch (err) {
      setTurns((prev) => prev.map((t) => (t === turn ? { ...t, error: (err as Error).message } : t)));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-6">
        {turns.map((turn, i) => (
          <div key={i} className="flex flex-col gap-2">
            <div className="self-end bg-accent text-black rounded-lg px-4 py-2 max-w-lg">{turn.query}</div>

            {turn.response && (
              <div className="bg-surface border border-border rounded-lg p-4 max-w-2xl flex flex-col gap-3">
                <div className="flex flex-wrap gap-2 text-xs">
                  {turn.response.tools_used.map((t, j) => (
                    <span
                      key={j}
                      className={`px-2 py-1 rounded border border-border/60 ${
                        t.status === "success" ? "text-accent" : "text-danger"
                      }`}
                    >
                      {STATUS_ICON[t.status]} {t.tool}
                    </span>
                  ))}
                </div>

                <p className="text-sm whitespace-pre-wrap leading-relaxed">{turn.response.answer}</p>

                {turn.response.sources.length > 0 && (
                  <div className="text-xs text-muted">
                    <p className="mb-1">Sources:</p>
                    <ul className="list-disc list-inside space-y-0.5">
                      {turn.response.sources.slice(0, 6).map((src) => (
                        <li key={src}>
                          <a href={src} target="_blank" rel="noreferrer" className="hover:text-accent break-all">
                            {src}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {turn.error && <div className="text-danger text-sm max-w-2xl">{turn.error}</div>}
          </div>
        ))}
        {loading && <p className="text-muted text-sm">Researching…</p>}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 sticky bottom-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder='Try: "Why did NVDA move recently?"'
          className="bg-surface border border-border rounded-lg px-4 py-3 flex-1 outline-none focus:border-accent transition"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-accent text-black font-medium px-5 py-3 rounded-lg hover:opacity-90 transition disabled:opacity-50"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
