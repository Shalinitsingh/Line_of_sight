"""
Metrics & formulas — the Formula-to-Placeholder lifecycle:

  1. POST /metrics                      create a named KPI
  2. POST /metrics/{id}/propose         AI proposes a DRAFT formula (the placeholder)
  3. POST /formulas/{id}/validate       gate: only validates if all columns resolve
  4. POST /formulas/{id}/execute        decoupled calculator pulls JSONB arrays + evals
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai_assistant import propose_formula
from ..deps import db
from ..evaluator import FormulaError, evaluate

router = APIRouter(tags=["metrics"])


class MetricIn(BaseModel):
    name: str
    description: str | None = None
    unit: str | None = None
    default_viz: str | None = "bar"
    workspace_id: UUID | None = None


class ProposeIn(BaseModel):
    goal: str
    dataset_id: UUID


@router.post("/metrics")
async def create_metric(body: MetricIn, s: AsyncSession = Depends(db)):
    mid = (
        await s.execute(
            text("""
                INSERT INTO metrics
                    (org_id, workspace_id, name, description,
                     unit, default_viz, created_by)
                VALUES (
                    app_current_org(), :w, :n, :d, :u, :v, app_current_user()
                )
                RETURNING id
                """),
            {
                "w": str(body.workspace_id) if body.workspace_id else None,
                "n": body.name,
                "d": body.description,
                "u": body.unit,
                "v": body.default_viz,
            },
        )
    ).scalar_one()
    return {"metric_id": str(mid)}


@router.post("/metrics/{metric_id}/propose")
async def propose(metric_id: UUID, body: ProposeIn, s: AsyncSession = Depends(db)):
    """AI proposes a formula string + column map; stored as a DRAFT placeholder."""
    cols = (
        (
            await s.execute(
                text("""
                    SELECT id, normalized_key, original_header,
                           data_type, is_numeric
                    FROM dataset_columns
                    WHERE dataset_id = :d
                    ORDER BY ordinal
                    """),
                {"d": str(body.dataset_id)},
            )
        )
        .mappings()
        .all()
    )
    if not cols:
        raise HTTPException(404, "dataset has no columns")

    catalog = [
        {
            "key": c["normalized_key"],
            "header": c["original_header"],
            "type": c["data_type"],
            "numeric": c["is_numeric"],
        }
        for c in cols
    ]
    key_to_id = {c["normalized_key"]: c["id"] for c in cols}

    proposal = propose_formula(body.goal, catalog)
    used = [v for v in proposal["variables"] if v in key_to_id]
    if not used:
        raise HTTPException(422, "AI referenced columns not present in dataset")

    version = (
        await s.execute(
            text("SELECT COALESCE(MAX(version),0)+1 FROM formulas WHERE metric_id=:m"),
            {"m": str(metric_id)},
        )
    ).scalar_one()
    fid = (
        await s.execute(
            text("""
                INSERT INTO formulas
                    (org_id, metric_id, version, expression,
                     status, proposed_by_ai)
                VALUES (app_current_org(), :m, :v, :e, 'draft', true)
                RETURNING id
                """),
            {"m": str(metric_id), "v": version, "e": proposal["expression"]},
        )
    ).scalar_one()
    for var in used:
        await s.execute(
            text(
                "INSERT INTO formula_columns "
                "(formula_id, column_id, var_name) VALUES (:f, :c, :v)"
            ),
            {"f": str(fid), "c": str(key_to_id[var]), "v": var},
        )

    return {
        "formula_id": str(fid),
        "expression": proposal["expression"],
        "variables": used,
        "rationale": proposal.get("rationale"),
        "status": "draft",
    }


@router.post("/formulas/{formula_id}/validate")
async def validate(formula_id: UUID, s: AsyncSession = Depends(db)):
    """The gate. The DB trigger refuses validation if any column is missing."""
    try:
        await s.execute(
            text("UPDATE formulas SET status='validated' WHERE id=:f"),
            {"f": str(formula_id)},
        )
    except Exception as exc:
        raise HTTPException(409, f"validation failed: {exc}")
    return {"formula_id": str(formula_id), "status": "validated"}


@router.post("/formulas/{formula_id}/execute")
async def execute(formula_id: UUID, s: AsyncSession = Depends(db)):
    """Decoupled calculator: pull numeric arrays from JSONB, evaluate in the sandbox."""
    meta = (
        await s.execute(
            text("SELECT expression,status FROM formulas WHERE id=:f"),
            {"f": str(formula_id)},
        )
    ).first()
    if not meta:
        raise HTTPException(404, "formula not found")
    if meta.status != "validated":
        raise HTTPException(409, "formula not validated; run the validation gate first")

    binds = (
        await s.execute(
            text("""SELECT fc.var_name, dc.normalized_key, dc.dataset_id
                FROM formula_columns fc JOIN dataset_columns dc ON dc.id=fc.column_id
                WHERE fc.formula_id=:f"""),
            {"f": str(formula_id)},
        )
    ).all()

    variables: dict[str, list[float]] = {}
    for var_name, nkey, ds_id in binds:
        arr = (
            await s.execute(
                text("""
                    SELECT array_agg((data ->> :k)::numeric ORDER BY row_index)
                    FROM dataset_rows
                    WHERE dataset_id = :d AND data ? :k
                    """),
                {"k": nkey, "d": str(ds_id)},
            )
        ).scalar()
        variables[var_name] = [float(x) for x in (arr or [])]

    try:
        result = evaluate(meta.expression, variables)
    except FormulaError as exc:
        raise HTTPException(422, f"evaluation error: {exc}")

    result = float(result) if isinstance(result, (int, float)) else result
    await s.execute(
        text("""
            INSERT INTO audit_logs
                (org_id, actor_id, action, target_type, target_id, detail)
            VALUES (
                app_current_org(), app_current_user(),
                'formula.evaluated', 'formula', :f, CAST(:j AS jsonb)
            )
            """),
        {
            "f": str(formula_id),
            "j": f'{{"result": {result}}}' if isinstance(result, float) else "{}",
        },
    )
    return {
        "formula_id": str(formula_id),
        "expression": meta.expression,
        "result": result,
    }
