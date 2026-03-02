"""Embedding service — semantic codebase indexing via Qdrant.

Responsibilities:
  - chunk_code(content, path)          split file into ≤512-token chunks
  - embed(texts, user_id, provider)    get float vectors from provider API
  - ensure_collection(project_id, ..)  create/verify Qdrant collection
  - index_file(project_id, path, ..)   chunk → embed → upsert + update summary
  - remove_file_from_index(..))        delete all chunks for a file path
  - search_index(project_id, query, ..) embed query → Qdrant → ranked results
  - generate_summary(..)               one-liner AI summary

Provider embedding strategy:
  provider     embedding model                 vector dim
  openai       text-embedding-3-small          1536
  anthropic    text-embedding-3-small (OpenAI)  1536  (Anthropic has no embeddings API)
  ollama       nomic-embed-text                 768
  lmstudio     nomic-embed-text                 768   (OpenAI-compatible API)

Anthropic users need an OpenAI key stored in the vault to enable Qdrant indexing.
If no suitable key is found, index_file/search_index silently no-ops so file
writes still succeed.

All failures are non-fatal — indexing is best-effort.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Optional

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from config import settings

logger = logging.getLogger(__name__)


_EMBED_MODEL: dict[str, str] = {
    "openai":    "text-embedding-3-small",
    "anthropic": "text-embedding-3-small",
    "ollama":    "nomic-embed-text",
    "lmstudio":  "nomic-embed-text",
}

_VECTOR_DIM: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "nomic-embed-text":        768,
    "mxbai-embed-large":      1024,
}

MAX_CHARS_PER_CHUNK = 2_000
CHUNK_OVERLAP_LINES = 3


_qdrant: Optional[AsyncQdrantClient] = None


def _get_qdrant() -> AsyncQdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = AsyncQdrantClient(url=settings.QDRANT_URL)
    return _qdrant


def _collection_name(project_id: str) -> str:
    return f"proj_{project_id}"


def _point_id(path: str, chunk_index: int) -> int:
    """Deterministic uint64 point ID from (path, chunk_index)."""
    raw = hashlib.md5(f"{path}:{chunk_index}".encode()).digest()
    return int.from_bytes(raw[:8], "big")


async def _get_vault_key(user_id: str, provider: str) -> Optional[str]:
    """Return the decrypted API key for a provider from the vault, or None."""
    try:
        from core.vault import decrypt_secret
        if settings.DATABASE_TYPE == "mongo":
            from database.mongo import get_database
            from models.mongo_models import UserSecretCollection
            db = get_database()
            doc = await UserSecretCollection.find_by_provider(db, user_id, provider)
            if doc:
                return decrypt_secret(user_id, doc["encrypted_value"], doc.get("key_version", 1))
        else:
            from database.sql import SessionLocal
            from models.sql_models import UserSecret
            with SessionLocal() as db:
                row = db.query(UserSecret).filter(
                    UserSecret.user_id == int(user_id),
                    UserSecret.provider == provider,
                    UserSecret.is_deleted.is_(False),
                ).first()
                if row:
                    return decrypt_secret(user_id, row.encrypted_value, row.key_version)
    except Exception as exc:
        logger.debug("Vault key lookup failed for %s/%s: %s", user_id, provider, exc)
    return None


_BOUNDARY_RE = re.compile(
    r"^("
    r"(async\s+)?def\s"
    r"|class\s"
    r"|function\s"
    r"|const\s+\w+\s*=.*=>"
    r"|export\s+(default\s+)?(function|class|const|async)"
    r"|interface\s"
    r"|type\s+\w+\s*="
    r"|#{1,3}\s"
    r")"
)


def chunk_code(
    content: str,
    path: str = "",
    max_chars: int = MAX_CHARS_PER_CHUNK,
) -> list[str]:
    """Split source code into overlapping chunks at logical boundaries.

    Chunking strategy:
      - Splits at function/class/section boundaries.
      - If a section exceeds max_chars, splits further by character count.
      - Carries CHUNK_OVERLAP_LINES lines from the previous chunk for context.

    Args:
        content:   Full file content.
        path:      File path (used for context prefix in each chunk).
        max_chars: Target maximum character count per chunk.

    Returns:
        List of non-empty text chunks.
    """
    if not content.strip():
        return []

    lines = content.splitlines()
    chunks: list[str] = []
    current: list[str] = []
    current_chars = 0

    def _flush():
        nonlocal current, current_chars
        text = "\n".join(current).strip()
        if text:
            chunks.append(f"# {path}\n{text}" if path else text)
        overlap = current[-CHUNK_OVERLAP_LINES:] if len(current) > CHUNK_OVERLAP_LINES else current[:]
        current = overlap
        current_chars = sum(len(l) + 1 for l in current)

    for line in lines:
        line_len = len(line) + 1
        is_boundary = bool(_BOUNDARY_RE.match(line)) and current_chars > 0
        would_overflow = current_chars + line_len > max_chars and current_chars > 0

        if is_boundary or would_overflow:
            _flush()

        current.append(line)
        current_chars += line_len

    if current:
        _flush()

    return [c for c in chunks if c.strip()]


async def _embed_openai(
    texts: list[str],
    api_key: str,
    model: str = "text-embedding-3-small",
) -> list[list[float]]:
    """Call OpenAI embeddings API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"input": texts, "model": model},
        )
        r.raise_for_status()
        data = r.json()
    return [item["embedding"] for item in data["data"]]


