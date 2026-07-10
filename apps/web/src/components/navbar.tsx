import Link from "next/link";

export function Navbar() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Omni<span className="text-primary-soft">Caption</span>
        </Link>
        <div className="flex items-center gap-6 text-sm text-muted">
          <Link href="/#features" className="transition-colors hover:text-foreground">
            Features
          </Link>
          <Link href="/docs" className="transition-colors hover:text-foreground">
            Docs
          </Link>
          <Link href="/login" className="transition-colors hover:text-foreground">
            Log in
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-primary px-4 py-2 font-medium text-white transition-colors hover:bg-primary-soft"
          >
            Sign up →
          </Link>
        </div>
      </nav>
    </header>
  );
}
