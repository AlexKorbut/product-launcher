"""Media transfer: download a donor photo via Telethon, re-upload via Bot API.

Telethon can't hand a Bot-API file_id to a bot, so we download bytes from the
source and upload them when publishing. To keep raw-post rows light we store the
bytes on disk under MEDIA_DIR keyed by source/message id, and reference the path.
"""
import os
from pathlib import Path

import httpx

MEDIA_DIR = Path(os.environ.get("MEDIA_DIR", "/srv/media"))


def _path(source_id: int, message_id: int) -> Path:
    return MEDIA_DIR / f"{source_id}_{message_id}.jpg"


async def download_photo(client, message, source_id: int) -> dict:
    """Download a message photo to disk. Returns a media dict or {}."""
    if not getattr(message, "photo", None):
        return {}
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(source_id, message.id)
    await client.download_media(message, file=str(path))
    return {"type": "photo", "path": str(path)}


async def upload_photo_to_channel(token: str, chat_id: str, path: str, caption: str) -> int:
    """Send a local photo file to a channel via Bot API sendPhoto. Returns message_id."""
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    with open(path, "rb") as f:
        files = {"photo": ("photo.jpg", f, "image/jpeg")}
        data = {"chat_id": chat_id, "caption": caption[:1024], "parse_mode": "HTML"}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, data=data, files=files)
    payload = resp.json()
    if not payload.get("ok"):
        raise RuntimeError(payload.get("description", "sendPhoto failed"))
    return payload["result"]["message_id"]
