"""
Apply the schema as the provisioner role. Extensions must already exist (created by
sql/bootstrap.sql on the Postgres container's first boot, or manually for local runs);
schema.sql uses CREATE EXTENSION IF NOT EXISTS, which is a no-op once they're present.

Connection comes from PROVISIONER_DATABASE_URL so the same script works in Docker
(host 'db') and locally (host 127.0.0.1).

Usage: python scripts/init_db.py
"""

import asyncio
import os
import pathlib

import asyncpg

SCHEMA = pathlib.Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
PROV_URL = os.environ.get(
    "PROVISIONER_DATABASE_URL",
    "postgresql+asyncpg://provisioner:provpass@127.0.0.1:5432/lineofsight",
).replace(
    "+asyncpg", ""
)  # asyncpg wants a plain postgresql:// DSN


async def main():
    conn = await asyncpg.connect(PROV_URL)
    try:
        await conn.execute(SCHEMA.read_text())
        print("schema applied")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
