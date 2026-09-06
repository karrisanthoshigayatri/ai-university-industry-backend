"""Embedding service abstraction for semantic similarity.

This module provides a clean interface for converting problem text into
vector embeddings.  Two backends are supported:

- **Mock** (EMBEDDING_ENABLED=false, the default):
  Produces deterministic hash-based unit vectors so the application can
  run in development without any ML dependencies installed.

- **BGE** (EMBEDDING_ENABLED=true):
  Uses a locally cached HuggingFace sentence-transformers model
  (default: BAAI/bge-small-en-v1.5).  The model identifier is read from
  the EMBEDDING_MODEL environment variable.

No model paths are hardcoded.  All configuration comes from Settings.
"""

from __future__ import annotations

import hashlib
import logging
import math
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings


logger = logging.getLogger(__name__)

# ── Type alias ─────────────────────────────────────────────────────────────────
Vector = list[float]


# ── Base interface ─────────────────────────────────────────────────────────────

class EmbeddingService(ABC):
    """Abstract base class every embedding backend must implement."""

    @abstractmethod
    def embed(self, text: str) -> Vector:
        """Return a unit-normalised embedding vector for *text*."""

    def cosine_similarity(self, a: Vector, b: Vector) -> float:
        """Return cosine similarity between two equal-length vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return max(-1.0, min(1.0, dot / (mag_a * mag_b)))


# ── Mock backend ───────────────────────────────────────────────────────────────

class MockEmbeddingService(EmbeddingService):
    """Deterministic mock that produces 64-dimensional hash-based vectors.

    Identical texts always produce the same vector.  Similar texts (with
    shared n-grams) produce closer vectors.  Useful for development and
    CI without any ML dependencies.
    """

    DIMS = 64

    def embed(self, text: str) -> Vector:
        normalised = text.lower().strip()
        vec = [0.0] * self.DIMS
        # Slide a window of 3-character shingles over the text and accumulate
        # hash contributions into the vector dimensions.
        for i in range(len(normalised) - 2):
            shingle = normalised[i : i + 3]
            digest = hashlib.sha256(shingle.encode()).digest()
            for j in range(self.DIMS):
                byte_pair = digest[j * 2 % 32] * 256 + digest[(j * 2 + 1) % 32]
                vec[j] += (byte_pair / 65535.0) * 2 - 1
        # Fallback for very short strings
        if not any(vec):
            digest = hashlib.sha256(normalised.encode()).digest()
            vec = [(b / 255.0) * 2 - 1 for b in digest[: self.DIMS]]
        # L2-normalise
        magnitude = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / magnitude for x in vec]


# ── BGE / sentence-transformers backend ───────────────────────────────────────

class BgeEmbeddingService(EmbeddingService):
    """Real BGE embeddings via sentence-transformers.

    The model is lazy-loaded on first use to avoid slowing server startup.
    Requires:  pip install sentence-transformers
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None  # loaded lazily

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import]

            logger.info("Loading embedding model %s …", self._model_name)
            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded.")
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers  "
                "or set EMBEDDING_ENABLED=false to use mock embeddings."
            ) from exc

    def embed(self, text: str) -> Vector:
        self._load()
        embedding = self._model.encode(text, normalize_embeddings=True)  # type: ignore[union-attr]
        return embedding.tolist()


# ── Factory ────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return the configured embedding service (singleton)."""
    settings = get_settings()
    if settings.embedding_enabled:
        logger.info(
            "Embedding service: BGE model '%s'", settings.embedding_model
        )
        return BgeEmbeddingService(settings.embedding_model)
    logger.info("Embedding service: mock (EMBEDDING_ENABLED=false)")
    return MockEmbeddingService()
