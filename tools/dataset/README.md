# Style-caption dataset tooling (finetune track)

Builds the "golden" dataset for the style-adapter finetune proposed in
[docs/report-scoreboard-pivot.md](../../docs/report-scoreboard-pivot.md) —
with two deliberate deviations from that report:

1. **Teacher = Fireworks Kimi-K2P6, not GPT-4o/Gemini.** Keeps the AMD /
   Fireworks compute story intact, and the teacher sees only each clip's real
   keyframes + transcript, so captions stay grounded (PLAN.md non-negotiable:
   no invented content).
2. **Corpus = Pexels stock clips.** The judge's validation clips are Pexels
   exports (URL stems like `1860079-uhd_2560_1440_25fps`), so training data
   mirrors the hidden set's distribution: short, subject-focused stock clips
   across the same themes (16 themes, judge's 8 + close neighbours).

These tools live OUTSIDE `services/captioner/` on purpose: nothing here ships
in the submission image (the <10 GB gate is untouched).

## Run it (best on the AMD notebook: Linux, fast network, deps installed)

```bash
cd OmniCaption
pip install -r services/captioner/requirements.txt   # if not already done

# 1. Collect ~250 clips (free API key: pexels.com/api — instant signup)
PEXELS_API_KEY=... python tools/dataset/collect_clips.py \
    --out data/dataset/clips --per-theme 16

# 2. Generate teacher captions (resumable — rerun to continue after a stop)
FIREWORKS_API_KEY=... python tools/dataset/generate_captions.py \
    --clips data/dataset/clips --out data/dataset/golden.jsonl
```

~250 clips × 4 styles ≈ 1,000 records. Step 2 is the slow part (one teacher
call per record + Whisper per clip): expect several hours; it flushes after
every record and skips already-generated ones on rerun, so it survives the
notebook's session quota.

## What the dataset is FOR (decision gate — read before training)

The finetune is the **last** lever, not the next one. Before spending GPU
hours: confirm the latest published image (task concurrency + calibrated
prompts) has actually been scored. If style quality is still the weak axis
after that, the ladder is: prompt iteration → stronger Fireworks VLM →
LoRA finetune on this dataset.

Also note the constraint the report glossed over: serving a local 7B VLM
inside the container adds ~4–5 GB to a 9.67 GB image with a strict <10 GB
gate. A finetune only ships if something else of comparable size is cut —
budget that BEFORE training, not after.
