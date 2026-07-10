"use client";

import { useState } from "react";

import { Badge, Button, Card, Input, KineticLoader } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import type { SearchHit } from "@/lib/types";

type ViewState = "idle" | "loading" | "results" | "stub" | "error";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<ViewState>("idle");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [detail, setDetail] = useState("");

  const search = async () => {
    setState("loading");
    try {
      const response = await api.search(query.trim());
      setHits(response.hits);
      setState("results");
    } catch (err) {
      if (err instanceof ApiError && err.status === 501) {
        setState("stub");
        setDetail(err.message);
      } else {
        setState("error");
        setDetail(err instanceof Error ? err.message : "Search failed.");
      }
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-2 flex items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Video Search</h1>
        <Badge tone="primary">Track 3</Badge>
      </div>
      <p className="mb-8 text-sm text-muted">
        Semantic moment search over captions and transcripts.
      </p>

      <div className="mb-8 flex gap-3">
        <Input
          placeholder='Try "person on a bike at night"…'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && query.trim() && search()}
        />
        <Button onClick={search} disabled={!query.trim() || state === "loading"}>
          Search
        </Button>
      </div>

      {state === "loading" && <KineticLoader label="searching…" />}

      {state === "results" && hits.length === 0 && (
        <Card>
          <p className="text-sm text-muted">No indexed moments matched that query.</p>
        </Card>
      )}
      {state === "results" && hits.length > 0 && (
        <div className="space-y-3">
          {hits.map((hit, i) => (
            <Card key={`${hit.task_id}-${i}`} className="fade-up">
              <div className="mb-2 flex items-center gap-3">
                <span className="font-mono text-sm text-primary-soft">{hit.task_id}</span>
                {hit.style && <Badge>{hit.style}</Badge>}
                {hit.t_start !== null && (
                  <span className="text-xs text-faint">@ {hit.t_start.toFixed(1)}s</span>
                )}
                <span className="ml-auto text-xs text-faint">
                  score {hit.score.toFixed(3)}
                </span>
              </div>
              <p className="text-sm leading-relaxed text-foreground/90">{hit.text}</p>
            </Card>
          ))}
        </div>
      )}

      {state === "stub" && (
        <Card className="border-primary/30">
          <h2 className="mb-2 font-medium text-primary-soft">Index not built yet.</h2>
          <p className="text-sm leading-relaxed text-muted">
            The backend answered: “{detail}”. Build it with{" "}
            <code className="font-mono text-xs">python -m oracle.cli build</code> (see
            services/oracle) and this page lights up.
          </p>
        </Card>
      )}
      {state === "error" && (
        <Card className="border-warn/40">
          <p className="text-sm text-muted">{detail}</p>
        </Card>
      )}
    </div>
  );
}
