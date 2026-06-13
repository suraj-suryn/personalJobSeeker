"""
Embedding generation using Ollama nomic-embed-text model.
Falls back to simple TF-IDF-style hashing if Ollama unavailable.
"""

import hashlib
import logging
import math
from collections import Counter

import httpx
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EMBEDDING_DIM = 768  # nomic-embed-text output dimension


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
async def generate_embedding(text: str) -> list[float]:
    """
    Generate a text embedding using Ollama nomic-embed-text.
    Returns a list of floats (length = EMBEDDING_DIM).
    Falls back to a deterministic hash-based vector if Ollama is unavailable.
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={
                    "model": settings.ollama_embed_model,
                    "prompt": text[:8000],  # Ollama context limit safety
                },
            )
            response.raise_for_status()
            data = response.json()
            embedding: list[float] = data["embedding"]
            return embedding
    except Exception as exc:
        logger.warning("Ollama embedding failed, using fallback: %s", exc)
        return _fallback_embedding(text)


def _fallback_embedding(text: str) -> list[float]:
    """
    Deterministic fallback embedding using character n-gram hashing.
    Not as good as Ollama but ensures the app still works offline.
    """
    text = text.lower().strip()
    words = text.split()

    # Build a simple word frequency vector hashed to EMBEDDING_DIM
    vec = [0.0] * EMBEDDING_DIM
    word_counts = Counter(words)
    total = max(len(words), 1)

    for word, count in word_counts.items():
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = h % EMBEDDING_DIM
        vec[idx] += count / total

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


async def batch_embed(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts sequentially."""
    embeddings = []
    for text in texts:
        emb = await generate_embedding(text)
        embeddings.append(emb)
    return embeddings


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)

    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
