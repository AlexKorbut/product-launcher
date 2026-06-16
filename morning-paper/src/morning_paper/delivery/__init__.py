from __future__ import annotations

from .base import Deliverer, DeliveryResult
from .email import EmailDeliverer
from .file import FileDeliverer
from .telegram_bot import TelegramBotDeliverer, run_onboarding_bot

__all__ = [
    "Deliverer",
    "DeliveryResult",
    "FileDeliverer",
    "TelegramBotDeliverer",
    "EmailDeliverer",
    "run_onboarding_bot",
    "get_deliverer",
]

_REGISTRY = {
    "file": FileDeliverer,
    "telegram": TelegramBotDeliverer,
    "email": EmailDeliverer,
}


def get_deliverer(channel: str = "file", **kwargs) -> Deliverer:
    try:
        cls = _REGISTRY[channel]
    except KeyError:
        raise ValueError(f"unknown delivery channel: {channel!r}") from None
    return cls(**kwargs)
