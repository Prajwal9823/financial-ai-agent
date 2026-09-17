"use client";

import { ReactNode } from "react";

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*.*?\*\*|`.*?`)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={index} className="font-semibold text-white">{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={index} className="rounded bg-white/[.08] px-1.5 py-0.5 text-[.85em] text-accent">{part.slice(1, -1)}</code>;
    return part;
  });
}

function parseTable(lines: string[]) {
  const rows = lines.filter((line) => !/^\s*\|?\s*:?-{3,}/.test(line)).map((line) => line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim()));
  const [headers, ...body] = rows;
  if (!headers || !body.length) return null;
  return <div className="overflow-x-auto rounded-xl border border-white/[0.08]"><table className="min-w-full text-left text-xs"><thead className="bg-white/[0.05] text-white"><tr>{headers.map((header, i) => <th className="whitespace-nowrap px-3 py-2.5 font-medium" key={i}>{inline(header)}</th>)}</tr></thead><tbody>{body.map((row, i) => <tr className="border-t border-white/[0.07] align-top" key={i}>{headers.map((_, j) => <td className="min-w-[10rem] px-3 py-2.5 leading-5 text-muted" key={j}>{inline(row[j] || "—")}</td>)}</tr>)}</tbody></table></div>;
}

export default function ResearchAnswer({ answer }: { answer: string }) {
  const lines = answer.split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line) { index++; continue; }
    if (line.startsWith("|") && lines[index + 1]?.includes("---")) {
      const table: string[] = [];
      while (lines[index]?.trim().startsWith("|")) table.push(lines[index++]);
      blocks.push(<div key={`table-${index}`}>{parseTable(table)}</div>); continue;
    }
    if (/^#{1,3}\s/.test(line)) { const content = line.replace(/^#{1,3}\s*/, ""); blocks.push(<h3 className="pt-2 text-base font-semibold tracking-tight text-white" key={index}>{inline(content)}</h3>); index++; continue; }
    if (/^[-*]\s+/.test(line)) {
      const items: string[] = []; while (index < lines.length && /^[-*]\s+/.test(lines[index].trim())) items.push(lines[index++].trim().replace(/^[-*]\s+/, ""));
      blocks.push(<ul className="space-y-1.5 pl-4 text-sm leading-6 text-white/85 marker:text-accent" key={`ul-${index}`}>{items.map((item, i) => <li key={i}>{inline(item)}</li>)}</ul>); continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      const items: string[] = []; while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) items.push(lines[index++].trim().replace(/^\d+\.\s+/, ""));
      blocks.push(<ol className="space-y-1.5 pl-5 text-sm leading-6 text-white/85 marker:font-medium marker:text-accent" key={`ol-${index}`}>{items.map((item, i) => <li key={i}>{inline(item)}</li>)}</ol>); continue;
    }
    if (/^---+$/.test(line)) { blocks.push(<hr className="border-white/[0.07]" key={index} />); index++; continue; }
    blocks.push(<p className="text-sm leading-7 text-white/85" key={index}>{inline(line)}</p>); index++;
  }
  return <div className="flex flex-col gap-3">{blocks}</div>;
}
