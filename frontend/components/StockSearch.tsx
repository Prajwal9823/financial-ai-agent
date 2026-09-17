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
    <form onSubmit={handleSubmit} className="flex flex-col gap-1">
      <div className="flex gap-2">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Enter a ticker symbol, e.g. AAPL"
          className="bg-surface border border-border rounded-lg px-4 py-2 flex-1 outline-none focus:border-accent transition"
        />
        <button
          type="submit"
          className="bg-accent text-black font-medium px-5 py-2 rounded-lg hover:opacity-90 transition"
        >
          Analyze
        </button>
      </div>
      <span className="text-xs text-muted">
        Use the stock&apos;s ticker symbol (e.g. AAPL for Apple, NVDA for Nvidia) — not the company name.
      </span>
    </form>
  );
}
