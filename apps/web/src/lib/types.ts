/** Mirrors the backend contract in services/api (docs/16-io-contract.md). */

export const ALL_STYLES = [
  "formal",
  "sarcastic",
  "humorous_tech",
  "humorous_non_tech",
] as const;

export type Style = (typeof ALL_STYLES)[number];

export const STYLE_LABELS: Record<Style, string> = {
  formal: "Formal",
  sarcastic: "Sarcastic",
  humorous_tech: "Humorous (tech)",
  humorous_non_tech: "Humorous (non-tech)",
};

export interface Task {
  task_id: string;
  video_url: string;
  styles: Style[];
}

export interface ClipResult {
  task_id: string;
  captions: Partial<Record<Style, string>>;
}

export type RunState = "idle" | "running" | "succeeded" | "failed";

export interface RunStatus {
  state: RunState;
  returncode: number | null;
}

export interface SearchHit {
  task_id: string;
  kind: string;
  style: string | null;
  text: string;
  t_start: number | null;
  t_end: number | null;
  score: number;
}

export interface SearchResponse {
  query: string;
  hits: SearchHit[];
}

export interface QAResponse {
  answer: string;
  citations: SearchHit[];
}
