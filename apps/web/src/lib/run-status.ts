/**
 * Honest run reporting.
 *
 * The captioner always exits 0 (the eval harness scores on output presence), so
 * a subprocess exit code of 0 only means "the process finished" — NOT "captions
 * were produced". When a stage fails before synthesis, results.json is backfilled
 * with empty caption strings and the run still exits 0. Reporting that as a plain
 * green success (and hiding the diagnostic log) violates the project's
 * "report failures honestly" non-negotiable.
 *
 * {@link describeRun} folds the exit-code state together with the actual caption
 * output so the UI can show "completed with errors" and surface the captured log
 * whenever a finished run produced no usable captions.
 */

import type { ClipResult, RunStatus } from "@/lib/types";

/** Number of requested captions that came back empty/whitespace across all clips. */
export function countEmptyCaptions(results: ClipResult[] | null | undefined): number {
  if (!results) return 0;
  let empty = 0;
  for (const clip of results) {
    for (const text of Object.values(clip.captions)) {
      if (!text || !text.trim()) empty += 1;
    }
  }
  return empty;
}

export interface RunPresentation {
  /** Badge tone, or null when the caller renders its own (running / idle). */
  tone: "ok" | "warn" | null;
  /** Badge label, or null for running / idle. */
  badge: string | null;
  /** Whether to show the diagnostic log block. */
  showLog: boolean;
  /** The captured pipeline log (stderr preferred, stdout fallback), trimmed. */
  logText: string;
  /** An honest one-line explanation, shown when a run is degraded. */
  note: string | null;
}

/**
 * Turn a run status + the captions it produced into an honest UI presentation.
 *
 * A "succeeded" (exit 0) run that produced one or more empty captions is treated
 * as degraded: warn badge, explanatory note, and the diagnostic log is shown so
 * the underlying stage failure is visible instead of hidden behind a green badge.
 */
export function describeRun(
  status: RunStatus | null,
  results: ClipResult[] | null | undefined,
): RunPresentation {
  const logText = status?.stderr?.trim() || status?.stdout?.trim() || "";
  const state = status?.state;

  if (state === "succeeded") {
    const empty = countEmptyCaptions(results);
    if (empty > 0) {
      return {
        tone: "warn",
        badge: "completed with errors",
        showLog: true,
        logText,
        note:
          `The run exited cleanly (code 0) but produced ${empty} empty ` +
          `caption${empty === 1 ? "" : "s"} — a stage failed before synthesis. ` +
          `See the diagnostic log below.`,
      };
    }
    return { tone: "ok", badge: "last run succeeded", showLog: false, logText, note: null };
  }

  if (state === "failed") {
    return {
      tone: "warn",
      badge: `last run failed (exit ${status?.returncode})`,
      showLog: true,
      logText,
      note: null,
    };
  }

  // running / idle / no status — caller handles the visuals.
  return { tone: null, badge: null, showLog: false, logText, note: null };
}
