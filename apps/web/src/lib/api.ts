/** Typed fetch wrapper over the services/api REST contract. */

import { getToken } from "./auth";
import { getApiUrl, getFireworksKey } from "./store";
import type {
  AuthResponse,
  ClipResult,
  QAResponse,
  RunStatus,
  SearchResponse,
  Task,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    detail: string,
  ) {
    super(detail);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const fireworksKey = getFireworksKey();
  const token = getToken();
  const resp = await fetch(`${getApiUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(fireworksKey ? { "X-Fireworks-Key": fireworksKey } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
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
  // 204 No Content (deletes) has an empty body — nothing to parse.
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>("/api/health"),

  // --- auth ---
  signup: (email: string, password: string) =>
    request<AuthResponse>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<{ email: string }>("/api/auth/me"),

  // --- tasks ---
  listTasks: () => request<Task[]>("/api/tasks"),
  submitTasks: (tasks: Task[]) =>
    request<Task[]>("/api/tasks", { method: "POST", body: JSON.stringify(tasks) }),
  deleteTask: (taskId: string) =>
    request<void>(`/api/tasks/${encodeURIComponent(taskId)}`, { method: "DELETE" }),
  clearTasks: () => request<void>("/api/tasks", { method: "DELETE" }),

  triggerRun: () => request<RunStatus>("/api/tasks/run", { method: "POST" }),
  runStatus: () => request<RunStatus>("/api/tasks/run"),

  // --- results ---
  listResults: () => request<ClipResult[]>("/api/results"),
  deleteResult: (taskId: string) =>
    request<void>(`/api/results/${encodeURIComponent(taskId)}`, { method: "DELETE" }),
  clearResults: () => request<void>("/api/results", { method: "DELETE" }),

  validateKey: (apiKey: string) =>
    request<{ valid: boolean }>("/api/keys/validate", {
      method: "POST",
      body: JSON.stringify({ api_key: apiKey }),
    }),

  search: (query: string) =>
    request<SearchResponse>("/api/search", { method: "POST", body: JSON.stringify({ query }) }),

  qa: (question: string) =>
    request<QAResponse>("/api/qa", { method: "POST", body: JSON.stringify({ question }) }),
};
