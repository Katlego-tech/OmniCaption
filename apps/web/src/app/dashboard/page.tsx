"use client";

import Link from "next/link";

import { AnimatedNumber } from "@/components/animated-number";
import { Badge, Card, KineticLoader } from "@/components/ui";
import { useResults, useRunStatus, useTasks } from "@/hooks/use-api";
import { STYLE_LABELS, type Style } from "@/lib/types";

export default function DashboardPage() {
  const tasks = useTasks();
  const results = useResults();
  const { status } = useRunStatus(() => {
    tasks.reload();
    results.reload();
  });

  const captionCount = (results.data ?? []).reduce(
    (sum, clip) => sum + Object.keys(clip.captions).length,
    0,
  );
  const offline = tasks.error !== null && results.error !== null;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        {status?.state === "running" ? (
          <KineticLoader label="pipeline running…" />
        ) : (
          <Badge tone={offline ? "warn" : "ok"}>
            {offline ? "backend unreachable" : "backend connected"}
          </Badge>
        )}
      </div>

      {offline && (
        <Card className="mb-6 border-warn/40">
          <p className="text-sm text-muted">
            Could not reach the backend API. Set its URL on the{" "}
            <Link href="/dashboard/accounts" className="text-primary-soft underline">
              Accounts page
            </Link>{" "}
            (default <code className="font-mono">http://localhost:8000</code>).
          </p>
        </Card>
      )}

      <div className="mb-10 grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-4xl font-semibold text-primary-soft">
            <AnimatedNumber value={tasks.data?.length ?? 0} />
          </p>
          <p className="mt-1 text-sm text-muted">Tasks queued</p>
        </Card>
        <Card>
          <p className="text-4xl font-semibold text-primary-soft">
            <AnimatedNumber value={results.data?.length ?? 0} />
          </p>
          <p className="mt-1 text-sm text-muted">Clips captioned</p>
        </Card>
        <Card>
          <p className="text-4xl font-semibold text-primary-soft">
            <AnimatedNumber value={captionCount} />
          </p>
          <p className="mt-1 text-sm text-muted">Captions generated</p>
        </Card>
      </div>

      <h2 className="mb-4 text-lg font-medium">Recent results</h2>
      {results.data && results.data.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Task</th>
                <th className="px-4 py-3 font-medium">Styles delivered</th>
              </tr>
            </thead>
            <tbody>
              {results.data.map((clip) => (
                <tr key={clip.task_id} className="border-b border-border/50 last:border-0">
                  <td className="px-4 py-3 font-mono text-primary-soft">{clip.task_id}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {(Object.keys(clip.captions) as Style[]).map((style) => (
                        <Badge key={style} tone="neutral">
                          {STYLE_LABELS[style] ?? style}
                        </Badge>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Card>
          <p className="text-sm text-muted">
            No results yet. Queue a clip in the{" "}
            <Link href="/dashboard/captioner" className="text-primary-soft underline">
              Captioner
            </Link>{" "}
            and trigger a run.
          </p>
        </Card>
      )}
    </div>
  );
}
