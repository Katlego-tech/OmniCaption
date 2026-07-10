"use client";

import { useState } from "react";

import { Badge, Button, Card, Input } from "@/components/ui";
import { api, ApiError } from "@/lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<"idle" | "loading" | "stub" | "error">("idle");
  const [detail, setDetail] = useState("");

  const search = async () => {
    setState("loading");
    try {
      await api.search(query.trim());
      // When Track 3 lands this will render ranked moments; today the backend
      // answers 501 and we fall through to the error branches below.
      setState("idle");
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
        Semantic moment search over keyframes and transcripts.
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

      {state === "stub" && (
        <Card className="border-primary/30">
          <h2 className="mb-2 font-medium text-primary-soft">Not built yet — honestly.</h2>
          <p className="text-sm leading-relaxed text-muted">
            The backend answered: “{detail}”. The Video-Oracle index (CLIP embeddings over
            keyframes + transcripts, tasks T086–T092) is the Track 3 stretch goal; this page is
            wired to the pinned API contract and lights up the moment the index ships.
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
