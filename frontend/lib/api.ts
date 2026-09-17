/**
 * Thin, typed client around the FastAPI backend. Every function mirrors
 * one backend route 1:1 so it's obvious where a given piece of UI data
 * comes from — no hidden data transformation happens in here.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface StockPrice {
  ticker: string;
  price: number;
  currency: string;
  change: number;
  change_percent: number;
  market_cap?: number;
  as_of: string;
}

export interface HistoricalPricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoricalPrices {
  ticker: string;
  period: string;
  interval: string;
  points: HistoricalPricePoint[];
}

export interface Fundamentals {
  ticker: string;
  revenue_ttm?: number;
  revenue_growth?: number;
  net_income_ttm?: number;
  eps_ttm?: number;
  profit_margin?: number;
  operating_margin?: number;
  roe?: number;
  debt_to_equity?: number;
  pe_ratio?: number;
  market_cap?: number;
  free_cash_flow?: number;
  earnings_growth?: number;
  unavailable_fields: string[];
}

export interface TechnicalIndicators {
  ticker: string;
  sma_50?: number;
  sma_200?: number;
  ema_20?: number;
  macd?: number;
  macd_signal?: number;
  macd_trend?: string;
  rsi_14?: number;
  stochastic_k?: number;
  stochastic_d?: number;
  bollinger_upper?: number;
  bollinger_lower?: number;
  historical_volatility?: number;
  max_drawdown?: number;
  return_1d?: number;
  return_1w?: number;
  return_1m?: number;
  return_3m?: number;
  return_1y?: number;
}

export interface NewsArticle {
  title: string;
  source?: string;
  published_at?: string;
  url: string;
  summary?: string;
  sentiment?: "positive" | "neutral" | "negative";
  sentiment_score?: number;
}

export interface SentimentSummary {
  ticker: string;
  positive_pct: number;
  neutral_pct: number;
  negative_pct: number;
  article_count: number;
  articles: NewsArticle[];
}

export interface ToolTrace {
  tool: string;
  status: "success" | "error" | "skipped";
}

export interface ResearchResponse {
  query: string;
  intent: string;
  tools_used: ToolTrace[];
  answer: string;
  sources: string[];
  raw_data: Record<string, unknown>;
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getPrice: (ticker: string) => apiGet<StockPrice>(`/api/stock/${ticker}`),
  getHistory: (ticker: string, period = "1y") =>
    apiGet<HistoricalPrices>(`/api/stock/${ticker}/history?period=${period}`),
  getFundamentals: (ticker: string) => apiGet<Fundamentals>(`/api/stock/${ticker}/fundamentals`),
  getTechnicals: (ticker: string) => apiGet<TechnicalIndicators>(`/api/stock/${ticker}/technicals`),
  getSentiment: (ticker: string) => apiGet<SentimentSummary>(`/api/stock/${ticker}/sentiment`),
  research: (query: string) => apiPost<ResearchResponse>(`/api/research`, { query }),
};
