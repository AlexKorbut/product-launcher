from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import CreditLedger, Organization
from app.schemas import BalanceResponse, CheckoutRequest, CheckoutResponse, LedgerOut
from app.security import Principal, require_org
from app.services import billing

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/packs")
async def list_packs() -> dict:
    """Credit packs available for purchase (price_id -> credits)."""
    return {"packs": billing.price_to_credits_map()}


@router.get("/balance", response_model=BalanceResponse)
async def balance(
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> BalanceResponse:
    org = await session.get(Organization, p.org_id)
    return BalanceResponse(credit_balance=org.credit_balance)


@router.get("/ledger", response_model=list[LedgerOut])
async def ledger(
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> list[LedgerOut]:
    rows = (
        await session.scalars(
            select(CreditLedger).where(CreditLedger.org_id == p.org_id)
            .order_by(CreditLedger.created_at.desc()).limit(100)
        )
    ).all()
    return [LedgerOut.model_validate(r) for r in rows]


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    body: CheckoutRequest, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> CheckoutResponse:
    org = await session.get(Organization, p.org_id)
    try:
        url = billing.create_checkout_session(org, body.price_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001 — surface Stripe config errors cleanly
        raise HTTPException(502, f"Stripe error: {e}")
    return CheckoutResponse(url=url)


@router.post("/webhook")
async def webhook(request: Request, session: AsyncSession = Depends(get_session)) -> dict:
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = billing.verify_webhook(payload, sig)
    except Exception:  # noqa: BLE001 — invalid signature / malformed
        raise HTTPException(400, "Invalid webhook signature")
    granted = await billing.handle_event(session, event)
    return {"received": True, "granted": granted}
