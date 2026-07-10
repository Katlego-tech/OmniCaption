import Link from "next/link";

import { AuroraHero } from "@/components/aurora-hero";
import { FlipText } from "@/components/flip-text";
import { Navbar } from "@/components/navbar";
import { Card } from "@/components/ui";

const FEATURES = [
  {
    title: "4 caption styles",
    body: "Formal, sarcastic, humorous tech and non-tech — every caption grounded in the clip's actual audio and frames. The joke is creative; the facts are not.",
  },
  {
    title: "AMD compute, end to end",
    body: "Local faster-whisper STT on CTranslate2-HIP (ROCm) plus the Kimi-K2P6 VLM served from Fireworks AI's AMD MI300X backend.",
  },
  {
    title: "Under 30 s per clip",
    body: "Strict budgets: ≤10 min per batch, <30 s per request, ≤10 GB image (ships at 9.58 GB), <60 s cold start — enforced in code and CI.",
  },
  {
    title: "Deterministic I/O",
    body: "Schema-valid results.json every run, exit code 0 even on partial failure, deterministic fallbacks so no requested style is ever missing.",
  },
  {
    title: "Sequential VRAM discipline",
    body: "STT and VLM are never co-resident: explicit memory reclamation between pipeline stages keeps the whole run inside the VRAM budget.",
  },
  {
    title: "Always-green main",
    body: "76 tests across the pipeline and API, golden-clip regression pins on tone-bearing surfaces, and a pre-push gate that refuses red pushes.",
  },
];

const STACK = ["PyTorch ROCm", "faster-whisper", "OpenCV", "Fireworks AI", "FastAPI", "Next.js"];

const FAQ = [
  {
    q: "What styles are supported?",
    a: "formal, sarcastic, humorous_tech and humorous_non_tech. Every requested style always gets a caption — on model failure a deterministic evidence-based fallback is emitted instead, because a missing style scores zero.",
  },
  {
    q: "How does AMD compute work here?",
    a: "Speech-to-text runs locally on CTranslate2-HIP (ROCm). Vision-language synthesis calls Kimi-K2P6 on Fireworks AI, which serves it from AMD MI300X accelerators. Device logs and request evidence are captured for judging.",
  },
  {
    q: "Is my API key stored securely?",
    a: "Your Fireworks key lives only in this browser's localStorage and is sent only to the backend you configure. Nothing is persisted server-side.",
  },
];

export default function LandingPage() {
  return (
    <div>
      <Navbar />

      <AuroraHero>
        <div className="mx-auto flex max-w-4xl flex-col items-center px-6 py-28 text-center">
          <h1 className="fade-up text-5xl font-bold leading-tight tracking-tight sm:text-6xl">
            AI video captions that are <FlipText words={["grounded", "fast", "funny", "formal"]} />
          </h1>
          <p
            className="fade-up mt-6 max-w-2xl text-lg text-muted"
            style={{ animationDelay: "0.15s" }}
          >
            A dual-model hybrid pipeline on AMD compute: local Whisper transcription, keyframe
            vision, and one VLM pass that writes four distinct caption styles per clip.
          </p>
          <div className="fade-up mt-10 flex gap-4" style={{ animationDelay: "0.3s" }}>
            <Link
              href="/dashboard"
              className="rounded-lg bg-primary px-6 py-3 font-medium text-white shadow-[0_0_32px_-8px] shadow-primary/70 transition-colors hover:bg-primary-soft"
            >
              Get started →
            </Link>
            <Link
              href="/docs"
              className="rounded-lg border border-border px-6 py-3 font-medium text-foreground transition-colors hover:bg-card-hover"
            >
              View docs
            </Link>
          </div>
        </div>
      </AuroraHero>

      <section id="features" className="mx-auto max-w-6xl px-6 py-20">
        <h2 className="mb-10 text-center text-3xl font-semibold tracking-tight">
          Built for the AMD Developer Hackathon, judged on the details
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <Card key={feature.title}>
              <h3 className="mb-2 font-semibold text-primary-soft">{feature.title}</h3>
              <p className="text-sm leading-relaxed text-muted">{feature.body}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-y border-border/60 bg-surface/50 py-10">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-center gap-x-10 gap-y-4 px-6 text-sm font-medium text-faint">
          {STACK.map((name) => (
            <span key={name} className="transition-colors hover:text-muted">
              {name}
            </span>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-6 py-20">
        <h2 className="mb-8 text-center text-3xl font-semibold tracking-tight">FAQ</h2>
        <div className="space-y-3">
          {FAQ.map((item) => (
            <details
              key={item.q}
              className="group rounded-xl border border-border bg-card px-5 py-4 open:bg-card-hover"
            >
              <summary className="cursor-pointer list-none font-medium marker:hidden">
                <span className="mr-2 inline-block text-primary-soft transition-transform group-open:rotate-90">
                  ›
                </span>
                {item.q}
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-muted">{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      <footer className="border-t border-border/60 py-8 text-center text-sm text-faint">
        © 2026 OmniCaption ·{" "}
        <a
          href="https://github.com/Katlego-tech/OmniCaption"
          className="transition-colors hover:text-muted"
        >
          GitHub
        </a>{" "}
        ·{" "}
        <Link href="/docs" className="transition-colors hover:text-muted">
          Docs
        </Link>
      </footer>
    </div>
  );
}
