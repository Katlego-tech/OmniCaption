# Research & Technical Decisions: OmniCaption

**Feature branch:** `001-omnicaption-captioning`
**Plan:** [plan.md](plan.md) · **Spec:** [spec.md](spec.md)
**Primary source:** `Hackathon Research for AI Video Captioning.pdf` (repo root) — cited below as
**[Research PDF]**. See also [docs/09-research-summary](../../docs/09-research-summary.md).

This document records the significant technical decisions, each as **Decision → Rationale →
Alternatives considered → Why deferred**. It resolves the design questions that shaped
[plan.md](plan.md) and the stage contracts.

---

## D1 — Dual-model hybrid vs monolithic VLM

**Decision.** Use a **hybrid** pipeline: a dedicated speech-to-text model (faster-whisper) for audio
plus a vision-language model (Gemma 4 E4B-it) for image+text synthesis, rather than a single
end-to-end video model that ingests raw audio+video together.

**Rationale.**
- The **[Research PDF]** finds that specialized STT dramatically outperforms VLM-native audio
  understanding on transcription accuracy at a fraction of the VRAM, and that grounding captions in an
  accurate transcript raises visual-fidelity scores.
- Separation lets each model run at its optimal precision and be **loaded sequentially**, keeping peak
  VRAM within the 8 GB-class budget (see D2).
- Each stage is independently testable and mockable, which the test-first constitution requires.

**Alternatives considered.**
- *Monolithic multimodal Gemma taking audio + video directly.* Deferred: higher peak VRAM (audio
  encoder + long video token context co-resident), weaker transcription, and harder to fit the ≤10 GB
  image and <30 s/request budgets. Revisit only if a single model demonstrably beats the hybrid on Φ
  within budget.
- *A large monolithic VLM with an external ASR API.* Rejected: network dependence at eval time is
  fragile and the harness environment is not guaranteed to have outbound access.

---

## D2 — Sequential VRAM loading (never co-resident)

**Decision.** Load Whisper, transcribe fully, **tear it down** (`del` → `gc.collect()` →
`torch.cuda.empty_cache()`) in a dedicated **Memory Reclamation** stage, and only then load Gemma 4
E4B in 4-bit for synthesis.

**Rationale.**
- Target AMD range includes **8 GB cards (e.g. RX 6600)**. Whisper + a 4-bit Gemma 4 E4B co-resident
  would OOM. The **[Research PDF]** measures that neither model alone exceeds the budget, but their sum
  does.
- The trade is one extra model-load's wall-clock time for the ability to run on the **entire AMD GPU
  target range** — an acceptable cost inside the ≤10 min batch budget.
- Reclamation is made an **explicit pipeline stage** (S3), not an incidental `del`, so it is testable
  and observable (log freed VRAM).

**Alternatives considered.**
- *Keep both resident for speed.* Deferred to MI300X-only lanes where VRAM is abundant; not safe as
  the default because it forfeits small-card compatibility.
- *Offload Whisper to CPU while VLM runs.* Rejected: CPU STT is far slower and complicates the AMD
  compute-usage proof.

---

## D3 — Keyframe extraction vs all-frames (token budget)

**Decision.** Sample **scene-change keyframes** with an OpenCV pixel-variance heuristic, capped at a
configurable maximum, instead of feeding every frame to the VLM.

**Rationale.**
- The VLM's context/token budget and the <30 s/request limit make all-frames infeasible; most frames
  are near-duplicates.
- Pixel-variance scene detection is **cheap, CPU-side, and adds no GPU model weight** — it does not
  compete with the models for VRAM.
- Capping keyframes bounds the image-token count, protecting both latency and the modality-ordering
  prompt from overflow.
- A **static-clip fallback** (first/mid/last) guarantees ≥1 keyframe so vision evidence always exists.

**Alternatives considered.**
- *Uniform time sampling.* Simpler but wastes budget on redundant frames and can miss short salient
  events; scene-change sampling covers more distinct content per token.
- *Learned keyframe/shot-boundary model (e.g. TransNet).* Deferred: extra model weight + VRAM/startup
  cost for marginal gain at this clip length; the variance heuristic is good enough for ~short clips.

---

## D4 — Gemma 4 modality ordering & thinking mode

**Decision.** Assemble the synthesis prompt in the strict order **images → transcript → style
prompt**, and use a bounded metacognitive ("thinking") chain only where it pays off (sarcasm, D6).

**Rationale.**
- The **[Research PDF]** reports that Gemma 4 grounds captions best when **visual tokens precede text
  context**, with the task/style instruction last so it conditions generation without being diluted by
  long context.
- Placing the style prompt last keeps the tone instruction salient at generation time.
- Unbounded "thinking" burns the <30 s/request budget; it is reserved for styles that measurably
  benefit and kept length-bounded.

**Alternatives considered.**
- *Transcript-first ordering.* Deferred: measured lower visual fidelity — the model over-indexes on
  speech and under-describes the scene.
- *Always-on chain-of-thought for every style.* Rejected on latency grounds; formal/humor styles do
  not need it.

---

## D5 — Whisper on CTranslate2-HIP (ROCm) build

**Decision.** Run faster-whisper on a **CTranslate2 build compiled with HIP/ROCm** for the host gfx
architecture; the PyPI CT2 wheel is a CPU/CUDA fallback for local dev only.

**Rationale.**
- faster-whisper is ~4–5× faster than reference Whisper and, on **CT2-HIP**, executes on AMD GPUs —
  satisfying the AMD-compute requirement for the audio stage.
