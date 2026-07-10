"use client";

import { useEffect, useRef, useState } from "react";

/** Counts up from 0 to the target value on mount / when the value changes. */
export function AnimatedNumber({ value, durationMs = 900 }: { value: number; durationMs?: number }) {
  const [shown, setShown] = useState(0);
  const frame = useRef<number>(0);

  useEffect(() => {
    const start = performance.now();
    const animate = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(Math.round(eased * value));
      if (t < 1) frame.current = requestAnimationFrame(animate);
    };
    frame.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame.current);
  }, [value, durationMs]);

  return <span className="tabular-nums">{shown}</span>;
}
