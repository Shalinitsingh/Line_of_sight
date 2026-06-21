"""Dashboards & widgets.

Assemble metrics into a dashboard; compute and cache widget results.
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import db

router = APIRouter(tags=["dashboards"])


class DashboardIn(BaseModel):
    name: str
    workspace_id: UUID | None = None


class WidgetIn(BaseModel):
    metric_id: UUID
    viz_type: str = "bar"  # performance_bridge | nine_box | savings | bar
    title: str | None = None
    config: dict = {}


@router.post("/dashboards")
async def create_dashboard(body: DashboardIn, s: AsyncSession = Depends(db)):
    did = (
        await s.execute(
            text("""INSERT INTO dashboards (org_id,workspace_id,name,created_by)
                VALUES (app_current_org(),:w,:n,app_current_user()) RETURNING id"""),
            {
                "w": str(body.workspace_id) if body.workspace_id else None,
                "n": body.name,
            },
        )
    ).scalar_one()
    return {"dashboard_id": str(did)}


@router.post("/dashboards/{dashboard_id}/widgets")
async def add_widget(dashboard_id: UUID, body: WidgetIn, s: AsyncSession = Depends(db)):
    wid = (
        await s.execute(
            text("""
                INSERT INTO widgets
                    (org_id, dashboard_id, metric_id, viz_type, title, config)
                VALUES (app_current_org(), :d, :m, :v, :t, CAST(:c AS jsonb))
                RETURNING id
                """),
            {
                "d": str(dashboard_id),
                "m": str(body.metric_id),
                "v": body.viz_type,
                "t": body.title,
                "c": json.dumps(body.config),
            },
        )
    ).scalar_one()
    return {"widget_id": str(wid)}


@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(dashboard_id: UUID, s: AsyncSession = Depends(db)):
    dash = (
        (
            await s.execute(
                text("SELECT id,name FROM dashboards WHERE id=:d"),
                {"d": str(dashboard_id)},
            )
        )
        .mappings()
        .first()
    )
    if not dash:
        raise HTTPException(404, "dashboard not found")
    widgets = (
        (
            await s.execute(
                text("""SELECT w.id,w.viz_type,w.title,w.cached_result,w.computed_at,
                       m.name AS metric_name, m.unit
                FROM widgets w LEFT JOIN metrics m ON m.id=w.metric_id
                WHERE w.dashboard_id=:d ORDER BY w.position"""),
                {"d": str(dashboard_id)},
            )
        )
        .mappings()
        .all()
    )
    return {"dashboard": dict(dash), "widgets": [dict(w) for w in widgets]}
