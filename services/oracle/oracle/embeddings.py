"""Embedding + chat clients over the Fireworks AI API.

Both are tiny httpx wrappers behind Protocols so tests (and the backend API)
can inject deterministic fakes.
"""

from __future__ import annotations

from typing import Protocol

import httpx

DEFAULT_BASE_URL = "https://api.fireworks.ai/inference/v1"
DEFAULT_EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"
DEFAULT_CHAT_MODEL = "accounts/fireworks/models/kimi-k2p6"


class Embedder(Protocol):
    """Anything that turns a batch of texts into vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class ChatClient(Protocol):
    """Anything that completes a (system, user) prompt pair."""

    def complete(self, system: str, user: str) -> str: ...


class FireworksEmbeddings:
    """Batch text embeddings via the Fireworks embeddings endpoint."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_EMBEDDING_MODEL,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed all texts in one request, preserving order."""
        resp = httpx.post(
            f"{self._base_url}/embeddings",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "input": texts},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in data]


class FireworksChat:
    """Single-turn chat completion via the Fireworks chat endpoint."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_CHAT_MODEL,
        timeout: float = 60.0,
        max_tokens: int = 1024,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        resp = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "max_tokens": self._max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