async def _embed_ollama(
    texts: list[str],
    base_url: str,
    model: str = "nomic-embed-text",
) -> list[list[float]]:
    """Call Ollama /api/embed endpoint (Ollama ≥ 0.3.6 batch API)."""
    base_url = base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{base_url}/api/embed",
            json={"model": model, "input": texts},
        )
        r.raise_for_status()
        data = r.json()
    return data["embeddings"]


async def _embed_lmstudio(
    texts: list[str],
    base_url: str,
    model: str = "nomic-embed-text",
) -> list[list[float]]:
    """Call LMStudio OpenAI-compatible embeddings endpoint."""
    base_url = base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{base_url}/embeddings",
            json={"input": texts, "model": model},
        )
        r.raise_for_status()
        data = r.json()
    return [item["embedding"] for item in data["data"]]


async def embed(
    texts: list[str],
    user_id: str,
    model_provider: str,
) -> Optional[list[list[float]]]:
    """Return embeddings for a list of texts using the user's configured provider.

    Returns None if no suitable API key is found or the provider is unavailable.
    Caller should treat None as "skip indexing".
    """
    if not texts:
        return []

    embed_provider = model_provider
    if model_provider == "anthropic":
        embed_provider = "openai"

    model = _EMBED_MODEL.get(embed_provider, "nomic-embed-text")

    try:
        if embed_provider == "openai":
            api_key = await _get_vault_key(user_id, "openai")
            if not api_key:
                api_key = settings.OPENAI_API_KEY or None
            if not api_key:
                logger.debug("No OpenAI key for embeddings (user %s)", user_id)
                return None
            return await _embed_openai(texts, api_key, model)

        elif embed_provider == "ollama":
            base_url = await _get_vault_key(user_id, "ollama") or settings.OLLAMA_BASE_URL
            return await _embed_ollama(texts, base_url, model)

        elif embed_provider == "lmstudio":
            base_url = await _get_vault_key(user_id, "lmstudio") or settings.LMSTUDIO_BASE_URL
            return await _embed_lmstudio(texts, base_url, model)

    except Exception as exc:
        logger.warning("Embedding failed (%s): %s", embed_provider, exc)

    return None


async def ensure_collection(project_id: str, vector_size: int) -> None:
    """Create a Qdrant collection for the project if it does not exist.

    If the collection already exists with the same vector size, this is a no-op.
    If the vector size differs (provider changed), the collection is recreated
    — existing index data for that project is lost and will be re-indexed on
    the next file write.
    """
    client = _get_qdrant()
    name = _collection_name(project_id)

    try:
        exists = await client.collection_exists(name)
    except Exception as exc:
        logger.warning("Qdrant collection_exists check failed: %s", exc)
        return

    if exists:
        try:
            info = await client.get_collection(name)
            vec_cfg = info.config.params.vectors
            if hasattr(vec_cfg, "size") and vec_cfg.size == vector_size:
                return
            logger.warning(
                "Qdrant collection %s has incompatible vector config; recreating", name
            )
            await client.delete_collection(name)
        except Exception as exc:
            logger.warning("Could not inspect/delete Qdrant collection %s: %s", name, exc)
            return

    try:
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection %s (dim=%d)", name, vector_size)
    except Exception as exc:
        logger.error("Failed to create Qdrant collection %s: %s", name, exc)


