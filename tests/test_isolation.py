"""Regression test for the non-negotiable guarantee: no cross-tenant data access."""

import io

import httpx
import pandas as pd
import pytest

from app.main import app

BASE = "http://test"


def _csv(df):
    b = io.StringIO()
    df.to_csv(b, index=False)
    return b.getvalue().encode()


async def _signup(c, slug):
    r = await c.post(
        "/auth/signup",
        json={
            "org_name": slug,
            "slug": slug,
            "industry": "x",
            "email": f"o@{slug}.com",
            "password": "pw123456",
        },
    )
    return r.json()["token"]


@pytest.mark.asyncio
async def test_no_cross_tenant_access():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=BASE, timeout=30) as c:
        ta = await _signup(c, "tenanta")
        tb = await _signup(c, "tenantb")
        ha = {"Authorization": f"Bearer {ta}"}
        hb = {"Authorization": f"Bearer {tb}"}

        up = await c.post(
            "/datasets",
            headers=hb,
            data={"name": "secret"},
            files={"file": ("b.csv", _csv(pd.DataFrame({"x": [1, 2]})), "text/csv")},
        )
        b_ds = up.json()["dataset_id"]

        # A cannot list B's datasets
        assert (await c.get("/datasets", headers=ha)).json() == []
        # A cannot read B's columns by id
        assert (await c.get(f"/datasets/{b_ds}/columns", headers=ha)).status_code == 404
        # No token => rejected
        assert (await c.get("/datasets")).status_code == 401
