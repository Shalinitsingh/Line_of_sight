"""
Email delivery for verification codes.

If SMTP is configured (SMTP_HOST set), sends a real email. Otherwise runs in DEV
mode: logs the code to the API console and returns it to the caller so the whole
verification flow works locally with no email provider. Flip to real email by
setting the SMTP_* env vars; no code change needed.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from .config import get_settings

logger = logging.getLogger("lineofsight.email")
settings = get_settings()


def _build(to: str, code: str, purpose: str) -> EmailMessage:
    action = (
        "reset your password" if purpose == "password_reset" else "verify your email"
    )
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = f"Your Line-of-Sight code: {code}"
    msg.set_content(
        f"Use this code to {action}: {code}\n\n"
        f"It expires in {settings.code_ttl_minutes} minutes.\n"
        f"If you didn't request this, you can ignore this email."
    )
    return msg


def _send_smtp(msg: EmailMessage) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
        if settings.smtp_starttls:
            s.starttls()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_password or "")
        s.send_message(msg)


async def send_code_email(to: str, code: str, purpose: str) -> bool:
    """
    Returns True if delivered via SMTP, False if running in DEV mode (no SMTP).
    In DEV mode the caller surfaces the code so the flow is testable.
    """
    if not settings.smtp_host:
        logger.warning("DEV email: code for %s (%s) = %s", to, purpose, code)
        return False
    await asyncio.to_thread(_send_smtp, _build(to, code, purpose))
    return True
