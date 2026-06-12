"""Credit accounting: atomic debit/grant with an append-only ledger."""
import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import CreditLedger, LedgerKind, Organization


def cost_to_credits(cost_usd: float) -> int:
    """Convert raw model $ cost to customer-facing credits (with markup)."""
    s = get_settings()
    if cost_usd <= 0:
        return 0
    return max(1, math.ceil(cost_usd * s.generation_markup / s.credit_price_usd))


async def get_balance(session: AsyncSession, org_id: int) -> int:
    return await session.scalar(
        select(Organization.credit_balance).where(Organization.id == org_id)
    ) or 0


async def _apply(
    session: AsyncSession, org_id: int, delta: int, kind: LedgerKind, ref: str = ""
) -> int:
    """Atomically adjust balance and append a ledger row. Returns new balance.

    Uses a row lock so concurrent debits (multiple generator workers) are safe.
    The session is expected to be committed by the caller.
    """
    stmt = select(Organization).where(Organization.id == org_id).with_for_update()
    org = await session.scalar(stmt)
    if org is None:
        raise ValueError(f"org {org_id} not found")
    org.credit_balance += delta
    session.add(
        CreditLedger(
            org_id=org_id, delta=delta, balance_after=org.credit_balance, kind=kind, ref=ref
        )
    )
    return org.credit_balance


async def grant(session: AsyncSession, org_id: int, credits: int, kind: LedgerKind, ref: str = "") -> int:
    return await _apply(session, org_id, abs(credits), kind, ref)


async def debit(session: AsyncSession, org_id: int, credits: int, ref: str = "") -> int:
    return await _apply(session, org_id, -abs(credits), LedgerKind.debit, ref)
