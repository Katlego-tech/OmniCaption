"""Stage 5: synthesis — caption generation with the Gemma 4 E4B-it VLM.

The chat prompt is assembled in a fixed order: **images -> transcript text ->
style system prompt**. The sarcastic style routes through Pragmatic
Metacognitive Prompting (PMP). Styles for a single clip are generated in a loop
over one loaded model instance (the model is loaded once per run, not per style).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.schema import Style
from app.models.loader import load_gemma_vlm
from app.prompts.pmp import PMP_INSTRUCTION
from app.prompts.styles import get_style_prompt

if TYPE_CHECKING:  # pragma: no cover - typing only
    from PIL import Image

    from app.pipeline.audio import Transcript
    from app.pipeline.vision import Keyframe

logger = get_logger(__name__)


class CaptionSynthesizer:
    """Loads the Gemma VLM and generates captions across styles."""

    def __init__(self, cfg: Settings) -> None:
        """Store config; defer model loading to :meth:`load`.

        Args:
            cfg: Application settings.
        """
        self._cfg = cfg
        self.model: Any | None = None
        self.processor: Any | None = None

    def load(self) -> None:
        """Load the Gemma VLM + processor (idempotent)."""
        if self.model is None:
            self.model, self.processor = load_gemma_vlm(self._cfg)

    def unload(self) -> None:
        """Drop model/processor references for VRAM reclamation."""
        self.model = None
        self.processor = None

    @staticmethod
    def _keyframes_to_images(keyframes: list[Keyframe]) -> list[Image.Image]:
        """Convert BGR OpenCV keyframes to RGB PIL images for the processor.

        Args:
            keyframes: Extracted keyframes (OpenCV BGR ndarrays).

        Returns:
            PIL RGB images in keyframe order.
        """
        import cv2
        from PIL import Image

        images: list[Image.Image] = []
        for kf in keyframes:
            rgb = cv2.cvtColor(kf.image, cv2.COLOR_BGR2RGB)
            images.append(Image.fromarray(rgb))
        return images

    def _build_messages(
        self,
        images: list[Image.Image],
        transcript_text: str,
        style: Style,
    ) -> list[dict[str, Any]]:
        """Assemble chat messages in order: images -> transcript -> style prompt.

        Args:
            images: Keyframe images.
            transcript_text: The clip transcript.
            style: Requested caption style.

        Returns:
            A chat-template-ready message list.
        """
        content: list[dict[str, Any]] = [{"type": "image", "image": img} for img in images]

        transcript_block = transcript_text.strip() or "(no speech detected)"
        content.append({"type": "text", "text": f"Transcript:\n{transcript_block}"})

        # Sarcasm uses the PMP reasoning scaffold before the persona instruction.
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
        """Generate a single caption for one style.

        Args:
            keyframes: Aligned keyframes for the clip.
            transcript: The audio transcript.
            style: Requested caption style.

        Returns:
            The generated caption text (stripped).

        Raises:
            RuntimeError: If called before :meth:`load`.
        """
        if self.model is None or self.processor is None:
            raise RuntimeError("CaptionSynthesizer.generate_caption() called before load().")

        import torch

        images = self._keyframes_to_images(keyframes)
        messages = self._build_messages(images, transcript.text, style)

        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)

        with torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                max_new_tokens=self._cfg.max_new_tokens,
                do_sample=False,
            )

        # Strip the prompt tokens; decode only the newly generated continuation.
        prompt_len = inputs["input_ids"].shape[-1]
        new_tokens = generated[0][prompt_len:]
        text = self.processor.decode(new_tokens, skip_special_tokens=True)
        return text.strip()

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
            Mapping of style -> caption text. A per-style failure yields an empty
            string for that style rather than aborting the whole batch.
        """
        captions: dict[Style, str] = {}
        for style in styles:
            try:
                captions[style] = self.generate_caption(keyframes, transcript, style)
            except Exception as exc:  # noqa: BLE001 - never let one style sink the task
                logger.exception("Caption generation failed for style=%s: %s", style, exc)
                captions[style] = ""
        return captions
