from __future__ import annotations

from pathlib import Path

import httpx

from ..config import get_settings
from .base import DeliveryResult


class TelegramBotDeliverer:
    """Send the PDF as a document via the Telegram Bot API (dependency-light)."""

    channel = "telegram"

    def __init__(self, bot_token: str | None = None) -> None:
        self.bot_token = bot_token or get_settings().secrets.telegram_bot_token

    def deliver(
        self,
        pdf_path: Path,
        *,
        user_id: str,
        subject: str,
        body: str = "",
        chat_id: str | None = None,
        **kwargs,
    ) -> DeliveryResult:
        if not self.bot_token:
            return DeliveryResult(ok=False, channel=self.channel, detail="no bot token")
        chat_id = chat_id or user_id
        pdf_path = Path(pdf_path)
        try:
            data = pdf_path.read_bytes()
            url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
            resp = httpx.post(
                url,
                files={"document": (pdf_path.name, data, "application/pdf")},
                data={"chat_id": str(chat_id), "caption": subject},
                timeout=60,
            )
            resp.raise_for_status()
            payload = resp.json()
            if not payload.get("ok"):
                return DeliveryResult(
                    ok=False, channel=self.channel, detail=str(payload)
                )
            msg_id = payload.get("result", {}).get("message_id")
            return DeliveryResult(
                ok=True,
                channel=self.channel,
                location=str(msg_id) if msg_id is not None else None,
            )
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult(ok=False, channel=self.channel, detail=str(exc))


async def run_onboarding_bot(bot_token: str | None = None, *, on_setup=None) -> None:
    """Long-polling aiogram bot: /start collects output language, topics, theme.

    Calls on_setup(user_id, prefs: dict) when the user finishes. Lazy-imports aiogram;
    raises RuntimeError('pip install morning-paper[bot]') if missing.
    """
    try:
        from aiogram import Bot, Dispatcher
        from aiogram.filters import Command
        from aiogram.types import Message
    except ImportError as exc:  # pragma: no cover - optional dep
        raise RuntimeError("pip install morning-paper[bot]") from exc

    token = bot_token or get_settings().secrets.telegram_bot_token
    if not token:
        raise RuntimeError("no bot token")

    bot = Bot(token)
    dp = Dispatcher()
    # in-memory state keyed by user id: {"step": str, "prefs": dict}
    sessions: dict[int, dict] = {}

    steps = ("lang", "topics", "theme")
    prompts = {
        "lang": "Welcome! What output language do you want? (e.g. ru, en)",
        "topics": "Great. List your interests (free text).",
        "theme": "Finally, pick a theme by name (e.g. times-classic). Send /done when ready.",
    }

    @dp.message(Command("start"))
    async def start(message: Message) -> None:  # pragma: no cover - needs aiogram
        sessions[message.from_user.id] = {"step": "lang", "prefs": {}}
        await message.answer(prompts["lang"])

    @dp.message(Command("done"))
    async def done(message: Message) -> None:  # pragma: no cover - needs aiogram
        uid = message.from_user.id
        sess = sessions.pop(uid, None)
        if not sess:
            await message.answer("Send /start first.")
            return
        if on_setup is not None:
            on_setup(str(uid), sess["prefs"])
        await message.answer("All set! Your morning paper is configured.")

    @dp.message()
    async def collect(message: Message) -> None:  # pragma: no cover - needs aiogram
        uid = message.from_user.id
        sess = sessions.get(uid)
        if not sess:
            await message.answer("Send /start to begin.")
            return
        step = sess["step"]
        sess["prefs"][step] = (message.text or "").strip()
        idx = steps.index(step)
        if idx + 1 < len(steps):
            nxt = steps[idx + 1]
            sess["step"] = nxt
            await message.answer(prompts[nxt])
        else:
            await message.answer("Send /done to finish.")

    await dp.start_polling(bot)
