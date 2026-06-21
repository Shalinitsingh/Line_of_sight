"""Datasets: upload a CSV/XLSX, profile + ingest into JSONB, list, inspect columns."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import Principal, current_principal, db
from ..ingestion import ingest_dataframe, read_table

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("")
async def upload(
    file: UploadFile = File(...),
    name: str = Form(...),
    workspace_id: str | None = Form(None),
    p: Principal = Depends(current_principal),
    s: AsyncSession = Depends(db),
):
    content = await file.read()
    try:
        df = read_table(content, file.filename or "upload.csv")
    except Exception as exc:
        raise HTTPException(422, f"could not parse file: {exc}")
    if df.empty:
        raise HTTPException(422, "file has no rows")

    ds_id = (
        await s.execute(
            text("""
                INSERT INTO datasets
                    (org_id, workspace_id, name, source_kind,
                     original_filename, uploaded_by, status)
                VALUES (:o, :w, :n, :k, :f, :u, 'profiling')
                RETURNING id
                """),
            {
                "o": str(p.org_id),
                "w": workspace_id,
                "n": name,
                "k": (
                    "xlsx" if (file.filename or "").endswith(("xlsx", "xls")) else "csv"
                ),
                "f": file.filename,
                "u": str(p.user_id),
            },
        )
    ).scalar_one()

    summary = await ingest_dataframe(s, p.org_id, ds_id, df)
    await s.execute(
        text("""
            INSERT INTO audit_logs
                (org_id, actor_id, action, target_type, target_id, detail)
            VALUES (
                app_current_org(), app_current_user(),
                'dataset.ingested', 'dataset', :d, CAST(:j AS jsonb)
            )
            """),
        {"d": str(ds_id), "j": f'{{"rows": {summary["rows"]}}}'},
    )
    return {"dataset_id": str(ds_id), **summary}


@router.get("")
async def list_datasets(s: AsyncSession = Depends(db)):
    rows = (
        (
            await s.execute(
                text(
                    "SELECT id, name, status, row_count, created_at "
                    "FROM datasets ORDER BY created_at DESC"
                )
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


@router.get("/{dataset_id}/columns")
async def columns(dataset_id: UUID, s: AsyncSession = Depends(db)):
    rows = (
        (
            await s.execute(
                text("""
                    SELECT id, original_header, normalized_key, data_type,
                           is_numeric, sample_values, stats
                    FROM dataset_columns
                    WHERE dataset_id = :d
                    ORDER BY ordinal
                    """),
                {"d": str(dataset_id)},
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        raise HTTPException(404, "dataset not found or has no columns")
    return [dict(r) for r in rows]


@router.get("/{dataset_id}/preview")
async def preview(dataset_id: UUID, limit: int = 10, s: AsyncSession = Depends(db)):
    rows = (
        (
            await s.execute(
                text(
                    "SELECT data FROM dataset_rows "
                    "WHERE dataset_id = :d ORDER BY row_index LIMIT :l"
                ),
                {"d": str(dataset_id), "l": limit},
            )
        )
        .scalars()
        .all()
    )
    return rows
