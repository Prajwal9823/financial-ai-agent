"use client";

import { useState } from "react";
import StockSearch from "@/components/StockSearch";
import PriceChart from "@/components/PriceChart";
import TechnicalIndicators from "@/components/TechnicalIndicators";
import NewsSentiment from "@/components/NewsSentiment";
import {
  api,
  Fundamentals,
  HistoricalPrices,
  SentimentSummary,
  StockPrice,
  TechnicalIndicators as TechData,
} from "@/lib/api";

interface DashboardState {
  price?: StockPrice;
  history?: HistoricalPrices;
  fundamentals?: Fundamentals;
  technicals?: TechData;
  sentiment?: SentimentSummary;
}

export default function DashboardPage() {
  const [ticker, setTicker] = useState<string>("");
  const [data, setData] = useState<DashboardState>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadTicker(symbol: string) {
    setTicker(symbol);
    setLoading(true);
    setError(null);
    setData({});
    try {
      // Fire every request in parallel — each panel renders independently
      // as soon as its own data arrives instead of waiting on the slowest.
      const [price, history, fundamentals, technicals, sentiment] = await Promise.allSettled([
        api.getPrice(symbol),
        api.getHistory(symbol),
        api.getFundamentals(symbol),
        api.getTechnicals(symbol),
        api.getSentiment(symbol),
      ]);

      setData({
        price: price.status === "fulfilled" ? price.value : undefined,
        history: history.status === "fulfilled" ? history.value : undefined,
        fundamentals: fundamentals.status === "fulfilled" ? fundamentals.value : undefined,
        technicals: technicals.status === "fulfilled" ? technicals.value : undefined,
        sentiment: sentiment.status === "fulfilled" ? sentiment.value : undefined,
      });

      if (price.status === "rejected") {
        setError((price.reason as Error).message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div><p className="eyebrow">Market workspace</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">The terminal</h1><p className="mt-1 text-sm text-muted">A focused view of price action, signals and narrative.</p></div>
        <div className="flex items-center gap-2 text-xs text-muted"><span className="h-2 w-2 rounded-full bg-accent" /> Live data on demand</div>
      </div>
      <StockSearch onSearch={loadTicker} />

      {loading && <div className="panel rounded-xl px-4 py-3 text-sm text-muted"><span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-accent" />Building a view for {ticker}…</div>}
      {error && <p className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>}

      {data.price && (
        <div className="panel rounded-2xl p-5 sm:p-6 flex items-center justify-between">
          <div>
            <p className="eyebrow">Quote</p><h2 className="mt-1 text-3xl font-semibold tracking-tight">{data.price.ticker}</h2>
            <p className="mt-1 text-muted text-xs">As of {new Date(data.price.as_of).toLocaleString()}</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-semibold tracking-tight">${data.price.price.toFixed(2)}</div>
            <div className={`mt-1 text-sm font-medium ${data.price.change >= 0 ? "text-accent" : "text-danger"}`}>
              {data.price.change >= 0 ? "+" : ""}
              {data.price.change.toFixed(2)} ({data.price.change_percent.toFixed(2)}%)
            </div>
          </div>
        </div>
      )}

      {data.history && <PriceChart history={data.history} />}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {data.technicals && <TechnicalIndicators data={data.technicals} />}
        {data.sentiment && <NewsSentiment data={data.sentiment} />}
      </div>

      {data.fundamentals && (
        <div className="panel rounded-2xl p-5">
          <div className="mb-4"><p className="eyebrow">Company health</p><h3 className="mt-1 font-medium">Fundamentals</h3></div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
            <Field label="Revenue (TTM)" value={data.fundamentals.revenue_ttm} />
            <Field label="Revenue growth" value={data.fundamentals.revenue_growth} percent />
            <Field label="Net income (TTM)" value={data.fundamentals.net_income_ttm} />
            <Field label="EPS (TTM)" value={data.fundamentals.eps_ttm} />
            <Field label="P/E ratio" value={data.fundamentals.pe_ratio} />
            <Field label="Profit margin" value={data.fundamentals.profit_margin} percent />
            <Field label="Operating margin" value={data.fundamentals.operating_margin} percent />
            <Field label="ROE" value={data.fundamentals.roe} percent />
            <Field label="Debt/Equity" value={data.fundamentals.debt_to_equity} />
            <Field label="Market cap" value={data.fundamentals.market_cap} />
            <Field label="Free cash flow" value={data.fundamentals.free_cash_flow} />
            <Field label="Earnings growth" value={data.fundamentals.earnings_growth} percent />
          </div>
        </div>
      )}

      {!data.price && !loading && (
        <div className="panel rounded-2xl px-6 py-10 text-center"><div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-accent/10 text-xl text-accent">⌁</div><h2 className="mt-4 font-medium">Start with a company</h2><p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted">Search a ticker to build its market snapshot—from price action to the latest news sentiment.</p></div>
      )}
    </div>
  );
}

function Field({ label, value, percent }: { label: string; value?: number; percent?: boolean }) {
  const display =
    value === undefined || value === null
      ? "Not available from the current data source."
      : percent
      ? `${(value * 100).toFixed(1)}%`
      : value.toLocaleString();
  return (
    <div className="flex flex-col rounded-xl border border-white/[0.07] bg-black/10 p-3">
      <span className="text-muted text-xs">{label}</span><span className="mt-1 text-sm font-medium">{display}</span>
    </div>
  );
}
