from __future__ import annotations

import os

import httpx

VOYAGE_EMBED_URL = "https://api.voyageai.com/v1/embeddings"
DEFAULT_MODEL = "voyage-multilingual-2"
_BATCH_SIZE = 128


class VoyageClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._key = api_key or os.environ.get("VOYAGE_API_KEY", "")

    def embed(self, texts: list[str], *, model: str = DEFAULT_MODEL) -> list[list[float]]:
        """Return embedding vectors for each text. Batches internally at 128 texts."""
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            chunk = texts[i : i + _BATCH_SIZE]
            response = httpx.post(
                VOYAGE_EMBED_URL,
                headers={"Authorization": f"Bearer {self._key}"},
                json={"input": chunk, "model": model},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            # data["data"] is sorted by index
            for item in sorted(data["data"], key=lambda x: x["index"]):
                all_embeddings.append(item["embedding"])
        return all_embeddings

    def embed_one(self, text: str, *, model: str = DEFAULT_MODEL) -> list[float]:
        return self.embed([text], model=model)[0]
