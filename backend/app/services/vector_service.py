"""
ChromaDB vector store service.
One collection per user: resumes_{user_id}
A shared collection for all job descriptions: jobs_descriptions
"""

import logging
import uuid

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton ChromaDB client
_chroma_client: chromadb.AsyncHttpClient | None = None


async def get_chroma_client() -> chromadb.AsyncHttpClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = await chromadb.AsyncHttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


async def get_or_create_collection(collection_name: str) -> chromadb.AsyncCollection:
    client = await get_chroma_client()
    return await client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


async def upsert_resume_embedding(
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
    text: str,
    embedding: list[float],
    metadata: dict | None = None,
) -> str:
    """Store a resume embedding in the user's personal collection."""
    collection_name = f"resumes_{str(user_id).replace('-', '_')}"
    collection = await get_or_create_collection(collection_name)

    doc_id = str(resume_id)
    meta = metadata or {}
    meta.update({"resume_id": str(resume_id), "user_id": str(user_id)})

    await collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text[:5000]],  # ChromaDB document preview
        metadatas=[meta],
    )
    logger.debug("Upserted resume embedding: collection=%s doc=%s", collection_name, doc_id)
    return doc_id


async def upsert_job_embedding(
    job_id: uuid.UUID,
    text: str,
    embedding: list[float],
    metadata: dict | None = None,
) -> str:
    """Store a job description embedding in the shared jobs collection."""
    collection = await get_or_create_collection("job_descriptions")
    doc_id = str(job_id)
    meta = metadata or {}
    meta["job_id"] = str(job_id)

    await collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text[:5000]],
        metadatas=[meta],
    )
    return doc_id


async def query_similar_jobs(
    user_id: uuid.UUID,
    resume_embedding: list[float],
    n_results: int = 20,
) -> list[dict]:
    """
    Find the most similar job descriptions to a resume embedding.
    Returns list of {job_id, score, document}.
    """
    try:
        collection = await get_or_create_collection("job_descriptions")
        results = await collection.query(
            query_embeddings=[resume_embedding],
            n_results=n_results,
            include=["metadatas", "distances", "documents"],
        )
        output = []
        for i, doc_id in enumerate(results["ids"][0]):
            output.append(
                {
                    "job_id": results["metadatas"][0][i].get("job_id", doc_id),
                    "distance": results["distances"][0][i],
                    "score": max(0.0, 1.0 - results["distances"][0][i]),  # cosine: distance=1-similarity
                    "document": results["documents"][0][i] if results.get("documents") else "",
                }
            )
        return output
    except Exception as exc:
        logger.warning("ChromaDB query failed: %s", exc)
        return []


async def delete_resume_embedding(user_id: uuid.UUID, resume_id: uuid.UUID) -> None:
    """Delete a resume embedding from the user's collection."""
    try:
        collection_name = f"resumes_{str(user_id).replace('-', '_')}"
        collection = await get_or_create_collection(collection_name)
        await collection.delete(ids=[str(resume_id)])
    except Exception as exc:
        logger.warning("Failed to delete resume embedding: %s", exc)
