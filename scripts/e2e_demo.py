"""
End-to-end proof. Drives the real ASGI app in-process (httpx ASGITransport) against
the live Postgres. Two tenants with DIFFERENT schemas (healthcare vs retail), full
AI->validate->execute flow, semantic search, and the cross-tenant isolation assertion.

Run: python scripts/e2e_demo.py
"""

import asyncio
import io
import sys

import httpx
import pandas as pd

sys.path.insert(0, ".")
from app.main import app  # noqa: E402

BASE = "http://test"


def csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode()


# Two tenants, deliberately unrelated schemas — proves schema-agnostic ingestion.
ACME = pd.DataFrame(
    {  # healthcare: denials per training hours
        "Claim ID": [1, 2, 3, 4, 5],
        "Denials": [12, 8, 5, 3, 2],
        "Completed Training Hours": [10, 20, 40, 60, 80],
    }
)
GLOBEX = pd.DataFrame(
    {  # retail: revenue per training hours
        "Store": ["A", "B", "C", "D"],
        "Closed Won Revenue": [1000, 2200, 3400, 5000],
        "Completed Training Hours": [10, 30, 50, 90],
    }
)


async def hdr(client, token):
    return {"Authorization": f"Bearer {token}"}


async def onboard(client, slug, industry, df, goal, dataset_name):
    r = await client.post(
        "/auth/signup",
        json={
            "org_name": slug.title(),
            "slug": slug,
            "industry": industry,
            "email": f"owner@{slug}.com",
            "password": "pw123456",
        },
    )
    r.raise_for_status()
    tok = r.json()["token"]
    h = await hdr(client, tok)

    up = await client.post(
        "/datasets",
        headers=h,
        data={"name": dataset_name},
        files={"file": (f"{slug}.csv", csv_bytes(df), "text/csv")},
    )
    up.raise_for_status()
    ds_id = up.json()["dataset_id"]
    print(
        f"  [{slug}] ingested {up.json()['rows']} rows, "
        f"cols={[c['key'] for c in up.json()['columns']]}"
    )

    m = await client.post(
        "/metrics",
        headers=h,
        json={"name": goal, "unit": "ratio", "default_viz": "performance_bridge"},
    )
    mid = m.json()["metric_id"]
    prop = await client.post(
        f"/metrics/{mid}/propose", headers=h, json={"goal": goal, "dataset_id": ds_id}
    )
    prop.raise_for_status()
    fid = prop.json()["formula_id"]
    proposal = prop.json()
    print(
        f"  [{slug}] AI proposed: {proposal['expression']}  "
        f"(vars={proposal['variables']})"
    )

    v = await client.post(f"/formulas/{fid}/validate", headers=h)
    v.raise_for_status()
    ex = await client.post(f"/formulas/{fid}/execute", headers=h)
    ex.raise_for_status()
    print(f"  [{slug}] executed -> result = {ex.json()['result']:.4f}")
    return tok, ds_id


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=BASE, timeout=30) as c:
        print("\n== Onboard Acme (healthcare) ==")
        acme_tok, acme_ds = await onboard(
            c,
            "acme",
            "healthcare",
            ACME,
            "denials per completed_training_hours",
            "Q2 Claims",
        )

        print("\n== Onboard Globex (retail) ==")
        glob_tok, glob_ds = await onboard(
            c,
            "globex",
            "retail",
            GLOBEX,
            "closed_won_revenue per completed_training_hours",
            "Q2 Sales",
        )

        print("\n== ISOLATION CHECK ==")
        # Acme lists its datasets -> should see ONLY its own.
        mine = (await c.get("/datasets", headers=await hdr(c, acme_tok))).json()
        print(f"  Acme sees datasets: {[d['name'] for d in mine]}")
        assert all(
            d["name"] == "Q2 Claims" for d in mine
        ), "LEAK: Acme saw foreign data!"

        # Acme tries to read Globex's dataset columns by ID -> RLS returns 404.
        cross = await c.get(
            f"/datasets/{glob_ds}/columns", headers=await hdr(c, acme_tok)
        )
        print(
            f"  Acme requesting Globex dataset by ID -> "
            f"HTTP {cross.status_code} (expect 404)"
        )
        assert cross.status_code == 404, "LEAK: cross-tenant read succeeded!"

        print("\n== Semantic search (tenant-scoped pgvector) ==")
        h = await hdr(c, glob_tok)
        await c.post(
            "/search/index",
            headers=h,
            json={
                "source_type": "dataset",
                "source_id": glob_ds,
                "content": "quarterly retail sales and training ROI",
            },
        )
        q = await c.post(
            "/search/query", headers=h, json={"query": "sales ROI", "k": 3}
        )
        print(f"  Globex search hits: {len(q.json())}")
        # Acme's search must NOT see Globex's vector.
        qa = await c.post(
            "/search/query",
            headers=await hdr(c, acme_tok),
            json={"query": "sales ROI", "k": 3},
        )
        print(f"  Acme search hits (should be 0): {len(qa.json())}")
        assert len(qa.json()) == 0, "LEAK: Acme matched Globex embedding!"

        print("\n== Audit trail ==")
        a = (await c.get("/audit", headers=await hdr(c, acme_tok))).json()
        print(f"  Acme audit events: {[e['action'] for e in a]}")

    print("\n*** ALL END-TO-END CHECKS PASSED ***")


if __name__ == "__main__":
    asyncio.run(main())
