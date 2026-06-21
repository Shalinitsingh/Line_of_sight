"""
Database engines and the RLS-enforcing tenant session.

Two engines:
  * app_engine        -> connects as app_user (NOBYPASSRLS). All request traffic.
  * provisioner_engine-> connects as provisioner (BYPASSRLS). Signup/migrations only.

tenant_session() pins app.current_org_id with SET LOCAL inside a transaction, so a
pooled connection can never leak one tenant's context into another request. If context
is unset, RLS matches zero rows -> fail closed.
"""

from __future__ import annotations

import contextlib
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings

settings = get_settings()

app_engine = create_async_engine(
    settings.app_database_url, pool_size=20, max_overflow=10, pool_pre_ping=True
)
provisioner_engine = create_async_engine(
    settings.provisioner_database_url, pool_size=5, max_overflow=5, pool_pre_ping=True
)

AppSession = async_sessionmaker(app_engine, expire_on_commit=False, class_=AsyncSession)
ProvisionerSession = async_sessionmaker(
    provisioner_engine, expire_on_commit=False, class_=AsyncSession
)


@contextlib.asynccontextmanager
async def tenant_session(org_id: UUID, user_id: UUID | None = None):
    """RLS-scoped transaction. Commits on clean exit, rolls back on error."""
    async with AppSession() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_org_id', :org, true)"),
                {"org": str(org_id)},
            )
            if user_id is not None:
                await session.execute(
                    text("SELECT set_config('app.current_user_id', :uid, true)"),
                    {"uid": str(user_id)},
                )
            yield session


@contextlib.asynccontextmanager
async def provisioner_session():
    """Privileged, RLS-bypassing session. Use ONLY for signup and migrations."""
    async with ProvisionerSession() as session:
        async with session.begin():
            yield session
