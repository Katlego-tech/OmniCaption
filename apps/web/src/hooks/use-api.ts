"use client";

/** Small client-side data hooks — plain React, no query library, so the static
 *  export stays dependency-light. */

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import type { ClipResult, RunStatus, Task } from "@/lib/types";

interface Loadable<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

function useLoad<T>(loader: () => Promise<T>): Loadable<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loader()
      .then((value) => {
        if (!cancelled) {
          setData(value);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload };
}

export function useTasks(): Loadable<Task[]> {
  return useLoad(useCallback(() => api.listTasks(), []));
}

export function useResults(): Loadable<ClipResult[]> {
  return useLoad(useCallback(() => api.listResults(), []));
}

/** Poll the run status while a pipeline run is in flight. */
export function useRunStatus(onFinish?: () => void): {
  status: RunStatus | null;
  refresh: () => void;
} {
  const [status, setStatus] = useState<RunStatus | null>(null);
  const onFinishRef = useRef(onFinish);
  onFinishRef.current = onFinish;

  const refresh = useCallback(() => {
    api
      .runStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (status?.state !== "running") return;
    const timer = setInterval(async () => {
      try {
        const next = await api.runStatus();
        setStatus(next);
        if (next.state !== "running") onFinishRef.current?.();
      } catch {
        // backend momentarily unreachable — keep polling
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [status?.state]);

  return { status, refresh };
}
