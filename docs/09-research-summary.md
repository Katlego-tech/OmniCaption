# 09 — Research Summary

Condensed from **`Hackathon Research for AI Video Captioning.pdf`** (repo root). This captures the
ideas that shaped OmniCaption's architecture; the pipeline itself is in
[03-captioning-pipeline](03-captioning-pipeline.md).

## Dual-model hybrid pipeline

The central design: use **two specialist models sequentially** rather than one monolith — a fast
speech-to-text model (faster-whisper) for the audio track, and a vision-language model (Gemma 4 E4B)
for the visual + fused reasoning. They are loaded one at a time to stay within VRAM (Stage 3 memory
reclamation). This hybrid beats a single VLM trying to do everything, because the STT model produces
precise word-level timing the VLM can anchor to.

## MTSS — multi-stream idea

**Multi-Track/Stream Synthesis:** treat a video as parallel streams (visual keyframes, transcript
text, and — as a stretch — audio-event tags) and fuse them at synthesis time rather than forcing one
stream to carry all meaning. OmniCaption realizes a practical subset: keyframes + transcript fused in
the Gemma 4 prompt.

## Neural-ODE temporal localization

Research direction for **continuous-time** localization of events: rather than discretizing a video
into fixed windows, model event boundaries as a continuous trajectory (Neural-ODE style) to pinpoint
*when* something happens. OmniCaption approximates this pragmatically with OpenCV scene-change
detection plus transcript-timestamp alignment; Neural-ODE localization is a future direction, not in
the Track 2 build.

## Multimodal fusion

Grounding captions requires fusing modalities, not concatenating them naively. The key practical
finding: **modality order matters** for Gemma 4 — visual tokens must precede text, audio follows
text. Getting this order wrong degrades grounding.

## Gemma 4 architecture highlights

- Multimodal (vision + text) with a strict input-ordering contract: **images → text → audio**.
- Runs at a workable footprint when **4-bit quantized**, which is what lets it fit 8 GB AMD cards.
- The E4B variant is the Track 2 workhorse; the 31B variant is reserved for Track 3 serving via vLLM.

## Whisper-HIP

**faster-whisper on CTranslate2-HIP** brings Whisper-class STT to AMD GPUs. Building CTranslate2 with
HIP for the host `gfx` arch (see [05-amd-rocm-optimization](05-amd-rocm-optimization.md)) is what
makes the audio stage AMD-accelerated rather than CPU-bound.

## PMP for sarcasm

**Pragmatic Metacognitive Prompting** produces genuinely dry sarcasm instead of cheesy puns by
forcing a reasoning chain: analyze literal facts → identify contradictions → determine pragmatic
meaning → write the dry caption. This is the technique behind the `sarcastic` style — see
[13-prompt-engineering-playbook](13-prompt-engineering-playbook.md).
