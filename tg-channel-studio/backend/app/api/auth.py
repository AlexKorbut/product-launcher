from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import LedgerKind, Membership, Organization, Role, User
from app.schemas import LoginRequest, MeResponse, SignupRequest, TokenResponse
from app.security import (
    Principal,
    create_token,
    hash_password,
    require_org,
    verify_password,
)
from app.services import credits

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    s = get_settings()
    existing = await session.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    session.add(user)
    await session.flush()

    org = Organization(name=body.org_name, owner_user_id=user.id)
    if body.referral_code:
        referrer = await session.scalar(
            select(Organization).where(Organization.referral_code == body.referral_code)
        )
        if referrer:
            org.referred_by_org_id = referrer.id
    session.add(org)
    await session.flush()

    session.add(Membership(user_id=user.id, org_id=org.id, role=Role.owner))

    # Welcome credits + referral bonus to both sides.
    await credits.grant(session, org.id, s.signup_bonus_credits, LedgerKind.bonus, ref="signup")
    if org.referred_by_org_id:
        await credits.grant(session, org.id, s.referral_bonus_credits, LedgerKind.referral, ref="referred")
        await credits.grant(
            session, org.referred_by_org_id, s.referral_bonus_credits, LedgerKind.referral,
            ref=f"referral:{org.id}",
        )
    await session.commit()
    return TokenResponse(access_token=create_token(user.id, org.id, user.email))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    user = await session.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    membership = await session.scalar(select(Membership).where(Membership.user_id == user.id))
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No organization")
    return TokenResponse(access_token=create_token(user.id, membership.org_id, user.email))


@router.get("/me", response_model=MeResponse)
async def me(
    principal: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> MeResponse:
    org = await session.get(Organization, principal.org_id)
    return MeResponse(
        user_id=principal.user_id,
        email=principal.email,
        org_id=org.id,
        org_name=org.name,
        credit_balance=org.credit_balance,
        plan=org.plan,
        referral_code=org.referral_code,
    )
