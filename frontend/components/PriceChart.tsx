"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HistoricalPrices } from "@/lib/api";

export default function PriceChart({ history }: { history: HistoricalPrices }) {
  // Recharts wants plain objects — flatten just the fields the chart needs.
  const data = history.points.map((p) => ({ date: p.date, close: p.close }));

  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <h3 className="text-sm text-muted mb-3">
        Price history ({history.period}) — {history.ticker}
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#8592a3" }} minTickGap={40} />
          <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fill: "#8592a3" }} width={50} />
          <Tooltip
            contentStyle={{ background: "#121821", border: "1px solid #1f2733", borderRadius: 8 }}
            labelStyle={{ color: "#8592a3" }}
          />
          <Line type="monotone" dataKey="close" stroke="#3dd68c" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
