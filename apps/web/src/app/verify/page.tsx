"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuroraHero } from "@/components/aurora-hero";
import { Button, Card, Input } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { setSession } from "@/lib/auth";

export default function VerifyPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError(null);
    setBusy(true);
    try {
      const res = await api.verify(token.trim());
      setSession(res.email, res.token);
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 429
            ? "Too many attempts — wait a moment."
            : "That verification token is invalid or expired."
          : "Could not reach the backend.",
      );
      setBusy(false);
    }
  };

  return (
    <AuroraHero>
      <div className="flex min-h-screen items-center justify-center px-6">
        <Card className="w-full max-w-sm fade-up">
          <Link href="/" className="mb-6 block text-lg font-semibold tracking-tight">
            Omni<span className="text-primary-soft">Caption</span>
          </Link>
          <h1 className="mb-1 text-xl font-semibold">Verify your email</h1>
          <p className="mb-6 text-sm text-muted">
            Paste the verification token from your email. (Dev: the token is written to the
            backend&apos;s <code className="font-mono">outbox/</code> and server log.)
          </p>
          <div className="space-y-3">
            <Input
              placeholder="verification token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
            <Button className="w-full" onClick={submit} disabled={busy || !token.trim()}>
              {busy ? "Verifying…" : "Verify & continue"}
            </Button>
            {error && <p className="text-sm text-warn">{error}</p>}
          </div>
          <p className="mt-6 text-center text-sm text-muted">
            <Link href="/login" className="text-primary-soft underline">
              Back to log in
            </Link>
          </p>
        </Card>
      </div>
    </AuroraHero>
  );
}
