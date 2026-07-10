"use client";

import { useState } from "react";

import { Badge, Button, Card, Input, KineticLoader } from "@/components/ui";
import { api, ApiError } from "@/lib/api";

interface Message {
  role: "user" | "oracle";
  text: string;
}

export default function OraclePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  const ask = async () => {
    const question = input.trim();
    if (!question) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setBusy(true);
    try {
      await api.qa(question);
      // Track 3 not built: the 501 branch below is today's real path.
      setBusy(false);
    } catch (err) {
      setBusy(false);
      const text =
        err instanceof ApiError && err.status === 501
          ? "I can't answer that yet — the Video-Oracle RAG index (Track 3, tasks T093–T094) hasn't been built. This chat is wired to the pinned /api/qa contract and will answer with grounded, moment-cited responses once the index ships."
          : err instanceof Error
            ? `Backend error: ${err.message}`
            : "Backend unreachable.";
      setMessages((m) => [...m, { role: "oracle", text }]);
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-4rem)] max-w-3xl flex-col">
      <div className="mb-2 flex items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Oracle Chat</h1>
        <Badge tone="primary">Track 3</Badge>
      </div>
      <p className="mb-6 text-sm text-muted">
        Ask questions over your captioned clips; answers cite the moments they come from.
      </p>

      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 && (
          <Card>
            <p className="text-sm text-muted">
              Try: “What happens at the start of v1?” — and expect an honest answer about what is
              and is not built yet.
            </p>
          </Card>
        )}
        {messages.map((message, i) => (
          <div
            key={i}
            className={
              message.role === "user"
                ? "ml-auto max-w-[80%] rounded-xl rounded-br-sm bg-primary/15 px-4 py-3 text-sm"
                : "mr-auto max-w-[80%] rounded-xl rounded-bl-sm border border-border bg-card px-4 py-3 text-sm text-muted"
            }
          >
            {message.text}
          </div>
        ))}
        {busy && <KineticLoader label="thinking…" />}
      </div>

      <div className="flex gap-3 border-t border-border/60 pt-4">
        <Input
          placeholder="Ask the Oracle…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
        />
        <Button onClick={ask} disabled={!input.trim() || busy}>
          Send
        </Button>
      </div>
    </div>
  );
}
