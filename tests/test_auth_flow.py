"""End-to-end test for email verification + password reset (DEV-mode codes)."""

import httpx
import pytest

from app.main import app

BASE = "http://test"


@pytest.mark.asyncio
async def test_email_verification_and_reset():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=BASE, timeout=30) as c:
        email = "verify-me@example.com"

        # sign up (email-only identity)
        su = await c.post(
            "/auth/signup",
            json={
                "full_name": "Verify Me",
                "email": email,
                "password": "pw123456",
                "industry": "hospital",
            },
        )
        assert su.status_code == 200, su.text
        assert su.json()["industry"] == "hospital"

        # request an email-verify code; DEV mode returns it
        sc = await c.post(
            "/auth/send-code", json={"email": email, "purpose": "email_verify"}
        )
        assert sc.status_code == 200
        code = sc.json()["dev_code"]

        # wrong code is rejected
        bad = await c.post(
            "/auth/verify-code",
            json={"email": email, "code": "000000", "purpose": "email_verify"},
        )
        assert bad.status_code == 400

        # correct code verifies
        ok = await c.post(
            "/auth/verify-code",
            json={"email": email, "code": code, "purpose": "email_verify"},
        )
        assert ok.status_code == 200 and ok.json()["verified"] is True

        # password reset flow
        rc = await c.post(
            "/auth/send-code", json={"email": email, "purpose": "password_reset"}
        )
        reset_code = rc.json()["dev_code"]
        rp = await c.post(
            "/auth/reset-password",
            json={"email": email, "code": reset_code, "new_password": "newpw7890"},
        )
        assert rp.status_code == 200

        # old password fails, new password works
        assert (
            await c.post("/auth/login", json={"email": email, "password": "pw123456"})
        ).status_code == 401
        good = await c.post(
            "/auth/login", json={"email": email, "password": "newpw7890"}
        )
        assert good.status_code == 200 and "token" in good.json()
