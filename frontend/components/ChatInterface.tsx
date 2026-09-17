"use client";

import { FormEvent, useState } from "react";
import { api, ResearchResponse } from "@/lib/api";
import ResearchAnswer from "@/components/ResearchAnswer";

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
      {turns.length === 0 && <div className="panel rounded-2xl p-6 sm:p-8"><p className="eyebrow">Try a starting point</p><div className="mt-4 grid gap-3 sm:grid-cols-2">{["Why did NVDA move recently?", "Compare Apple and Microsoft", "What is Tesla's current sentiment?", "Explain AAPL's technical setup"].map((prompt) => <button key={prompt} onClick={() => setInput(prompt)} className="rounded-xl border border-white/[0.08] bg-black/10 p-4 text-left text-sm text-muted transition hover:border-accent/40 hover:bg-accent/[.04] hover:text-white">{prompt}<span className="ml-2 text-accent">→</span></button>)}</div></div>}
      <div className="flex flex-col gap-6">
        {turns.map((turn, i) => (
          <div key={i} className="flex flex-col gap-2">
            <div className="self-end max-w-lg rounded-2xl rounded-br-sm bg-accent px-4 py-2.5 text-sm font-medium text-[#07120c]">{turn.query}</div>

            {turn.response && (
              <div className="panel max-w-2xl rounded-2xl rounded-tl-sm p-5 flex flex-col gap-4">
                <div className="flex flex-wrap gap-2 text-xs">
                  {turn.response.tools_used.map((t, j) => (
                    <span
                      key={j}
                      className={`rounded-full border border-white/[0.09] bg-black/10 px-2.5 py-1 ${
                        t.status === "success" ? "text-accent" : "text-danger"
                      }`}
                    >
                      {STATUS_ICON[t.status]} {t.tool}
                    </span>
                  ))}
                </div>

                <ResearchAnswer answer={turn.response.answer} />

                {turn.response.sources.length > 0 && (
                  <div className="border-t border-white/[0.07] pt-3 text-xs text-muted"><p className="mb-1.5 font-medium text-white/70">Sources</p>
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

            {turn.error && <div className="max-w-2xl rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-danger">{turn.error}</div>}
          </div>
        ))}
        {loading && <p className="text-sm text-muted"><span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-accent" />Gathering evidence…</p>}
      </div>

      <form onSubmit={handleSubmit} className="panel sticky bottom-4 flex gap-2 rounded-2xl p-2 shadow-[0_16px_45px_rgba(0,0,0,.4)]">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder='Try: "Why did NVDA move recently?"'
          className="min-w-0 flex-1 bg-transparent px-3 py-3 text-sm outline-none placeholder:text-muted"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-[#07120c] transition hover:brightness-110 disabled:opacity-50"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
