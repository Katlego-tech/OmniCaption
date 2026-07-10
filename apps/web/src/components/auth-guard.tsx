"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { KineticLoader } from "@/components/ui";
import { isAuthed } from "@/lib/auth";

/** Client-side gate for the dashboard. Static export has no server middleware,
 *  so this redirects unauthenticated visitors to /login; the backend is the
 *  real enforcement point for any authenticated call. */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isAuthed()) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <KineticLoader label="checking session…" />
      </div>
    );
  }
  return <>{children}</>;
}
