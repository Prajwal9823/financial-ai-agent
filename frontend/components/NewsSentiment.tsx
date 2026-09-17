import type { SentimentSummary } from "@/lib/api";

const SENTIMENT_COLOR: Record<string, string> = {
  positive: "text-accent",
  negative: "text-danger",
  neutral: "text-muted",
};

export default function NewsSentiment({ data }: { data: SentimentSummary }) {
  return (
    <div className="panel rounded-2xl p-5"><div className="mb-4"><p className="eyebrow">Narrative pulse</p><h3 className="mt-1 font-medium">News sentiment <span className="text-sm font-normal text-muted">· {data.article_count} articles</span></h3></div>

      <div className="flex gap-4 mb-4 text-sm">
        <span className="text-accent">Positive {data.positive_pct}%</span>
        <span className="text-muted">Neutral {data.neutral_pct}%</span>
        <span className="text-danger">Negative {data.negative_pct}%</span>
      </div>

      <div className="flex flex-col gap-3">
        {data.articles.slice(0, 5).map((article) => (
          <a
            key={article.url}
            href={article.url}
            target="_blank"
            rel="noreferrer"
            className="block rounded-xl border border-white/[0.07] bg-black/10 p-3 transition hover:border-accent/50 hover:bg-white/[0.035]"
          >
            <div className="text-sm font-medium">{article.title}</div>
            <div className="text-xs text-muted mt-1 flex gap-2">
              <span>{article.source ?? "Unknown source"}</span>
              {article.sentiment && (
                <span className={SENTIMENT_COLOR[article.sentiment]}>· {article.sentiment}</span>
              )}
            </div>
          </a>
        ))}
        {data.articles.length === 0 && <p className="text-sm text-muted">No recent news found for this ticker.</p>}
      </div>
    </div>
  );
}
