from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path

from ..config import PROJECT_ROOT
from .base import DeliveryResult


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "issue"


class FileDeliverer:
    """Zero-config default: copy the PDF into a local outbox dir."""

    channel = "file"

    def __init__(self, outbox: Path | str | None = None) -> None:
        self.outbox = Path(outbox) if outbox else PROJECT_ROOT / ".data" / "outbox"

    def deliver(
        self, pdf_path: Path, *, user_id: str, subject: str, body: str = "", **kwargs
    ) -> DeliveryResult:
        pdf_path = Path(pdf_path)
        try:
            dest_dir = self.outbox / _slug(user_id)
            dest_dir.mkdir(parents=True, exist_ok=True)
            name = f"{_slug(subject)}-{date.today().isoformat()}.pdf"
            dest = dest_dir / name
            shutil.copyfile(pdf_path, dest)
            return DeliveryResult(
                ok=True, channel=self.channel, location=str(dest.resolve())
            )
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult(ok=False, channel=self.channel, detail=str(exc))
