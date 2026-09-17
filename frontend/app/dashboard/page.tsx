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
      <StockSearch onSearch={loadTicker} />

      {loading && <p className="text-muted text-sm">Loading {ticker}…</p>}
      {error && <p className="text-danger text-sm">{error}</p>}

      {data.price && (
        <div className="bg-surface border border-border rounded-xl p-5 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold">{data.price.ticker}</h2>
            <p className="text-muted text-sm">As of {new Date(data.price.as_of).toLocaleString()}</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">${data.price.price.toFixed(2)}</div>
            <div className={data.price.change >= 0 ? "text-accent" : "text-danger"}>
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
        <div className="bg-surface border border-border rounded-xl p-4">
          <h3 className="text-sm text-muted mb-2">Fundamentals</h3>
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
        <p className="text-muted text-sm">Search a ticker above to load its dashboard.</p>
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
    <div className="flex flex-col border border-border/60 rounded-lg p-3">
      <span className="text-muted text-xs">{label}</span>
      <span>{display}</span>
    </div>
  );
}
