"""Reports: freeze a snapshot of metric results into an immutable payload."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import db

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportIn(BaseModel):
    title: str
    payload: dict = {}
    workspace_id: UUID | None = None


@router.post("")
async def create_report(body: ReportIn, s: AsyncSession = Depends(db)):
    rid = (
        await s.execute(
            text("""
                INSERT INTO reports
                    (org_id, workspace_id, title, payload, generated_by)
                VALUES (
                    app_current_org(), :w, :t,
                    CAST(:p AS jsonb), app_current_user()
                )
                RETURNING id
                """),
            {
                "w": str(body.workspace_id) if body.workspace_id else None,
                "t": body.title,
                "p": json.dumps(body.payload),
            },
        )
    ).scalar_one()
    return {"report_id": str(rid)}


@router.get("")
async def list_reports(s: AsyncSession = Depends(db)):
    rows = (
        (
            await s.execute(
                text("SELECT id,title,created_at FROM reports ORDER BY created_at DESC")
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]
