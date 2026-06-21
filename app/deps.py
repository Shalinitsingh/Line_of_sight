"""Request dependencies: verify JWT, resolve tenant, open an RLS-scoped session."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .db import tenant_session
from .security import decode_token


class Principal:
    def __init__(self, user_id: UUID, org_id: UUID, role: str):
        self.user_id, self.org_id, self.role = user_id, org_id, role


async def current_principal(authorization: str = Header(default="")) -> Principal:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    try:
        claims = decode_token(authorization.split(" ", 1)[1])
    except Exception:
        raise HTTPException(401, "invalid or expired token")
    # Tenant comes from the *verified* token, never a client-supplied header.
    return Principal(UUID(claims["sub"]), UUID(claims["org"]), claims["role"])


async def db(principal: Principal = Depends(current_principal)) -> AsyncSession:
    async with tenant_session(principal.org_id, principal.user_id) as session:
        yield session
