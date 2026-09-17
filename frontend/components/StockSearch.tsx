"use client";

import { FormEvent, useState } from "react";

interface Props {
  defaultValue?: string;
  onSearch: (ticker: string) => void;
}

/** Simple controlled search box — deliberately dumb, all fetching logic
 * lives in the parent dashboard page so this stays reusable. */
export default function StockSearch({ defaultValue = "", onSearch }: Props) {
  const [value, setValue] = useState(defaultValue);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const ticker = value.trim().toUpperCase();
    if (ticker) onSearch(ticker);
  }

  return (
    <form onSubmit={handleSubmit} className="panel rounded-2xl p-3 sm:p-4">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Enter a ticker symbol, e.g. AAPL"
          className="min-w-0 flex-1 rounded-xl border border-white/[0.09] bg-black/20 px-4 py-3 text-sm outline-none placeholder:text-muted/70 focus:border-accent/70 focus:ring-4 focus:ring-accent/10 transition"
        />
        <button
          type="submit"
          className="rounded-xl bg-accent px-6 py-3 text-sm font-semibold text-[#07120c] transition hover:brightness-110 active:scale-[.98]"
        >
          Analyze
        </button>
      </div>
      <span className="mt-2 block text-xs text-muted">Enter a ticker symbol, such as AAPL, NVDA or MSFT.</span>
    </form>
  );
}
