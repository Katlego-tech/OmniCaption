import type { ReactNode } from "react";

import { AuthGuard } from "@/components/auth-guard";
import { Sidebar } from "@/components/sidebar";
import { UserChip } from "@/components/user-chip";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-x-hidden">
          <header className="flex items-center justify-end border-b border-border/60 px-8 py-3">
            <UserChip />
          </header>
          <main className="flex-1 px-8 py-8">{children}</main>
        </div>
      </div>
    </AuthGuard>
  );
}