async def index_file(
    project_id: str,
    path: str,
    content: str,
    user_id: str,
    model_provider: str,
) -> None:
    """Chunk, embed, and upsert a project file into Qdrant.

    Also stores a one-line AI-generated summary in the MongoDB ProjectFile doc.

    This function is best-effort: failures are logged and silently swallowed so
    that file writes always succeed even if Qdrant is unreachable.
    """
    chunks = chunk_code(content, path)
    if not chunks:
        return

    vectors = await embed(chunks, user_id, model_provider)
    if vectors is None:
        logger.debug("Skipping Qdrant indexing for %s — no embedding key", path)
        return

    embed_model = _EMBED_MODEL.get(
        model_provider if model_provider != "anthropic" else "openai",
        "nomic-embed-text",
    )
    vector_size = _VECTOR_DIM.get(embed_model, 768)

    try:
        await ensure_collection(project_id, vector_size)

        language = _detect_language(path)
        points = [
            PointStruct(
                id=_point_id(path, i),
                vector=vec,
                payload={"path": path, "chunk": chunk, "language": language, "chunk_index": i},
            )
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]

        client = _get_qdrant()
        await client.upsert(
            collection_name=_collection_name(project_id),
            points=points,
        )
        logger.debug("Indexed %d chunks for %s in project %s", len(points), path, project_id)
    except Exception as exc:
        logger.warning("Qdrant upsert failed for %s: %s", path, exc)

    summary = await generate_summary(path, content, user_id, model_provider)
    if summary:
        try:
            from database.mongo import get_database
            from models.mongo_models import ProjectFileCollection
            db = get_database()
            await ProjectFileCollection.upsert(db, project_id, path, content, {"summary": summary})
        except Exception as exc:
            logger.warning("Could not store summary for %s: %s", path, exc)


async def remove_file_from_index(project_id: str, path: str) -> None:
    """Delete all Qdrant points associated with a file path.

    Best-effort: failures are silently logged.
    """
    client = _get_qdrant()
    name = _collection_name(project_id)
    try:
        exists = await client.collection_exists(name)
        if not exists:
            return
        await client.delete(
            collection_name=name,
            points_selector=Filter(
                must=[FieldCondition(key="path", match=MatchValue(value=path))]
            ),
        )
        logger.debug("Removed Qdrant points for %s in project %s", path, project_id)
    except Exception as exc:
        logger.warning("Qdrant delete failed for %s: %s", path, exc)


async def delete_project_index(project_id: str) -> None:
    """Drop the entire Qdrant collection for a project (called on project deletion).

    Best-effort: failures are logged but never raised.
    """
    client = _get_qdrant()
    name = _collection_name(project_id)
    try:
        exists = await client.collection_exists(name)
        if exists:
            await client.delete_collection(name)
            logger.info("Deleted Qdrant collection %s for project %s", name, project_id)
    except Exception as exc:
        logger.warning("Could not delete Qdrant collection %s: %s", name, exc)


async def search_index(
    project_id: str,
    query: str,
    top_k: int,
    user_id: str,
    model_provider: str,
) -> list[dict]:
    """Semantic search over a project's Qdrant index.

    Returns a list of dicts with keys: path, chunk, language, score.
    Returns [] if Qdrant is unavailable or no embedding key is configured.
    """
    vectors = await embed([query], user_id, model_provider)
    if not vectors:
        return []

    query_vector = vectors[0]
    client = _get_qdrant()
    name = _collection_name(project_id)

    try:
        exists = await client.collection_exists(name)
        if not exists:
            return []

        results = await client.query_points(
            collection_name=name,
            query=query_vector,
            limit=max(1, min(top_k, 20)),
            with_payload=True,
        )
        return [
            {
                "path":     r.payload.get("path", ""),
                "chunk":    r.payload.get("chunk", ""),
                "language": r.payload.get("language", ""),
                "score":    r.score,
            }
            for r in results.points
        ]
    except Exception as exc:
        logger.warning("Qdrant search failed: %s", exc)
        return []


async def generate_summary(
    path: str,
    content: str,
    user_id: str,
    model_provider: str,
) -> Optional[str]:
    """Generate a one-line AI summary for a file using the cheapest available model.

    Uses cloud providers (anthropic → haiku, openai → gpt-4.1-mini) for summaries.
    Skips local providers (ollama/lmstudio) — not worth the latency for a one-liner.
    Returns None on any failure so callers can silently skip.
    """
    try:
        from services.model_router import get_cheap_model_id, get_model_for_user
        model_id = get_cheap_model_id(model_provider)
        if not model_id:
            return None

        llm = await get_model_for_user(model_provider, model_id, user_id)
        snippet = content[:3_000]
        prompt = (
            f"Summarise this file in one sentence (max 20 words).\n"
            f"File: {path}\n\n{snippet}"
        )
        result = await llm.ainvoke(prompt)
        summary = result.content.strip() if hasattr(result, "content") else str(result).strip()
        return summary.splitlines()[0][:200] if summary else None
    except Exception as exc:
        logger.debug("Summary generation failed for %s: %s", path, exc)
        return None


_EXT_TO_LANG: dict[str, str] = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "tsx", ".jsx": "jsx", ".html": "html", ".css": "css",
    ".scss": "scss", ".json": "json", ".md": "markdown",
    ".yaml": "yaml", ".yml": "yaml", ".sh": "bash",
    ".toml": "toml", ".sql": "sql", ".go": "go", ".rs": "rust",
}


def _detect_language(path: str) -> str:
    name = os.path.basename(path).lower()
    if name == "dockerfile":
        return "dockerfile"
    _, ext = os.path.splitext(name)
    return _EXT_TO_LANG.get(ext, "text")
