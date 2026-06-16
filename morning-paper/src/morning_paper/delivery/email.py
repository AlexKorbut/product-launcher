from __future__ import annotations

import base64
from pathlib import Path

import httpx

from ..config import get_settings
from .base import DeliveryResult


def _looks_like_email(value: str) -> bool:
    return "@" in value and "." in value.split("@")[-1]


class EmailDeliverer:
    """Email the PDF. Prefer Resend if an API key is set, else SMTP."""

    channel = "email"

    def __init__(
        self,
        *,
        resend_api_key: str | None = None,
        smtp_url: str | None = None,
        from_addr: str = "paper@morning-paper.local",
    ) -> None:
        self.resend_api_key = resend_api_key or get_settings().secrets.resend_api_key
        self.smtp_url = smtp_url
        self.from_addr = from_addr

    def deliver(
        self,
        pdf_path: Path,
        *,
        user_id: str,
        subject: str,
        body: str = "",
        to: str | None = None,
        **kwargs,
    ) -> DeliveryResult:
        to = to or (user_id if _looks_like_email(user_id) else None)
        if not to:
            return DeliveryResult(
                ok=False, channel=self.channel, detail="no recipient address"
            )
        pdf_path = Path(pdf_path)
        if self.resend_api_key:
            return self._send_resend(pdf_path, to=to, subject=subject, body=body)
        if self.smtp_url:
            return self._send_smtp(pdf_path, to=to, subject=subject, body=body)
        return DeliveryResult(
            ok=False, channel=self.channel, detail="no email backend configured"
        )

    def _send_resend(
        self, pdf_path: Path, *, to: str, subject: str, body: str
    ) -> DeliveryResult:
        try:
            content = base64.b64encode(pdf_path.read_bytes()).decode("ascii")
            resp = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self.resend_api_key}"},
                json={
                    "from": self.from_addr,
                    "to": to,
                    "subject": subject,
                    "html": body,
                    "attachments": [
                        {"filename": pdf_path.name, "content": content}
                    ],
                },
                timeout=60,
            )
            resp.raise_for_status()
            msg_id = resp.json().get("id")
            return DeliveryResult(ok=True, channel=self.channel, location=msg_id)
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult(ok=False, channel=self.channel, detail=str(exc))

    def _send_smtp(
        self, pdf_path: Path, *, to: str, subject: str, body: str
    ) -> DeliveryResult:
        try:
            import smtplib
            from email.mime.application import MIMEApplication
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from urllib.parse import urlparse

            parsed = urlparse(self.smtp_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 25

            msg = MIMEMultipart()
            msg["From"] = self.from_addr
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body or "", "html"))
            part = MIMEApplication(pdf_path.read_bytes(), _subtype="pdf")
            part.add_header(
                "Content-Disposition", "attachment", filename=pdf_path.name
            )
            msg.attach(part)

            with smtplib.SMTP(host, port) as smtp:
                if parsed.username:
                    smtp.starttls()
                    smtp.login(parsed.username, parsed.password or "")
                smtp.send_message(msg)
            return DeliveryResult(ok=True, channel=self.channel, location=to)
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult(ok=False, channel=self.channel, detail=str(exc))
