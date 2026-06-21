"""
Semantic search over tenant content via pgvector. Embeddings are tenant-scoped, so the
ANN query is automatically constrained by RLS, so Company A cannot match
Company B's vectors.

embed() is a placeholder: wire to Voyage (voyage-3, 1024-dim) or your provider. A
deterministic stub is provided so the endpoint runs offline.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..deps import db

router = APIRouter(prefix="/search", tags=["search"])
DIM = get_settings().embedding_dim


def embed(textstr: str) -> list[float]:
    """STUB. Replace with a real embedding API call. Deterministic for offline demo."""
    h = hashlib.sha256(textstr.encode()).digest()
    vals = [(b / 255.0) for b in (h * ((DIM // len(h)) + 1))[:DIM]]
    return vals


class IndexIn(BaseModel):
    source_type: str  # dataset | dataset_column | metric | report | document
    source_id: str
    content: str


class QueryIn(BaseModel):
    query: str
    k: int = 5


@router.post("/index")
async def index(body: IndexIn, s: AsyncSession = Depends(db)):
    vec = embed(body.content)
    await s.execute(
        text("""INSERT INTO embeddings (org_id,source_type,source_id,content,embedding)
                VALUES (app_current_org(),CAST(:st AS embedding_source),:sid,:c,:e)"""),
        {
            "st": body.source_type,
            "sid": body.source_id,
            "c": body.content,
            "e": str(vec),
        },
    )
    return {"indexed": True}


@router.post("/query")
async def query(body: QueryIn, s: AsyncSession = Depends(db)):
    vec = embed(body.query)
    rows = (
        (
            await s.execute(
                text("""SELECT source_type, source_id, content,
                       1 - (embedding <=> :e) AS similarity
                FROM embeddings ORDER BY embedding <=> :e LIMIT :k"""),
                {"e": str(vec), "k": body.k},
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]
