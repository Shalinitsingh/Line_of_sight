"""Auth router.

Signup creates an org + owner via the privileged provisioner path;
login issues a JWT.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

from ..db import provisioner_session
from ..security import hash_password, issue_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupIn(BaseModel):
    org_name: str
    slug: str
    industry: str | None = None
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginIn(BaseModel):
    slug: str
    email: EmailStr
    password: str


@router.post("/signup")
async def signup(body: SignupIn):
    """
    Org creation must bypass RLS (no tenant context exists yet), so it runs as
    provisioner. This is the ONLY place that engine is used in the request path.
    """
    async with provisioner_session() as s:
        exists = (
            await s.execute(
                text("SELECT 1 FROM organizations WHERE slug=:s"), {"s": body.slug}
            )
        ).first()
        if exists:
            raise HTTPException(409, "slug already taken")
        org_id = (
            await s.execute(
                text(
                    "INSERT INTO organizations (name, slug, industry) "
                    "VALUES (:n, :s, :i) RETURNING id"
                ),
                {"n": body.org_name, "s": body.slug, "i": body.industry},
            )
        ).scalar_one()
        user_id = (
            await s.execute(
                text("""INSERT INTO users (org_id,email,full_name,role,password_hash)
                    VALUES (:o,:e,:f,'owner',:p) RETURNING id"""),
                {
                    "o": str(org_id),
                    "e": body.email,
                    "f": body.full_name,
                    "p": hash_password(body.password),
                },
            )
        ).scalar_one()
    return {
        "org_id": str(org_id),
        "user_id": str(user_id),
        "token": issue_token(user_id, org_id, "owner"),
    }


@router.post("/login")
async def login(body: LoginIn):
    # Resolve org by slug via provisioner (pre-auth, no tenant context yet).
    async with provisioner_session() as s:
        row = (
            await s.execute(
                text("""SELECT u.id,u.org_id,u.role,u.password_hash
                    FROM users u JOIN organizations o ON o.id=u.org_id
                    WHERE o.slug=:s AND u.email=:e"""),
                {"s": body.slug, "e": body.email},
            )
        ).first()
    if not row or not verify_password(body.password, row.password_hash or ""):
        raise HTTPException(401, "invalid credentials")
    return {
        "token": issue_token(row.id, row.org_id, row.role),
        "org_id": str(row.org_id),
        "role": row.role,
    }
