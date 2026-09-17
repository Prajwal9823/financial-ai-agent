import ChatInterface from "@/components/ChatInterface";

export default function ResearchPage() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold">AI Research Chat</h1>
        <p className="text-muted text-sm">
          Ask about a company — the agent decides which tools to run and shows its trace below each answer.
        </p>
      </div>
      <ChatInterface />
    </div>
  );
}
