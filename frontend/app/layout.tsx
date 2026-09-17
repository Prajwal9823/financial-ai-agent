import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = { title: "Aster — Financial Intelligence", description: "Clearer market research, powered by AI." };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="soft-grid">
        <header className="sticky top-0 z-20 border-b border-white/[0.07] bg-background/75 backdrop-blur-xl"><div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="flex items-center gap-3"><span className="grid h-8 w-8 place-items-center rounded-xl bg-accent text-sm font-black text-[#07120c] shadow-[0_0_24px_rgba(73,229,156,.26)]">A</span><span className="text-base font-semibold tracking-tight">aster<span className="text-accent">.ai</span></span></Link>
          <nav className="flex items-center gap-1 rounded-xl border border-white/[0.07] bg-white/[0.025] p-1 text-sm"><Link href="/dashboard" className="rounded-lg px-3 py-1.5 text-muted transition hover:bg-white/[0.06] hover:text-white">Terminal</Link><Link href="/research" className="rounded-lg px-3 py-1.5 text-muted transition hover:bg-white/[0.06] hover:text-white">Research</Link></nav>
          <div className="hidden items-center gap-2 text-xs text-muted sm:flex"><span className="h-2 w-2 rounded-full bg-accent shadow-[0_0_10px_#49e59c]" /> Markets connected</div>
        </div></header>
        <main className="mx-auto min-h-[calc(100vh-72px)] max-w-7xl px-5 py-8 sm:px-8 sm:py-12">{children}</main>
      </body>
    </html>
  );
}
