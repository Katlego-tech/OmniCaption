"use client";

import { useState } from "react";

import { Badge, Button, Card, Input, KineticLoader } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import type { SearchHit } from "@/lib/types";

interface Message {
  role: "user" | "oracle";
  text: string;
  citations?: SearchHit[];
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
      const response = await api.qa(question);
      setMessages((m) => [
        ...m,
        { role: "oracle", text: response.answer, citations: response.citations },
      ]);
    } catch (err) {
      const text =
        err instanceof ApiError && err.status === 501
          ? `The Video-Oracle index has not been built yet — the backend said: "${err.message}". Build it with the oracle CLI (services/oracle) and I will answer with grounded, moment-cited responses.`
          : err instanceof Error
            ? `Backend error: ${err.message}`
            : "Backend unreachable.";
      setMessages((m) => [...m, { role: "oracle", text }]);
    } finally {
      setBusy(false);
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
              Try: “What happens at the start of v1?” — answers are grounded strictly in indexed
              moments, cited as [task_id @ t].
            </p>
          </Card>
        )}
        {messages.map((message, i) => (
          <div
            key={i}
            className={
              message.role === "user"
                ? "ml-auto max-w-[80%] rounded-xl rounded-br-sm bg-primary/15 px-4 py-3 text-sm"
                : "mr-auto max-w-[80%] rounded-xl rounded-bl-sm border border-border bg-card px-4 py-3 text-sm"
            }
          >
            <p className={message.role === "oracle" ? "text-foreground/90" : undefined}>
              {message.text}
            </p>
            {message.citations && message.citations.length > 0 && (
              <div className="mt-3 space-y-1 border-t border-border/60 pt-2">
                {message.citations.map((hit, j) => (
                  <p key={j} className="text-xs text-faint">
                    <span className="font-mono text-primary-soft">{hit.task_id}</span>
                    {hit.t_start !== null && ` @ ${hit.t_start.toFixed(1)}s`} — {hit.text}
                  </p>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <KineticLoader label="thinking…" />}
      </div>

      <div className="flex gap-3 border-t border-border/60 pt-4">
        <Input
          placeholder="Ask the Oracle…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !busy && ask()}
        />
        <Button onClick={ask} disabled={!input.trim() || busy}>
          Send
        </Button>
      </div>
    </div>
  );
}
