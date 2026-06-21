"""
Schema-agnostic ingestion. Any CSV/XLSX -> dataset_columns (profiled) + dataset_rows
(JSONB keyed by normalized column names). No fixed business tables anywhere.
"""

from __future__ import annotations

import io
import math
import re
from uuid import UUID

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def normalize_key(header: str, taken: set[str]) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", str(header).strip().lower()).strip("_") or "col"
    base, n = key, 1
    while key in taken:
        n += 1
        key = f"{base}_{n}"
    taken.add(key)
    return key


def infer_type(series: pd.Series) -> tuple[str, bool]:
    s = series.dropna()
    if s.empty:
        return "unknown", False
    if pd.api.types.is_bool_dtype(s):
        return "boolean", False
    coerced = pd.to_numeric(s, errors="coerce")
    if coerced.notna().mean() > 0.95:
        is_int = bool((coerced.dropna() % 1 == 0).all())
        return ("integer" if is_int else "number"), True
    if pd.to_datetime(s, errors="coerce", format="mixed").notna().mean() > 0.9:
        return "timestamp", False
    if s.nunique() <= max(20, int(0.2 * len(s))):
        return "categorical", False
    return "text", False


def read_table(content: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content))
    return pd.read_csv(io.BytesIO(content))


def _clean(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if pd.isna(v):
        return None
    if hasattr(v, "item"):  # numpy scalar -> python scalar
        return v.item()
    return v


async def ingest_dataframe(
    session: AsyncSession, org_id: UUID, dataset_id: UUID, df: pd.DataFrame
) -> dict:
    """Profile + load. Returns a summary used by the API response and for embedding."""
    taken: set[str] = set()
    rename: dict = {}
    col_summaries = []

    for ordinal, header in enumerate(df.columns):
        nkey = normalize_key(header, taken)
        rename[header] = nkey
        dtype, is_num = infer_type(df[header])
        col = df[header].dropna()
        stats = {
            "null_count": int(df[header].isna().sum()),
            "distinct": int(col.nunique()),
        }
        if is_num:
            num = pd.to_numeric(col, errors="coerce").dropna()
            if not num.empty:
                stats |= {
                    "min": float(num.min()),
                    "max": float(num.max()),
                    "mean": float(num.mean()),
                }
        samples = [_clean(x) for x in col.unique()[:5]]
        await session.execute(
            text("""
                INSERT INTO dataset_columns
                    (org_id, dataset_id, ordinal, original_header,
                     normalized_key, data_type, is_numeric,
                     sample_values, stats)
                VALUES (:o, :d, :ord, :h, :k, :dt, :num,
                        CAST(:s AS jsonb), CAST(:st AS jsonb))
                """),
            {
                "o": str(org_id),
                "d": str(dataset_id),
                "ord": ordinal,
                "h": str(header),
                "k": nkey,
                "dt": dtype,
                "num": is_num,
                "s": pd.Series(samples).to_json(),
                "st": pd.Series(stats).to_json(),
            },
        )
        col_summaries.append(
            {"key": nkey, "header": str(header), "type": dtype, "numeric": is_num}
        )

    renamed = df.rename(columns=rename)
    records = renamed.to_dict(orient="records")
    for i, row in enumerate(records):
        clean = {k: _clean(v) for k, v in row.items()}
        await session.execute(
            text("""
                INSERT INTO dataset_rows (org_id, dataset_id, row_index, data)
                VALUES (:o, :d, :i, CAST(:j AS jsonb))
                """),
            {
                "o": str(org_id),
                "d": str(dataset_id),
                "i": i,
                "j": pd.Series(clean).to_json(),
            },
        )

    await session.execute(
        text("UPDATE datasets SET row_count=:n, status='ready' WHERE id=:d"),
        {"n": len(records), "d": str(dataset_id)},
    )
    return {"rows": len(records), "columns": col_summaries}
