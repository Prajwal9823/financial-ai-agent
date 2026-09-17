import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="flex flex-col items-start gap-6 py-16">
      <h1 className="text-4xl font-bold tracking-tight max-w-2xl">
        A financial research agent that shows its work.
      </h1>
      <p className="text-muted max-w-xl leading-relaxed">
        Ask about a company in plain English. The agent pulls live prices,
        technical indicators, fundamentals, news sentiment, and grounded
        excerpts from SEC filings — then tells you exactly which tools it
        used and where each fact came from. Informational research only,
        never trading advice.
      </p>
      <div className="flex gap-4">
        <Link
          href="/dashboard"
          className="bg-accent text-black font-medium px-5 py-2.5 rounded-lg hover:opacity-90 transition"
        >
          Open Dashboard
        </Link>
        <Link
          href="/research"
          className="border border-border px-5 py-2.5 rounded-lg hover:border-accent transition"
        >
          Try Research Chat
        </Link>
      </div>
    </div>
  );
}
