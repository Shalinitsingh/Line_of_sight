"""Auth router.

Email is the global identity (matches the Figma: no org/company field).
- signup: creates an org (with chosen industry) + owner, returns a token.
- login:  email + password only.
- send-code / verify-code / reset-password: email verification + password reset
  using 6-digit codes that expire in CODE_TTL_MINUTES.

All of this is pre-tenant-context, so it runs through the privileged provisioner
session (RLS bypass). verification_codes is provisioner-only.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

from ..config import get_settings
from ..db import provisioner_session
from ..email import send_code_email
from ..security import hash_password, issue_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

VALID_PURPOSES = {"email_verify", "password_reset"}


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class SignupIn(BaseModel):
    full_name: str | None = None
    email: EmailStr
    password: str
    industry: str = "corporate"  # 'corporate' | 'hospital' (from the toggle)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class SendCodeIn(BaseModel):
    email: EmailStr
    purpose: str = "password_reset"


class VerifyCodeIn(BaseModel):
    email: EmailStr
    code: str
    purpose: str = "email_verify"


class ResetPasswordIn(BaseModel):
    email: EmailStr
    code: str
    new_password: str


class GoogleIn(BaseModel):
    credential: str  # Google ID token (JWT) from Google Identity Services
    industry: str = "corporate"


async def _find_or_create_user(s, email: str, name: str | None, industry: str):
    """Return (user_id, org_id, role, industry). Creates org+owner if new."""
    row = (
        await s.execute(
            text("""
                SELECT u.id, u.org_id, u.role, o.industry
                FROM users u JOIN organizations o ON o.id = u.org_id
                WHERE lower(u.email) = lower(:e)
                """),
            {"e": email},
        )
    ).first()
    if row:
        return row.id, row.org_id, row.role, row.industry

    local = email.split("@")[0]
    org_id = (
        await s.execute(
            text(
                "INSERT INTO organizations (name, slug, industry) "
                "VALUES (:n, :s, :i) RETURNING id"
            ),
            {
                "n": name or f"{local}'s workspace",
                "s": f"{local[:20]}-{secrets.token_hex(3)}".lower(),
                "i": industry,
            },
        )
    ).scalar_one()
    user_id = (
        await s.execute(
            text("""
                INSERT INTO users
                    (org_id, email, full_name, role, email_verified)
                VALUES (:o, :e, :f, 'owner', true)
                RETURNING id
                """),
            {"o": str(org_id), "e": email, "f": name},
        )
    ).scalar_one()
    return user_id, org_id, "owner", industry


# --------------------------------------------------------------------------- #
# Signup / login
# --------------------------------------------------------------------------- #
@router.post("/signup")
async def signup(body: SignupIn):
    """Create an org (named from the user) + owner. Email must be globally unique."""
    local = body.email.split("@")[0]
    org_name = body.full_name or f"{local}'s workspace"
    slug = f"{local[:20]}-{secrets.token_hex(3)}".lower()

    async with provisioner_session() as s:
        taken = (
            await s.execute(
                text("SELECT 1 FROM users WHERE lower(email) = lower(:e)"),
                {"e": body.email},
            )
        ).first()
        if taken:
            raise HTTPException(409, "an account with this email already exists")

        org_id = (
            await s.execute(
                text(
                    "INSERT INTO organizations (name, slug, industry) "
                    "VALUES (:n, :s, :i) RETURNING id"
                ),
                {"n": org_name, "s": slug, "i": body.industry},
            )
        ).scalar_one()
        user_id = (
            await s.execute(
                text("""
                    INSERT INTO users
                        (org_id, email, full_name, role, password_hash)
                    VALUES (:o, :e, :f, 'owner', :p)
                    RETURNING id
                    """),
                {
                    "o": str(org_id),
                    "e": body.email,
                    "f": body.full_name,
                    "p": hash_password(body.password),
                },
            )
        ).scalar_one()

    return {
        "user_id": str(user_id),
        "org_id": str(org_id),
        "industry": body.industry,
        "token": issue_token(user_id, org_id, "owner"),
    }


@router.post("/login")
async def login(body: LoginIn):
    async with provisioner_session() as s:
        row = (
            await s.execute(
                text("""
                    SELECT u.id, u.org_id, u.role, u.password_hash,
                           o.industry, u.full_name
                    FROM users u JOIN organizations o ON o.id = u.org_id
                    WHERE lower(u.email) = lower(:e)
                    """),
                {"e": body.email},
            )
        ).first()
    if not row or not verify_password(body.password, row.password_hash or ""):
        raise HTTPException(401, "invalid email or password")
    return {
        "token": issue_token(row.id, row.org_id, row.role),
        "org_id": str(row.org_id),
        "role": row.role,
        "industry": row.industry,
        "full_name": row.full_name,
    }


@router.post("/google")
async def google_signin(body: GoogleIn):
    """Verify a Google ID token, then log in (creating the account on first use)."""
    if not settings.google_client_id:
        raise HTTPException(
            503, "Google sign-in is not configured (set GOOGLE_CLIENT_ID)"
        )
    try:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token

        info = await asyncio.to_thread(
            id_token.verify_oauth2_token,
            body.credential,
            g_requests.Request(),
            settings.google_client_id,
        )
    except Exception:
        raise HTTPException(401, "invalid Google credential")

    email = info.get("email")
    if not email or not info.get("email_verified", False):
        raise HTTPException(401, "Google account email not verified")

    async with provisioner_session() as s:
        user_id, org_id, role, industry = await _find_or_create_user(
            s, email, info.get("name"), body.industry
        )
    return {
        "token": issue_token(user_id, org_id, role),
        "org_id": str(org_id),
        "role": role,
        "industry": industry,
        "full_name": info.get("name"),
    }


# --------------------------------------------------------------------------- #
# Email verification / password reset codes
# --------------------------------------------------------------------------- #
@router.post("/send-code")
async def send_code(body: SendCodeIn):
    if body.purpose not in VALID_PURPOSES:
        raise HTTPException(422, "invalid purpose")

    code = _new_code()
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        minutes=settings.code_ttl_minutes
    )
    async with provisioner_session() as s:
        # For password_reset we don't reveal whether the account exists.
        await s.execute(
            text("""
                INSERT INTO verification_codes
                    (email, purpose, code_hash, expires_at)
                VALUES (:e, :p, :h, :x)
                """),
            {"e": body.email, "p": body.purpose, "h": _hash_code(code), "x": expires},
        )

    delivered = await send_code_email(body.email, code, body.purpose)
    resp = {"sent": True, "expires_in_minutes": settings.code_ttl_minutes}
    # DEV convenience: surface the code so the flow is testable without SMTP.
    if not delivered and settings.is_dev:
        resp["dev_code"] = code
    return resp


async def _consume_valid_code(s, email: str, code: str, purpose: str) -> bool:
    row = (
        await s.execute(
            text("""
                SELECT id, code_hash, expires_at, consumed_at
                FROM verification_codes
                WHERE lower(email) = lower(:e) AND purpose = :p
                ORDER BY created_at DESC
                LIMIT 1
                """),
            {"e": email, "p": purpose},
        )
    ).first()
    now = dt.datetime.now(dt.timezone.utc)
    if (
        not row
        or row.consumed_at is not None
        or row.expires_at < now
        or row.code_hash != _hash_code(code)
    ):
        if row is not None:
            await s.execute(
                text(
                    "UPDATE verification_codes SET attempts = attempts + 1 "
                    "WHERE id = :i"
                ),
                {"i": str(row.id)},
            )
        return False
    await s.execute(
        text("UPDATE verification_codes SET consumed_at = now() WHERE id = :i"),
        {"i": str(row.id)},
    )
    return True


@router.post("/verify-code")
async def verify_code(body: VerifyCodeIn):
    if body.purpose not in VALID_PURPOSES:
        raise HTTPException(422, "invalid purpose")
    async with provisioner_session() as s:
        ok = await _consume_valid_code(s, body.email, body.code, body.purpose)
        if ok and body.purpose == "email_verify":
            await s.execute(
                text(
                    "UPDATE users SET email_verified = true "
                    "WHERE lower(email) = lower(:e)"
                ),
                {"e": body.email},
            )
    if not ok:
        raise HTTPException(400, "invalid or expired code")
    return {"verified": True}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordIn):
    async with provisioner_session() as s:
        ok = await _consume_valid_code(s, body.email, body.code, "password_reset")
        if not ok:
            raise HTTPException(400, "invalid or expired code")
        updated = (
            await s.execute(
                text(
                    "UPDATE users SET password_hash = :p "
                    "WHERE lower(email) = lower(:e) RETURNING id"
                ),
                {"p": hash_password(body.new_password), "e": body.email},
            )
        ).first()
    if not updated:
        raise HTTPException(404, "no account for that email")
    return {"reset": True}
