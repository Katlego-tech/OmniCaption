"""Stage 5: synthesis — caption generation with the Fireworks VLM API.

The chat prompt is assembled in a fixed order: **images -> transcript text ->
style system prompt**. The sarcastic style routes through Pragmatic
Metacognitive Prompting (PMP). Styles for a single clip are generated in a loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests

from app.core.config import Settings
from app.core.errors import SynthesisError
from app.core.logging import get_logger
from app.core.schema import Style
from app.prompts.pmp import PMP_INSTRUCTION
from app.prompts.styles import get_style_prompt

if TYPE_CHECKING:
    from app.pipeline.audio import Transcript
    from app.pipeline.vision import Keyframe

logger = get_logger(__name__)


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
        """Assemble chat messages in order: images -> transcript -> style prompt.

        Args:
            keyframes: Aligned keyframes.
            transcript_text: The clip transcript.
            style: Requested caption style.

        Returns:
            A chat-completions-ready message list.
        """
        from app.pipeline.vision import encode_image_to_base64

        content: list[dict[str, Any]] = []

        # 1. Images first
        for kf in keyframes:
            try:
                b64 = encode_image_to_base64(kf.image)
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    }
                )
            except Exception as exc:
                logger.warning("Failed to encode keyframe to base64: %s", exc)

        # 2. Transcript text
        transcript_block = transcript_text.strip() or "(no speech detected)"
        content.append({"type": "text", "text": f"Transcript:\n{transcript_block}"})

        # 3. Style prompt (preceded by PMP instruction for sarcasm)
        if style is Style.SARCASTIC:
            content.append({"type": "text", "text": PMP_INSTRUCTION})

        content.append({"type": "text", "text": get_style_prompt(style)})

        return [{"role": "user", "content": content}]

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

        url = f"{self._cfg.fireworks_api_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._cfg.fireworks_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._cfg.fireworks_vlm_model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": self._cfg.max_new_tokens,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15.0)
        except Exception as exc:
            raise SynthesisError(f"HTTP request to Fireworks Vision API failed: {exc}") from exc

        if response.status_code != 200:
            raise SynthesisError(
                f"Fireworks Vision API failed with status {response.status_code}: {response.text}"
            )

        try:
            res_json = response.json()
            caption = res_json["choices"][0]["message"]["content"]
            return caption.strip()
        except Exception as exc:
            raise SynthesisError(
                f"Failed to parse Fireworks Vision API response: {exc}"
            ) from exc

    def generate_for_styles(
        self,
        keyframes: list[Keyframe],
        transcript: Transcript,
        styles: list[Style],
    ) -> dict[Style, str]:
        """Generate captions for a batch of styles over one loaded model.

        Args:
            keyframes: Aligned keyframes for the clip.
            transcript: The audio transcript.
            styles: Requested styles.

        Returns:
            Mapping of style -> caption text. A per-style failure yields a fallback
            caption for that style rather than aborting the whole batch.
        """
        from app.core.errors import fallback_caption

        captions: dict[Style, str] = {}
        for style in styles:
            try:
                captions[style] = self.generate_caption(keyframes, transcript, style)
            except Exception as exc:  # noqa: BLE001 - never let one style sink the task
                logger.exception("Caption generation failed for style=%s: %s", style, exc)
                tx_text = transcript.text if transcript else None
                kf_count = len(keyframes) if keyframes else 0
                captions[style] = fallback_caption(tx_text, kf_count)
        return captions
