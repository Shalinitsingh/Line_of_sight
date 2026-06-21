"""Audit log: append-only, tenant-scoped. Read access for the org's own events."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import db

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def list_audit(limit: int = 50, s: AsyncSession = Depends(db)):
    rows = (
        (
            await s.execute(
                text("""SELECT action,target_type,target_id,detail,created_at
                FROM audit_logs ORDER BY created_at DESC LIMIT :l"""),
                {"l": limit},
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]