- CT2-HIP must be built for the **host gfx target**; a mismatched build silently falls back or fails,
  so the build is pinned and verified (see [docs/05-amd-rocm-optimization](../../docs/05-amd-rocm-optimization.md)).

**Alternatives considered.**
- *Reference `openai-whisper` on PyTorch ROCm.* Deferred: slower and heavier; would eat into the
  per-request budget.
- *whisper.cpp.* Rejected for the primary path: weaker word-timestamp fidelity needed for keyframe
  alignment, though viable as an emergency CPU fallback.

---

## D6 — PMP metacognitive chain for sarcasm

**Decision.** Generate the `sarcastic` style via a **PMP (Perceive → Meta-interpret → Phrase)
metacognitive chain**: perceive the literal events, interpret the affect/expectation, **invert** it,
then phrase a dry/ironic caption — rather than a single "be sarcastic" instruction.

**Rationale.**
- The **[Research PDF]** shows single-shot sarcasm prompts frequently produce either non-sarcastic
  captions or ungrounded jokes. The explicit invert step yields captions whose *literal* reading
  diverges from a straight description **while staying about the same real events** (grounding
  preserved).
- The chain is length-bounded to respect latency; a **single-shot sarcastic prompt is the documented
  cut-order fallback** if the budget is tight.

**Alternatives considered.**
- *Single-shot sarcasm prompt.* Kept as fallback, not primary — inconsistent Style-Match scores.
- *Few-shot exemplars only.* Deferred: exemplars help tone but without the invert step still drift
  ungrounded; can be layered onto PMP later.

---

## D7 — 4-bit quantization of Gemma 4 E4B

**Decision.** Load Gemma 4 E4B-it in **4-bit** (bitsandbytes where available) via HF Transformers,
degrading gracefully to bf16/fp16 if the quant backend is unavailable on ROCm.

**Rationale.**
- 4-bit brings the VLM footprint within the 8 GB-class budget after Whisper is reclaimed.
- bitsandbytes ROCm support is experimental; a **graceful bf16 fallback** avoids a hard failure on
  cards/toolchains where 4-bit quant is unavailable, preserving the exit-0 guarantee.

**Alternatives considered.**
- *fp16-only.* Deferred: exceeds small-card VRAM budget.
- *GPTQ/AWQ pre-quantized weights.* Deferred: added packaging/build complexity for the ≤10 GB image;
  revisit if bitsandbytes-ROCm proves unstable.

---

## D8 — Determinism strategy

**Decision.** Make **evidence extraction deterministic** (fixed ffmpeg params, seeded/thresholded
keyframe selection, greedy/low-temp transcription) and pin VLM sampling to **low/zero temperature with
a fixed seed**; the **fallback caption path is fully deterministic**.

**Rationale.**
- Reproducibility aids debugging, golden-clip regression tests, and defensible scoring. Full VLM
  determinism is not guaranteed across ROCm kernels, so the deterministic guarantees are strongest on
  the evidence and fallback layers (spec CC5).

**Alternatives considered.**
- *High-temperature sampling for tonal variety.* Rejected for the default: harms reproducibility and
  risks grounding drift; tone is achieved via prompting/PMP, not randomness.

---

## D9 — Track 3 "Video-Oracle" stack (stretch)

**Decision.** If pursued, serve **Gemma 4 31B via vLLM-ROCm** and build a **multimodal vector index
(CLIP/USM embeddings)** over keyframes + transcript segments for semantic search + RAG QA, in a
**separate `services/oracle/` image**.

**Rationale.**
- vLLM-ROCm gives high-throughput serving on MI300X for the larger model; a vector index reuses the
  frames/transcripts already produced by Track 2.
- Isolation guarantees Track 3 **cannot regress** the Track 2 runtime or ≤10 GB image budget
  (spec AC7.4).

**Alternatives considered.**
- *Bolt search onto the Track 2 image.* Rejected: would blow the image-size and startup budgets.
- *Deferred entirely by default* — Track 3 is only enabled when US1–US6 are fully green.

---

## D10 — Alternatives surveyed and deferred (summary)

| Alternative | Where it would apply | Why deferred |
| --- | --- | --- |
| **Qwen-VL** (and other VLMs) | Synthesis (S5) | Gemma 4 E4B chosen for the VRAM/quality point at 4-bit on AMD; Qwen-VL kept as a swap candidate if Gemma underperforms on Φ. |
| **Monolithic Gemma audio+video** | Whole pipeline | Higher peak VRAM + weaker transcription; violates sequential-loading budget (D1, D2). |
| **Uniform-interval keyframes** | Vision (S4) | Redundant frames waste token budget vs scene-change sampling (D3). |
| **Learned shot-boundary model** | Vision (S4) | Extra VRAM/startup weight for marginal gain (D3). |
| **fp16-only VLM** | Synthesis (S5) | Exceeds 8 GB-class budget (D7). |
| **Single-shot sarcasm** | Style (S5) | Inconsistent Style-Match; kept only as cut-order fallback (D6). |
| **Transcript-first prompt order** | Synthesis (S5) | Lower visual fidelity (D4). |
| **External ASR API** | Audio (S2) | Network fragility at eval time (D1). |

---

## Open questions / assumptions

- Exact hidden-clip lengths are unknown; keyframe cap and per-request timeout are configurable to
  absorb variance (D3, spec CC1).
- `α`/`β` scoring weights are not published; the pipeline optimizes both Accuracy and Style Match
  rather than trading one off.
- bitsandbytes-ROCm 4-bit stability is toolchain-dependent; the bf16 fallback (D7) covers the risk.

All assumptions are non-blocking for the MVP (US1–US6).
