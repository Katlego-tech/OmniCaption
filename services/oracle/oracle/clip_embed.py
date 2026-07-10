"""Real CLIP encoder over open_clip — an OPTIONAL dependency.

Install for live visual search: ``pip install open_clip_torch pillow`` (pulls
PyTorch; CPU works, a GPU is faster). Everything else in the oracle runs
without it — clip-space moments are simply skipped when it is absent.
"""

from __future__ import annotations


class OpenClipEncoder:
    """ViT-B-32 CLIP embeddings for keyframe images and text queries."""

    def __init__(self, model_name: str = "ViT-B-32", pretrained: str = "laion2b_s34b_b79k") -> None:
        """Load the CLIP model; raises ImportError when open_clip is not installed."""
        import open_clip
        import torch

        self._torch = torch
        self._open_clip = open_clip
        self._model, _, self._preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained
        )
        self._tokenizer = open_clip.get_tokenizer(model_name)
        self._model.eval()

    def embed_images(self, paths: list[str]) -> list[list[float]]:
        """Embed image files into the CLIP space (unit-normalized)."""
        from PIL import Image

        tensors = [self._preprocess(Image.open(p).convert("RGB")) for p in paths]
        with self._torch.no_grad():
            features = self._model.encode_image(self._torch.stack(tensors))
            features = features / features.norm(dim=-1, keepdim=True)
        return features.tolist()

    def embed_text(self, text: str) -> list[float]:
        """Embed a text query into the CLIP space (unit-normalized)."""
        tokens = self._tokenizer([text])
        with self._torch.no_grad():
            features = self._model.encode_text(tokens)
            features = features / features.norm(dim=-1, keepdim=True)
        return features[0].tolist()
