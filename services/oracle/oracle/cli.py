"""Video-Oracle CLI (T094): build the index, search it, ask questions.

Requires FIREWORKS_API_KEY in the environment for live embedding/QA calls.

Examples::

    python -m oracle.cli build --results /output/results.json --out /data/oracle/index.json
    python -m oracle.cli search --index /data/oracle/index.json "person on a bike"
    python -m oracle.cli ask --index /data/oracle/index.json "what happens in v1?"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from oracle.corpus import moments_from_keyframes, moments_from_results, moments_from_transcripts
from oracle.embeddings import FireworksChat, FireworksEmbeddings
from oracle.index import MomentIndex
from oracle.qa import answer


def _embedder() -> FireworksEmbeddings:
    api_key = os.environ.get("FIREWORKS_API_KEY", "")
    if not api_key:
        sys.exit("FIREWORKS_API_KEY is required for oracle commands.")
    return FireworksEmbeddings(api_key)


def _clip_encoder():
    """The optional CLIP encoder, or None (with a note) when open_clip is absent."""
    try:
        from oracle.clip_embed import OpenClipEncoder

        return OpenClipEncoder()
    except ImportError:
        print("note: open_clip not installed - visual (keyframe) moments are skipped.")
        return None


def _cmd_build(args: argparse.Namespace) -> None:
    moments = moments_from_results(args.results)
    if args.transcripts and Path(args.transcripts).is_file():
        moments += moments_from_transcripts(args.transcripts)
    clip = None
    if args.keyframes and Path(args.keyframes).is_dir():
        moments += moments_from_keyframes(args.keyframes)
        clip = _clip_encoder()
    index = MomentIndex.build(moments, _embedder(), clip_encoder=clip)
    print(f"Indexed {len(index)} moments -> {args.out}")
    index.save(args.out)


def _cmd_search(args: argparse.Namespace) -> None:
    index = MomentIndex.load(args.index)
    clip = _clip_encoder() if any(m.space == "clip" for m in index.moments) else None
    hits = index.search(args.query, _embedder(), top_k=args.top_k, clip_encoder=clip)
    print(json.dumps([hit.model_dump() for hit in hits], indent=2))


def _cmd_ask(args: argparse.Namespace) -> None:
    api_key = os.environ.get("FIREWORKS_API_KEY", "")
    index = MomentIndex.load(args.index)
    clip = _clip_encoder() if any(m.space == "clip" for m in index.moments) else None
    result = answer(
        args.question,
        index,
        _embedder(),
        FireworksChat(api_key),
        top_k=args.top_k,
        clip_encoder=clip,
    )
    print(result.answer)
    for hit in result.citations:
        print(f"  - [{hit.moment.task_id}] ({hit.score:.3f}) {hit.moment.text[:80]}")


def main(argv: list[str] | None = None) -> None:
    """Entry point for ``python -m oracle.cli``."""
    parser = argparse.ArgumentParser(prog="oracle", description=__doc__)
    sub = parser.add_subparsers(required=True)

    build = sub.add_parser("build", help="Build the index from captioner artifacts.")
    build.add_argument("--results", required=True, help="Path to results.json.")
    build.add_argument("--transcripts", default=None, help="Optional transcripts sidecar.")
    build.add_argument(
        "--keyframes",
        default=None,
        help="Optional keyframe sidecar dir (visual moments; needs open_clip installed).",
    )
    build.add_argument("--out", required=True, help="Where to write index.json.")
    build.set_defaults(func=_cmd_build)

    search = sub.add_parser("search", help="Semantic moment search.")
    search.add_argument("--index", required=True)
    search.add_argument("--top-k", type=int, default=5)
    search.add_argument("query")
    search.set_defaults(func=_cmd_search)

    ask = sub.add_parser("ask", help="Grounded QA over indexed moments.")
    ask.add_argument("--index", required=True)
    ask.add_argument("--top-k", type=int, default=5)
    ask.add_argument("question")
    ask.set_defaults(func=_cmd_ask)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
