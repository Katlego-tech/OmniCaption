"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuroraHero } from "@/components/aurora-hero";
import { Button, Card, Input } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { setSession } from "@/lib/auth";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isSignup = mode === "signup";
  const title = isSignup ? "Create your account" : "Welcome back";
  const cta = isSignup ? "Sign up" : "Log in";

  const submit = async () => {
    setError(null);
    setBusy(true);
    try {
      const call = isSignup ? api.signup : api.login;
      const res = await call(email.trim(), password);
      setSession(res.email, res.token);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.status === 422
            ? "Enter a valid email and a password of at least 8 characters."
            : err.message,
        );
      } else {
        setError("Could not reach the backend. Check the API URL on the Accounts page.");
      }
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
          <h1 className="mb-1 text-xl font-semibold">{title}</h1>
          <p className="mb-6 text-sm text-muted">
            {isSignup ? "Start captioning in seconds." : "Log in to your dashboard."}
          </p>

          <div className="space-y-3">
            <Input
              type="email"
              placeholder="you@example.com"
              value={email}
              autoComplete="email"
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
            <Input
              type="password"
              placeholder="Password (min 8 chars)"
              value={password}
              autoComplete={isSignup ? "new-password" : "current-password"}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
            <Button
              className="w-full"
              onClick={submit}
              disabled={busy || !email.trim() || password.length < 8}
            >
              {busy ? "Please wait…" : cta}
            </Button>
            {error && <p className="text-sm text-warn">{error}</p>}
          </div>

          <p className="mt-6 text-center text-sm text-muted">
            {isSignup ? (
              <>
                Already have an account?{" "}
                <Link href="/login" className="text-primary-soft underline">
                  Log in
                </Link>
              </>
            ) : (
              <>
                No account?{" "}
                <Link href="/signup" className="text-primary-soft underline">
                  Sign up
                </Link>
              </>
            )}
          </p>
        </Card>
      </div>
    </AuroraHero>
  );
}
