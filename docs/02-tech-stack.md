# 02 — Tech Stack

The stack is **locked**. Do not swap components without a team decision recorded in `STATUS.md` and an
update to the non-negotiables in [PLAN.md](../PLAN.md) (see [07-planning-workflow](07-planning-workflow.md)).

| Component | Choice | Why |
| --- | --- | --- |
| Language | **Python 3.11** | Mature ROCm/Transformers ecosystem; matches faster-whisper and OpenCV bindings |
| Container | **Docker (linux/amd64)** | Required by the harness; reproducible ≤10 GB image |
| Speech-to-text | **faster-whisper** on **CTranslate2-HIP** (ROCm) | 4–5x faster than reference Whisper; CT2-HIP runs the inference on AMD GPUs |
| Audio extraction | **ffmpeg** | Reliable decode of arbitrary `video_url` inputs into mono 16 kHz WAV for Whisper |
| Keyframe selection | **OpenCV** | Pixel-variance scene-change detection is cheap, CPU-side, no extra model weight |
| Vision-language model | **Gemma 4 E4B-it (4-bit quantized)** via **Hugging Face Transformers** | Strong multimodal captioning at a VRAM footprint that fits 8 GB cards when 4-bit |
| GPU runtime | **PyTorch (ROCm)** | AMD-native tensor backend for the VLM; pairs with CT2-HIP for STT |
| Config | **pydantic-settings** | Typed, env-driven config; clean separation of tunables from code |
| Testing | **pytest** | Contract, golden-clip, and latency tests; VLM/Whisper mocked for cheap unit runs |
| Linting | **Ruff** (line length 100) | Fast, single-tool lint + format; enforced in the CI gate |

## Stretch (Track 3 only)

| Component | Choice | Why |
| --- | --- | --- |
| Serving | **vLLM-ROCm** | High-throughput serving of **Gemma 4 31B** on MI300X |
| Semantic index | Multimodal vector index (**CLIP/USM** embeddings) | Enables semantic video search + RAG QA for "Video-Oracle" |

## Notes

- faster-whisper and Gemma 4 E4B are loaded **sequentially**, never together — see
  [01-architecture](01-architecture.md).
- The Gemma 4 prompt requires a strict modality order (images → text → audio) — see
  [03-captioning-pipeline](03-captioning-pipeline.md).
- CTranslate2-HIP must be built for the host gfx architecture — see
  [05-amd-rocm-optimization](05-amd-rocm-optimization.md).
