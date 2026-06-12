"""Email delivery. Logs to stdout in dev; uses SMTP when configured."""
import asyncio
import logging
from email.message import EmailMessage

from app.config import get_settings

log = logging.getLogger("email")


def _smtp_send(to: str, subject: str, body: str) -> None:
    import smtplib

    s = get_settings()
    msg = EmailMessage()
    msg["From"] = s.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(s.smtp_host, s.smtp_port) as server:
        server.starttls()
        if s.smtp_user:
            server.login(s.smtp_user, s.smtp_password)
        server.send_message(msg)


async def send_email(to: str, subject: str, body: str) -> None:
    s = get_settings()
    if s.smtp_host:
        await asyncio.to_thread(_smtp_send, to, subject, body)
    else:
        # Dev mode: print the link so it can be copied from logs.
        log.info("[EMAIL] to=%s | %s\n%s", to, subject, body)


def verify_url(token: str) -> str:
    return f"{get_settings().public_base_url}/verify?token={token}"


def reset_url(token: str) -> str:
    return f"{get_settings().public_base_url}/reset?token={token}"


def invite_url(token: str) -> str:
    return f"{get_settings().public_base_url}/accept-invite?token={token}"
