/** Typed fetch wrapper over the services/api REST contract. */

import { getApiUrl } from "./store";
import type { ClipResult, RunStatus, Task } from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    detail: string,
  ) {
    super(detail);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${getApiUrl()}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body — keep the status text
    }
    throw new ApiError(resp.status, detail);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>("/api/health"),

  listTasks: () => request<Task[]>("/api/tasks"),
  submitTasks: (tasks: Task[]) =>
    request<Task[]>("/api/tasks", { method: "POST", body: JSON.stringify(tasks) }),

  triggerRun: () => request<RunStatus>("/api/tasks/run", { method: "POST" }),
  runStatus: () => request<RunStatus>("/api/tasks/run"),

  listResults: () => request<ClipResult[]>("/api/results"),

  validateKey: (apiKey: string) =>
    request<{ valid: boolean }>("/api/keys/validate", {
      method: "POST",
      body: JSON.stringify({ api_key: apiKey }),
    }),

  search: (query: string) =>
    request<unknown>("/api/search", { method: "POST", body: JSON.stringify({ query }) }),

  qa: (question: string) =>
    request<unknown>("/api/qa", { method: "POST", body: JSON.stringify({ question }) }),
};
