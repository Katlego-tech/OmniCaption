# 14 — Optimization Suggestions

**These are proposals, not committed work.** They are ideas to raise Φ or robustness once the Track 2
baseline is green. Anything here that competes with the baseline is subject to the cut order in
[00-project-plan](00-project-plan.md). Each item notes its likely payoff and cost.

## Quality / accuracy

- **Adaptive keyframe budgeting by clip length (PROPOSAL).** Instead of a fixed keyframe count, scale
  the budget with clip duration and scene density from the OpenCV variance signal. More frames for
  busy clips, fewer for static ones. Payoff: better visual fidelity without blowing the token budget.
- **Caption self-critique / LLM-judge loop before output (PROPOSAL).** After synthesis, have the VLM
  (or a small judge) score each caption on accuracy + style match and regenerate the weakest. Payoff:
  higher Φ. Cost: extra latency — must stay inside the <30 s/request and ≤10 min gates
  ([06-judging-criteria](06-judging-criteria.md)); first to cut if it threatens the budget.
- **Style-conditioned few-shot exemplars (PROPOSAL).** Prepend 1–2 curated example captions per style
  to sharpen tone (especially `sarcastic` and `humorous_tech`). Payoff: Style Match. Cost: prompt
  length / tokens.
- **Audio-event tagging, not just transcription (PROPOSAL).** Tag non-speech audio (applause, engine,
  animal sounds, weather) as an extra stream feeding synthesis — the MTSS idea from
  [09-research-summary](09-research-summary.md). Payoff: richer grounding on low-dialogue clips.

## Performance / robustness

- **Cache model weights in an image layer to hit the 60 s startup gate (PROPOSAL).** Bake Gemma 4 E4B
  and the Whisper model into the image so cold start does no download. Payoff: reliably meets the
  60 s startup gate. Cost: image size — must stay ≤10 GB.
- **Parallelize the 4 style generations in one batched VLM call (PROPOSAL).** The visual + transcript
  context is identical across styles; only the system prompt differs. Batch all four in a single
  forward pass. Payoff: large latency win toward the ≤10 min budget.
- **Deterministic fallback caption if the VLM OOMs (PROPOSAL, high priority).** On OOM or generation
  failure, emit a template caption built from the transcript + detected scene so the style key is
  never missing (a missing style scores 0). Low cost, high safety — closest to a must-have.

## Track 3 — Video-Oracle (STRETCH)

- **Semantic-search + RAG extension (PROPOSAL).** Build a multimodal vector index (CLIP/USM
  embeddings) over keyframes + transcript, serve **Gemma 4 31B** on **vLLM-ROCm** (MI300X tunables in
  [05-amd-rocm-optimization](05-amd-rocm-optimization.md)), and answer natural-language questions
  about a video via retrieval-augmented generation. This is the whole Track 3 deliverable and the
  first thing dropped under time pressure.
