"""Thin async Telegram Bot API client (publishing into our own channels)."""
from dataclasses import dataclass

import httpx

API = "https://api.telegram.org/bot{token}/{method}"


class TelegramError(Exception):
    def __init__(self, description: str, retry_after: int | None = None):
        super().__init__(description)
        self.retry_after = retry_after


@dataclass
class SentMessage:
    message_id: int


async def _call(token: str, method: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(API.format(token=token, method=method), json=payload)
    data = resp.json()
    if not data.get("ok"):
        params = data.get("parameters") or {}
        raise TelegramError(
            data.get("description", "unknown telegram error"),
            retry_after=params.get("retry_after"),
        )
    return data["result"]


async def send_post(token: str, chat: str, text: str, media: dict | None = None) -> SentMessage:
    """Send a post; uses sendPhoto when a photo URL/file_id is present."""
    chat_id = chat if chat.startswith("-") else (chat if chat.startswith("@") else f"@{chat}")
    if media and media.get("type") == "photo" and media.get("file_id"):
        result = await _call(
            token,
            "sendPhoto",
            {"chat_id": chat_id, "photo": media["file_id"], "caption": text[:1024], "parse_mode": "HTML"},
        )
    else:
        result = await _call(
            token,
            "sendMessage",
            {"chat_id": chat_id, "text": text[:4096], "parse_mode": "HTML",
             "disable_web_page_preview": True},
        )
    return SentMessage(message_id=result["message_id"])


async def check_bot(token: str, chat: str) -> dict:
    """Verify the bot token and that the bot is an admin of the channel."""
    me = await _call(token, "getMe", {})
    chat_id = chat if chat.startswith("-") else (chat if chat.startswith("@") else f"@{chat}")
    member = await _call(token, "getChatMember", {"chat_id": chat_id, "user_id": me["id"]})
    return {
        "bot_username": me.get("username"),
        "status": member.get("status"),
        "can_post": member.get("status") in ("administrator", "creator"),
    }
