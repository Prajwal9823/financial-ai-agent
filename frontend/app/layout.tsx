import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Financial AI Agent | Market Insights",
  description: "Agentic financial research: technicals, fundamentals, news sentiment, and SEC-filing RAG.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-white">
        <nav className="border-b border-border px-6 py-4 flex items-center gap-6">
          <Link href="/" className="font-semibold tracking-tight">
            Financial<span className="text-accent">AI</span>
          </Link>
          <Link href="/dashboard" className="text-sm text-muted hover:text-white transition">
            Dashboard
          </Link>
          <Link href="/research" className="text-sm text-muted hover:text-white transition">
            Research Chat
          </Link>
        </nav>
        <main className="px-6 py-8 max-w-6xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
