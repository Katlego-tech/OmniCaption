"use client";

import { useEffect, useState } from "react";

/** Cycles through words with a flip-in animation. */
export function FlipText({ words, intervalMs = 2200 }: { words: string[]; intervalMs?: number }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setIndex((i) => (i + 1) % words.length), intervalMs);
    return () => clearInterval(timer);
  }, [words.length, intervalMs]);

  return (
    <span key={index} className="flip-in text-primary-soft">
      {words[index]}
    </span>
  );
}
