/** Minimal shadcn-style primitives, in-repo (no registry dependency). */

import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium",
        "transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" &&
          "bg-primary text-white hover:bg-primary-soft shadow-[0_0_24px_-8px] shadow-primary/60",
        variant === "ghost" && "border border-border text-foreground hover:bg-card-hover",
        className,
      )}
      {...props}
    />
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("glow-card rounded-xl border border-border bg-card p-5", className)}>
      {children}
    </div>
  );
}

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm",
        "placeholder:text-faint focus:border-primary focus:outline-none",
        className,
      )}
      {...props}
    />
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "ok" | "warn" | "primary";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        tone === "neutral" && "border-border text-muted",
        tone === "ok" && "border-ok/40 text-ok",
        tone === "warn" && "border-warn/40 text-warn",
        tone === "primary" && "border-primary/40 text-primary-soft",
      )}
    >
      {children}
    </span>
  );
}

export function KineticLoader({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted">
      <span className="inline-flex gap-1">
        <span className="kinetic-dot h-1.5 w-1.5 rounded-full bg-primary-soft" />
        <span className="kinetic-dot h-1.5 w-1.5 rounded-full bg-primary-soft" />
        <span className="kinetic-dot h-1.5 w-1.5 rounded-full bg-primary-soft" />
      </span>
      {label}
    </span>
  );
}
