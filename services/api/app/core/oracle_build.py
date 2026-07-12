"""Build the Track 3 oracle index from a completed captioner run.

Reused by the API's post-run hook so search/QA work without a manual
`python -m oracle.cli build`. Text moments (captions + transcript) only —
no CLIP/keyframe encoding — which is all the dashboard search/QA need.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings

logger = logging.getLogger(__name__)


def build_index_from_run(settings: Settings, api_key: str, *, embedder: Any | None = None) -> int:
    """Embed the run's captions (+ transcript) and write the oracle index.

    Args:
        settings: API settings (paths + oracle_index_path).
        api_key: Fireworks key used to embed the moments.
        embedder: Optional pre-built embedder (tests inject a fake); a
            Fireworks embedder is created from ``api_key`` when omitted.

    Returns:
        The number of indexed moments.
    """
    # Imported lazily so the API doesn't hard-depend on the oracle package at import time.
    from oracle.corpus import moments_from_results, moments_from_transcripts
    from oracle.index import MomentIndex

    moments = moments_from_results(settings.results_path)

    transcripts_path = settings.output_dir / "transcripts.json"
    if transcripts_path.is_file():
        moments += moments_from_transcripts(transcripts_path)

    if embedder is None:
        from oracle.embeddings import FireworksEmbeddings

        embedder = FireworksEmbeddings(api_key)

    index = MomentIndex.build(moments, embedder)
    settings.oracle_index_path.parent.mkdir(parents=True, exist_ok=True)
    index.save(settings.oracle_index_path)
    logger.info("Auto-built oracle index: %d moments -> %s", len(index), settings.oracle_index_path)
    return len(index)
