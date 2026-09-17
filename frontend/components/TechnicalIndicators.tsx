import type { TechnicalIndicators as TechData } from "@/lib/api";

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  const isEmpty = value === undefined || value === null || value === "";
  return (
    <div className="flex justify-between border-b border-border/60 py-2 text-sm">
      <span className="text-muted">{label}</span>
      <span>{isEmpty ? "Data unavailable" : value}</span>
    </div>
  );
}

export default function TechnicalIndicators({ data }: { data: TechData }) {
  const trendColor =
    data.macd_trend === "Bullish" ? "text-accent" : data.macd_trend === "Bearish" ? "text-danger" : "text-muted";

  return (
    <div className="panel rounded-2xl p-5"><div className="mb-3"><p className="eyebrow">Signal desk</p><h3 className="mt-1 font-medium">Technical indicators</h3></div>
      <Metric label="RSI (14)" value={data.rsi_14} />
      <Metric label="MACD trend" value={data.macd_trend ? <span className={trendColor}>{data.macd_trend}</span> : undefined} />
      <Metric label="50D SMA" value={data.sma_50} />
      <Metric label="200D SMA" value={data.sma_200} />
      <Metric label="20D EMA" value={data.ema_20} />
      <Metric label="Bollinger upper" value={data.bollinger_upper} />
      <Metric label="Bollinger lower" value={data.bollinger_lower} />
      <Metric label="Historical volatility" value={data.historical_volatility ? `${data.historical_volatility}%` : undefined} />
      <Metric label="Max drawdown" value={data.max_drawdown ? `${data.max_drawdown}%` : undefined} />
      <Metric label="1M return" value={data.return_1m ? `${data.return_1m}%` : undefined} />
      <Metric label="1Y return" value={data.return_1y ? `${data.return_1y}%` : undefined} />
    </div>
  );
}
