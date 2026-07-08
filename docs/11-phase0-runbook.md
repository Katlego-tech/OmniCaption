# 11 — Phase 0 Runbook

Start here. This gets you from zero to a container that runs the three baseline clips and produces a
schema-valid `/output/results.json`. Phases are defined in [00-project-plan](00-project-plan.md).

## 1. Get AMD compute access

- Provision **AMD Developer Cloud** access, **or** confirm a **local ROCm** GPU from the target list
  ([05-amd-rocm-optimization](05-amd-rocm-optimization.md)).
- Verify ROCm sees the GPU (e.g. `rocminfo` / `rocm-smi`) and note the **gfx arch** — you need it to
  build CTranslate2-HIP.

## 2. Clone and wire up

```bash
git clone https://github.com/Katlego-tech/OmniCaption.git
cd OmniCaption
git config core.hooksPath .githooks     # enable the pre-push test gate
```

Then read `AGENTS.md` and `STATUS.md` before touching anything — see
[10-cross-ai-protocol](10-cross-ai-protocol.md).

## 3. Build the container

- Build the **linux/amd64** image, exporting `PYTORCH_ROCM_ARCH=<gfx>` before compiling
  CTranslate2-HIP so Whisper is AMD-accelerated ([05-amd-rocm-optimization](05-amd-rocm-optimization.md)).
- Confirm the image is **≤10 GB** and starts within **60 s** ([06-judging-criteria](06-judging-criteria.md)).
- Build/tag/push details are in [deployment](deployment.md).

## 4. Run against the 3 baseline clips

Prepare an `/input/tasks.json` referencing the baselines and run:

```bash
docker run --rm \
  -v ./input:/input \
  -v ./output:/output \
  <image>            # add the ROCm device flags for your host
```

Baseline clips (also the golden-clip regression set — [04-testing-strategy](04-testing-strategy.md)):

- **v1 boulevard** (urban/motion)
- **v2 kitten** (animals)
- **v3 office worker** (human actions)

## 5. Verify the output schema

- `/output/results.json` exists and is **schema-valid**: every task present, every requested style
  present, correct types.
- The process **exited 0**.
- Logs show **AMD/ROCm compute** was used (not CPU fallback) — this is a disqualifier if absent.

## Learning checklist

Before you start building your lane, make sure you understand:

- [ ] The container I/O contract (`/input/tasks.json` → `/output/results.json`, exit 0) — [01-architecture](01-architecture.md).
- [ ] The 6 pipeline stages and why models load sequentially — [03-captioning-pipeline](03-captioning-pipeline.md).
- [ ] The Gemma 4 modality-ordering rule (images → text → audio).
- [ ] The four styles and PMP for sarcasm — [13-prompt-engineering-playbook](13-prompt-engineering-playbook.md).
- [ ] The gfx target table and `HSA_OVERRIDE_GFX_VERSION` — [05-amd-rocm-optimization](05-amd-rocm-optimization.md).
- [ ] The runtime constraints and submission checklist — [06-judging-criteria](06-judging-criteria.md).
- [ ] Branch-only workflow + hooks + commit format — [08-git-workflow](08-git-workflow.md).
- [ ] Single-writer-per-task coordination — [10-cross-ai-protocol](10-cross-ai-protocol.md).
