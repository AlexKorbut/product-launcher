"""Stripe integration: checkout sessions for credit packs + webhook handling."""
import json

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import LedgerKind, Organization, StripeEvent
from app.services import credits


def _configure() -> None:
    stripe.api_key = get_settings().stripe_secret_key


def price_to_credits_map() -> dict[str, int]:
    try:
        return {str(k): int(v) for k, v in json.loads(get_settings().stripe_price_credits).items()}
    except (ValueError, TypeError):
        return {}


def create_checkout_session(org: Organization, price_id: str) -> str:
    """Create a Stripe Checkout Session for a credit pack; returns the redirect URL."""
    _configure()
    s = get_settings()
    if price_id not in price_to_credits_map():
        raise ValueError("unknown price id")
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{s.public_base_url}/billing?status=success",
        cancel_url=f"{s.public_base_url}/billing?status=cancel",
        client_reference_id=str(org.id),
        customer=org.stripe_customer_id or None,
        metadata={"org_id": str(org.id), "price_id": price_id},
    )
    return session.url


def verify_webhook(payload: bytes, signature: str):
    """Verify a Stripe webhook signature and return the parsed event."""
    return stripe.Webhook.construct_event(
        payload, signature, get_settings().stripe_webhook_secret
    )


async def handle_event(session: AsyncSession, event) -> bool:
    """Process a verified Stripe event idempotently. Returns True if credits granted."""
    event_id = event["id"]
    if await session.get(StripeEvent, event_id):
        return False  # already processed
    session.add(StripeEvent(id=event_id))

    if event["type"] != "checkout.session.completed":
        await session.commit()
        return False

    obj = event["data"]["object"]
    org_id = int(obj["metadata"]["org_id"])
    price_id = obj["metadata"]["price_id"]
    granted = price_to_credits_map().get(price_id, 0)
    if granted <= 0:
        await session.commit()
        return False

    org = await session.get(Organization, org_id)
    if org and obj.get("customer"):
        org.stripe_customer_id = obj["customer"]
    await credits.grant(session, org_id, granted, LedgerKind.purchase, ref=event_id)
    await session.commit()
    return True
