"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon, ICONS8_ATTRIBUTION_URL } from "@/components/icon";
import { cn } from "@/components/ui";

const LINKS = [
  { href: "/dashboard", label: "Home", icon: "home" },
  { href: "/dashboard/captioner", label: "Captioner", icon: "clapperboard" },
  { href: "/dashboard/search", label: "Search", icon: "search" },
  { href: "/dashboard/oracle", label: "Oracle", icon: "chat" },
  { href: "/dashboard/accounts", label: "Accounts", icon: "settings" },
  { href: "/docs", label: "Docs", icon: "book" },
];

// Tokens from globals.css, as hex for the Icons8 CDN color segment.
const ICON_ACTIVE = "ff4d5a";
const ICON_MUTED = "9b9ba6";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-52 shrink-0 flex-col gap-1 border-r border-border/60 bg-surface/60 p-4 backdrop-blur">
      <Link href="/" className="mb-4 px-3 text-base font-semibold tracking-tight">
        Omni<span className="text-primary-soft">Caption</span>
      </Link>
      {LINKS.map((link) => {
        const active =
          link.href === "/dashboard" ? pathname === link.href : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              active
                ? "bg-primary/15 text-primary-soft"
                : "text-muted hover:bg-card-hover hover:text-foreground",
            )}
          >
            <Icon name={link.icon} size={18} color={active ? ICON_ACTIVE : ICON_MUTED} />
            {link.label}
          </Link>
        );
      })}
      <div className="mt-auto px-3 pt-6 text-xs text-faint">
        AMD Hackathon ACT II
        <br />
        Track 2 · v1.0.0
        <br />
        <a
          href={ICONS8_ATTRIBUTION_URL}
          className="underline transition-colors hover:text-muted"
        >
          Icons by Icons8
        </a>
      </div>
    </aside>
  );
}
