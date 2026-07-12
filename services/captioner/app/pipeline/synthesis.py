"""Stage 5: synthesis — caption generation with the Fireworks VLM API.

Messages are assembled as a system prompt (style persona + output-tag rules)
and a user prompt in a fixed order: **images -> transcript text**. The model's
reasoning is kept outside ``<captionStyle>`` tags and only the tagged caption is
returned. Styles for a single clip are generated in a loop over shared evidence.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import requests

from app.core.config import Settings
from app.core.errors import SynthesisError
from app.core.logging import get_logger
from app.core.schema import Style
from app.prompts.styles import get_style_prompt

if TYPE_CHECKING:
    from app.pipeline.audio import Transcript
    from app.pipeline.vision import Keyframe

logger = get_logger(__name__)

_CAPTION_TAG_RE = re.compile(r"<captionStyle>(.*?)</captionStyle>", re.DOTALL)
# A genuine tag-less caption is a sentence or two. Anything longer without the
# required tag is a reasoning VLM leaking its chain-of-thought (usually because it
# was truncated before closing the tag), not a caption.
_MAX_UNTAGGED_CAPTION_CHARS = 300


def _is_meaningful_caption(text: str) -> bool:
    """Whether ``text`` is a substantive caption rather than a degenerate one.

    A reasoning VLM occasionally emits punctuation-only content inside the tags
    (e.g. a bare ``...`` for a deadpan persona) or gets truncated to nothing.
    Such output must not reach the results file — the caller falls back to a
    grounded deterministic caption instead. Substantive means it has at least a
    few characters and contains a real alphanumeric word, not just punctuation.
    """
    stripped = text.strip()
    return len(stripped) >= 3 and bool(re.search(r"[A-Za-z0-9]", stripped))


class CaptionSynthesizer:
    """Communicates with Fireworks VLM API to generate captions across styles."""

    def __init__(self, cfg: Settings) -> None:
        """Store config; defer client setup to :meth:`load`.

        Args:
            cfg: Application settings.
        """
        self._cfg = cfg
        self.model: Any | None = None

    def load(self) -> None:
        """Initialize the client (idempotent)."""
        if self.model is None:
            self.model = True

    def unload(self) -> None:
        """Drop references to the client."""
        self.model = None

    def _build_messages(
        self,
        keyframes: list[Keyframe],
        transcript_text: str,
        style: Style,
    ) -> list[dict[str, Any]]:
        """Assemble messages: system prompt (persona + rules) and user prompt (images + transcript).

        Args:
            keyframes: Aligned keyframes.
            transcript_text: The clip transcript.
            style: Requested caption style.

        Returns:
            A chat-completions-ready message list.
        """
        from app.pipeline.vision import encode_image_to_base64

        user_content: list[dict[str, Any]] = []

        # 1. Images first
        for kf in keyframes:
            try:
                b64 = encode_image_to_base64(kf.image)
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    }
                )
            except Exception as exc:
                logger.warning("Failed to encode keyframe to base64: %s", exc)

        # 2. Transcript text
        transcript_block = transcript_text.strip() or "(no speech detected)"
        user_content.append({"type": "text", "text": f"Transcript:\n{transcript_block}"})

        # 3. System prompt with formatting instructions
        system_instructions: list[str] = []
        system_instructions.append(get_style_prompt(style))

        # Append XML tag requirement to enforce reasoning/content separation on reasoning VLMs
        tag_instruction = (
            " IMPORTANT: Absolutely do not output the caption directly. You must format "
            "your final caption inside <captionStyle>...</captionStyle> tags. Put all your "
            "thinking process and notes outside these tags, and put ONLY the final caption "
            "inside the tags."
        )
        system_instructions.append(tag_instruction)

        system_prompt = "\n".join(system_instructions)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def generate_caption(
        self,
        keyframes: list[Keyframe],
        transcript: Transcript,
        style: Style,
    ) -> str:
        """Generate a single caption for one style via Fireworks VLM API.

        Args:
            keyframes: Aligned keyframes for the clip.
            transcript: The audio transcript.
            style: Requested caption style.

        Returns:
            The generated caption text (stripped).

        Raises:
            RuntimeError: If called before :meth:`load`.
            SynthesisError: If the API call fails.
        """
        if self.model is None:
            raise RuntimeError("CaptionSynthesizer.generate_caption() called before load().")

        if not self._cfg.fireworks_api_key:
            raise SynthesisError("Fireworks API key is not configured. Cannot synthesize.")

        messages = self._build_messages(keyframes, transcript.text, style)

        # The reasoning VLM fails intermittently: a repeated degenerate answer
        # ("...") or a truncation that leaks raw chain-of-thought. Both usually
        # clear on a retry, so escalate rather than immediately falling back —
        # more tokens gives reasoning room, and a little temperature after the
        # first try breaks the model out of a repeated bad answer.
        attempts = max(1, self._cfg.synthesis_max_attempts)
        last_error: SynthesisError | None = None
        for attempt in range(attempts):
            temperature = 0.0 if attempt == 0 else min(0.2 + 0.2 * attempt, 0.6)
            max_tokens = self._cfg.max_new_tokens * (attempt + 1)
            try:
                caption = self._request_caption(messages, style, temperature, max_tokens)
                if attempt > 0:
                    logger.info(
                        "Synthesis for style=%s recovered on attempt %d/%d.",
                        style.value,
                        attempt + 1,
                        attempts,
                    )
                return caption
            except SynthesisError as exc:
                last_error = exc
                logger.warning(
                    "Synthesis attempt %d/%d for style=%s failed: %s",
                    attempt + 1,
                    attempts,
                    style.value,
                    exc,
                )

        assert last_error is not None  # loop ran at least once
        raise last_error

    def _request_caption(
        self,
        messages: list[dict[str, Any]],
        style: Style,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """One Fireworks call; returns a validated caption or raises SynthesisError."""
        url = f"{self._cfg.fireworks_api_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._cfg.fireworks_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._cfg.fireworks_vlm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=self._cfg.fireworks_timeout_s
            )
        except Exception as exc:
            raise SynthesisError(f"HTTP request to Fireworks Vision API failed: {exc}") from exc

        if response.status_code != 200:
            raise SynthesisError(
                f"Fireworks Vision API failed with status {response.status_code}: {response.text}"
            )

        try:
            res_json = response.json()
            choice = res_json["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
        except Exception as exc:
            raise SynthesisError(f"Failed to parse Fireworks Vision API response: {exc}") from exc

        # Prefer the tagged caption; a reasoning VLM keeps its thinking outside the
        # tags. A response with no closing tag has either leaked raw chain-of-thought
        # or been truncated before the tag closed (finish_reason == "length") — dump
        # neither into results.json. A short tag-less response is still accepted
        # (some models answer directly).
        match = _CAPTION_TAG_RE.search(content)
        if match:
            caption = match.group(1).strip()
        else:
            caption = content.strip()
            if finish_reason == "length" or len(caption) > _MAX_UNTAGGED_CAPTION_CHARS:
                raise SynthesisError(
                    f"VLM response for style={style.value} has no <captionStyle> tag and "
                    f"appears truncated or leaked reasoning "
                    f"(finish_reason={finish_reason!r}, chars={len(caption)})."
                )

        if not _is_meaningful_caption(caption):
            raise SynthesisError(
                f"VLM returned a non-substantive caption for style={style.value} "
                f"(finish_reason={finish_reason!r}, tagged={bool(match)}, "
                f"caption={caption[:60]!r})."
            )
        return caption

    def generate_for_styles(
        self,
        keyframes: list[Keyframe],
        transcript: Transcript,
        styles: list[Style],
    ) -> dict[Style, str]:
        """Generate captions for a batch of styles over one loaded model.

        The style calls are remote (Fireworks) and independent, so they run
        CONCURRENTLY — measured sequentially they dominated the per-clip wall
        clock (~136 s of ~151 s on the public validation clips), and that
        latency is identical on the judge's AMD box because the API is remote.

        Args:
            keyframes: Aligned keyframes for the clip.
            transcript: The audio transcript.
            styles: Requested styles.

        Returns:
            Mapping of style -> caption text. A per-style failure yields a fallback
            caption for that style rather than aborting the whole batch.
        """
        from concurrent.futures import ThreadPoolExecutor

        from app.core.errors import fallback_caption

        def _one(style: Style) -> str:
            try:
                return self.generate_caption(keyframes, transcript, style)
            except Exception as exc:  # noqa: BLE001 - never let one style sink the task
                logger.exception("Caption generation failed for style=%s: %s", style, exc)
                tx_text = transcript.text if transcript else None
                kf_count = len(keyframes) if keyframes else 0
                return fallback_caption(tx_text, kf_count)

        if len(styles) <= 1:
            return {style: _one(style) for style in styles}
        with ThreadPoolExecutor(max_workers=min(4, len(styles))) as pool:
            texts = list(pool.map(_one, styles))
        return dict(zip(styles, texts, strict=False))
