from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class DeliveryResult:
    ok: bool
    channel: str
    detail: str = ""
    location: str | None = None  # where it landed (path, message id, etc.)


@runtime_checkable
class Deliverer(Protocol):
    channel: str

    def deliver(
        self, pdf_path: Path, *, user_id: str, subject: str, body: str = "", **kwargs
    ) -> DeliveryResult: ...
