import ChatInterface from "@/components/ChatInterface";

export default function ResearchPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div className="panel rounded-2xl p-6 sm:p-8">
        <p className="eyebrow">Evidence-led analysis</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Research room</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">Ask a question in your own words. Aster selects the right market tools, synthesizes the results and keeps the evidence visible.</p>
      </div>
      <ChatInterface />
    </div>
  );
}
