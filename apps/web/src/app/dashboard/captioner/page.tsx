"use client";

import { useState } from "react";

import { CaptionCard } from "@/components/caption-card";
import { Badge, Button, Card, Input, KineticLoader } from "@/components/ui";
import { useResults, useRunStatus, useTasks } from "@/hooks/use-api";
import { api, ApiError } from "@/lib/api";
import { ALL_STYLES, STYLE_LABELS, type Style } from "@/lib/types";

export default function CaptionerPage() {
  const tasks = useTasks();
  const results = useResults();
  const { status, refresh } = useRunStatus(() => {
    tasks.reload();
    results.reload();
  });

  const [taskId, setTaskId] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [styles, setStyles] = useState<Style[]>([...ALL_STYLES]);
  const [message, setMessage] = useState<string | null>(null);

  const toggleStyle = (style: Style) =>
    setStyles((current) =>
      current.includes(style) ? current.filter((s) => s !== style) : [...current, style],
    );

  const submit = async () => {
    setMessage(null);
    try {
      const id = taskId.trim() || `v${(tasks.data?.length ?? 0) + 1}`;
      await api.submitTasks([{ task_id: id, video_url: videoUrl.trim(), styles }]);
      setTaskId("");
      setVideoUrl("");
      tasks.reload();
      setMessage(`Task ${id} queued.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Submission failed.");
    }
  };

  const run = async () => {
    setMessage(null);
    try {
      await api.triggerRun();
      refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setMessage("A run is already in progress.");
        refresh();
      } else {
        setMessage(err instanceof Error ? err.message : "Could not trigger the run.");
      }
    }
  };

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="mb-8 text-2xl font-semibold tracking-tight">Captioner Hub</h1>

      <div className="mb-10 grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-4 font-medium">Queue a clip</h2>
          <div className="space-y-3">
            <Input
              placeholder="task id (optional, e.g. v1)"
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
            />
            <Input
              placeholder="https://…/clip.mp4"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              {ALL_STYLES.map((style) => (
                <button
                  key={style}
                  type="button"
                  onClick={() => toggleStyle(style)}
                  className={
                    styles.includes(style)
                      ? "rounded-full border border-primary/50 bg-primary/15 px-3 py-1 text-xs text-primary-soft"
                      : "rounded-full border border-border px-3 py-1 text-xs text-muted hover:text-foreground"
                  }
                >
                  {STYLE_LABELS[style]}
                </button>
              ))}
            </div>
            <Button onClick={submit} disabled={!videoUrl.trim() || styles.length === 0}>
              Add task
            </Button>
          </div>
        </Card>

        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-medium">Pipeline</h2>
            {status?.state === "running" && <KineticLoader label="running…" />}
            {status?.state === "succeeded" && <Badge tone="ok">last run succeeded</Badge>}
            {status?.state === "failed" && (
              <Badge tone="warn">last run failed (exit {status.returncode})</Badge>
            )}
            {(!status || status.state === "idle") && <Badge>idle</Badge>}
          </div>
          <p className="mb-4 text-sm text-muted">
            {tasks.data?.length ?? 0} task(s) queued. Running the pipeline processes the whole
            manifest: download → Whisper STT → keyframes → VLM synthesis → results.json.
          </p>
          <Button onClick={run} disabled={status?.state === "running"}>
            {status?.state === "running" ? "Run in progress…" : "▶ Run pipeline"}
          </Button>
          {message && <p className="mt-3 text-sm text-warn">{message}</p>}
        </Card>
      </div>

      {tasks.data && tasks.data.length > 0 && (
        <>
          <h2 className="mb-4 text-lg font-medium">Queued tasks</h2>
          <div className="mb-10 space-y-2">
            {tasks.data.map((task) => (
              <div
                key={task.task_id}
                className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 text-sm"
              >
                <span className="font-mono text-primary-soft">{task.task_id}</span>
                <span className="min-w-0 flex-1 truncate text-muted">{task.video_url}</span>
                <span className="text-xs text-faint">{task.styles.length} styles</span>
              </div>
            ))}
          </div>
        </>
      )}

      <h2 className="mb-4 text-lg font-medium">Captions</h2>
      {results.data && results.data.length > 0 ? (
        <div className="space-y-8">
          {results.data.map((clip) => (
            <div key={clip.task_id}>
              <p className="mb-3 font-mono text-sm text-primary-soft">{clip.task_id}</p>
              <div className="grid gap-4 sm:grid-cols-2">
                {(Object.entries(clip.captions) as [Style, string][]).map(([style, text]) => (
                  <CaptionCard key={style} style={style} text={text} />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Card>
          <p className="text-sm text-muted">
            No captions yet — queue a clip and run the pipeline.
          </p>
        </Card>
      )}
    </div>
  );
}
