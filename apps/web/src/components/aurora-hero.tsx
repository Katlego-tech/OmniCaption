import type { ReactNode } from "react";

/** Aurora hero background — animated gradient blobs behind the hero content. */
export function AuroraHero({ children }: { children: ReactNode }) {
  return (
    <section className="relative overflow-hidden">
      <div
        className="aurora-blob h-[420px] w-[420px] bg-primary"
        style={{ top: "-10%", left: "8%" }}
      />
      <div
        className="aurora-blob h-[360px] w-[360px] bg-[#7c3aed]"
        style={{ top: "10%", right: "5%", animationDelay: "-5s" }}
      />
      <div
        className="aurora-blob h-[300px] w-[300px] bg-[#0ea5e9]"
        style={{ bottom: "-20%", left: "40%", animationDelay: "-9s" }}
      />
      <div className="relative z-10">{children}</div>
    </section>
  );
}
