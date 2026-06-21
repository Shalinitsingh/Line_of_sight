"""Line-of-Sight API entrypoint."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import audit, auth, dashboards, datasets, metrics, reports, search

app = FastAPI(
    title="Line-of-Sight",
    description=(
        "Multi-tenant AI ROI analytics. " "Schema-agnostic ingestion, RLS isolation."
    ),
    version="1.0.0",
)

# CORS so a browser frontend (Vite :5173, CRA/Next :3000) can call the API.
# Lock CORS_ORIGINS down to your real domain in production.
_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(metrics.router)
app.include_router(dashboards.router)
app.include_router(reports.router)
app.include_router(search.router)
app.include_router(audit.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
