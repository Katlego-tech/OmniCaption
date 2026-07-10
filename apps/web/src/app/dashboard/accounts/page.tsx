"use client";

import { useEffect, useState } from "react";

import { Badge, Button, Card, Input } from "@/components/ui";
import { api } from "@/lib/api";
import {
  DEFAULT_API_URL,
  getApiUrl,
  getFireworksKey,
  setApiUrl,
  setFireworksKey,
} from "@/lib/store";

type KeyState = "unknown" | "checking" | "valid" | "invalid" | "unreachable";

export default function AccountsPage() {
  const [apiUrl, setApiUrlInput] = useState(DEFAULT_API_URL);
  const [health, setHealth] = useState<{ ok: boolean; latencyMs: number } | null>(null);
  const [fireworksKey, setFireworksKeyInput] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [keyState, setKeyState] = useState<KeyState>("unknown");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setApiUrlInput(getApiUrl());
    setFireworksKeyInput(getFireworksKey());
  }, []);

  const checkHealth = async () => {
    setHealth(null);
    const start = performance.now();
    try {
      await api.health();
      setHealth({ ok: true, latencyMs: Math.round(performance.now() - start) });
    } catch {
      setHealth({ ok: false, latencyMs: 0 });
    }
  };

  const validateKey = async () => {
    setKeyState("checking");
    try {
      const result = await api.validateKey(fireworksKey.trim());
      setKeyState(result.valid ? "valid" : "invalid");
    } catch {
      setKeyState("unreachable");
    }
  };

  const save = () => {
    setApiUrl(apiUrl.trim());
    setFireworksKey(fireworksKey.trim());
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-8 text-2xl font-semibold tracking-tight">Accounts &amp; API keys</h1>

      <Card className="mb-6">
        <h2 className="mb-1 font-medium">Backend API URL</h2>
        <p className="mb-4 text-sm text-muted">
          Where the OmniCaption FastAPI backend runs. Stored in this browser only.
        </p>
        <div className="flex gap-3">
          <Input
            value={apiUrl}
            onChange={(e) => setApiUrlInput(e.target.value)}
            placeholder={DEFAULT_API_URL}
          />
          <Button variant="ghost" onClick={checkHealth}>
            Test
          </Button>
        </div>
        {health && (
          <p className="mt-3 text-sm">
            {health.ok ? (
              <Badge tone="ok">connected · {health.latencyMs} ms</Badge>
            ) : (
              <Badge tone="warn">unreachable</Badge>
            )}
          </p>
        )}
      </Card>

      <Card className="mb-6">
        <h2 className="mb-1 font-medium">Fireworks AI API key</h2>
        <p className="mb-4 text-sm text-muted">
          Kept in localStorage, never persisted server-side; sent only to your configured backend
          for validation.
        </p>
        <div className="flex gap-3">
          <Input
            type={showKey ? "text" : "password"}
            value={fireworksKey}
            onChange={(e) => {
              setFireworksKeyInput(e.target.value);
              setKeyState("unknown");
            }}
            placeholder="fw-…"
          />
          <Button variant="ghost" onClick={() => setShowKey((v) => !v)}>
            {showKey ? "Hide" : "Show"}
          </Button>
          <Button onClick={validateKey} disabled={!fireworksKey.trim() || keyState === "checking"}>
            Validate
          </Button>
        </div>
        <p className="mt-3 text-sm">
          {keyState === "checking" && <Badge>checking…</Badge>}
          {keyState === "valid" && <Badge tone="ok">key accepted by Fireworks</Badge>}
          {keyState === "invalid" && <Badge tone="warn">key rejected (401/403)</Badge>}
          {keyState === "unreachable" && (
            <Badge tone="warn">could not reach the backend / Fireworks</Badge>
          )}
        </p>
      </Card>

      <div className="flex items-center gap-4">
        <Button onClick={save}>Save configuration</Button>
        {saved && <span className="text-sm text-ok">Saved.</span>}
      </div>
    </div>
  );
}
