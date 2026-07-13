"""Generate the golden style-caption dataset from a collected clip corpus.

For every clip in the manifest, runs the REAL pipeline evidence path (ffmpeg
audio extraction -> faster-whisper transcript -> OpenCV keyframes) by importing
the captioner's own modules, then asks the teacher VLM (Fireworks, Kimi-K2P6 by
default) for one caption per style with an uncapped, richly-instructed prompt.
Captions stay grounded by construction: the teacher sees only this clip's real
keyframes + transcript (PLAN.md non-negotiable — no invented content).

Output: JSONL, one record per (clip, style):
    {"clip_id", "style", "caption", "transcript", "n_keyframes", "theme"}

Usage (run from the repo root; captioner deps + ffmpeg required):
    FIREWORKS_API_KEY=... python tools/dataset/generate_captions.py \
        --clips data/dataset/clips --out data/dataset/golden.jsonl \
        [--teacher accounts/fireworks/models/kimi-k2p6] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Reuse the captioner's own stages so dataset evidence == production evidence.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "captioner"))

from app.core.config import Settings  # noqa: E402
from app.core.schema import Style  # noqa: E402
from app.pipeline import ingestion  # noqa: E402
from app.pipeline.audio import WhisperTranscriber  # noqa: E402
from app.pipeline.synthesis import CaptionSynthesizer  # noqa: E402
from app.pipeline.vision import align_to_transcript, extract_keyframes  # noqa: E402
from app.prompts.styles import get_style_prompt  # noqa: E402

# The teacher gets the production persona PLUS distillation-only guidance: it
# can spend unlimited reasoning, but the caption itself must stay 1-2 sentences
# and name concrete visible subjects. These strings feed training targets, so
# keep them stable once a dataset generation has started.
TEACHER_EXTRA = (
    " You are generating GOLD-STANDARD training data, so take your time: study "
    "every frame and the transcript, identify the single most distinctive "
    "visible detail, and build the caption around it. The caption must stand "
    "alone (1-2 sentences), never mention frames, images, videos, or "
    "transcripts, and never include meta-commentary."
)


def build_teacher_settings(teacher_model: str) -> Settings:
    """Settings tuned for offline dataset generation (patient, high-token)."""
    return Settings(
        max_new_tokens=16384,
        synthesis_max_attempts=3,
        fireworks_vlm_model=teacher_model,
        fireworks_timeout_s=180.0,
        whisper_model_size="base",
        whisper_compute_type="int8",
    )


def generate(
    clips_dir: Path, out_path: Path, teacher_model: str, limit: int | None
) -> int:
    manifest = json.loads((clips_dir / "manifest.json").read_text(encoding="utf-8"))
    if limit:
        manifest = manifest[:limit]

    cfg = build_teacher_settings(teacher_model)
    if not cfg.fireworks_api_key:
        print("ERROR: set FIREWORKS_API_KEY")
        return 1

    synth = CaptionSynthesizer(cfg)
    synth.load()
    transcriber = WhisperTranscriber(cfg)
    transcriber.load()

    # Teacher persona = production persona + distillation guidance.
    original_get = get_style_prompt
    import app.pipeline.synthesis as synthesis_mod

    synthesis_mod.get_style_prompt = lambda style: original_get(style) + TEACHER_EXTRA

    done_ids: set[tuple[str, str]] = set()
    if out_path.exists():  # resumable: skip records already generated
        for line in out_path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            done_ids.add((rec["clip_id"], rec["style"]))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out_path.open("a", encoding="utf-8") as out:
        for i, entry in enumerate(manifest):
            clip_id = entry["clip_id"]
            if all((clip_id, s.value) in done_ids for s in Style):
                continue
            video = clips_dir / entry["file"]
            try:
                wav = ingestion.extract_audio(video, clips_dir / "wav")
                transcript = transcriber.transcribe(wav)
                keyframes = extract_keyframes(
                    video,
                    threshold=cfg.keyframe_threshold,
                    max_keyframes=cfg.max_keyframes,
                )
                align_to_transcript(keyframes, transcript)
            except Exception as exc:  # noqa: BLE001 - skip broken clips, keep going
                print(f"[{clip_id}] evidence failed, skipping: {exc}")
                continue

            for style in Style:
                if (clip_id, style.value) in done_ids:
                    continue
                try:
                    caption = synth.generate_caption(keyframes, transcript, style)
                except Exception as exc:  # noqa: BLE001 - one style failing is fine
                    print(f"[{clip_id}] {style.value} failed: {exc}")
                    continue
                out.write(
                    json.dumps(
                        {
                            "clip_id": clip_id,
                            "style": style.value,
                            "caption": caption,
                            "transcript": transcript.text,
                            "n_keyframes": len(keyframes),
                            "theme": entry.get("theme", ""),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                out.flush()
                written += 1
            print(f"[{i + 1}/{len(manifest)}] {clip_id} done ({written} records total)")
            time.sleep(0.5)

    print(f"\nWrote {written} new records -> {out_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clips", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--teacher", default="accounts/fireworks/models/kimi-k2p6")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    return generate(args.clips, args.out, args.teacher, args.limit)


if __name__ == "__main__":
    sys.exit(main())
