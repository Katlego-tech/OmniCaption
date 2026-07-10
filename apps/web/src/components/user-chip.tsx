"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui";
import { api } from "@/lib/api";
import { clearSession, getEmail } from "@/lib/auth";

export function UserChip() {
  const router = useRouter();
  const [email, setEmail] = useState("");

  useEffect(() => {
    setEmail(getEmail());
  }, []);

  const logout = async () => {
    // Revoke the token server-side (logout-everywhere); clear locally regardless.
    try {
      await api.logout();
    } catch {
      // best-effort — still clear the local session below
    }
    clearSession();
    router.replace("/login");
  };

  return (
    <div className="flex items-center gap-3">
      {email && <span className="text-sm text-muted">{email}</span>}
      <Button variant="ghost" onClick={logout} className="px-3 py-1.5 text-xs">
        Log out
      </Button>
    </div>
  );
}
