from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Invitation, LedgerKind, Membership, Organization, Role, User
from app.schemas import (
    LoginRequest,
    MeResponse,
    OrgMembership,
    RequestResetBody,
    ResetBody,
    SignupRequest,
    SwitchOrgBody,
    TokenBody,
    TokenResponse,
)
from app.security import (
    Principal,
    create_purpose_token,
    create_token,
    hash_password,
    require_org,
    verify_password,
    verify_purpose_token,
)
from app.services import credits
from app.services.email import reset_url, send_email, verify_url

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _role(session: AsyncSession, user_id: int, org_id: int) -> str:
    role = await session.scalar(
        select(Membership.role).where(
            Membership.user_id == user_id, Membership.org_id == org_id
        )
    )
    return role.value if role else "editor"


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

    await credits.grant(session, org.id, s.signup_bonus_credits, LedgerKind.bonus, ref="signup")
    if org.referred_by_org_id:
        await credits.grant(session, org.id, s.referral_bonus_credits, LedgerKind.referral, ref="referred")
        await credits.grant(
            session, org.referred_by_org_id, s.referral_bonus_credits, LedgerKind.referral,
            ref=f"referral:{org.id}",
        )
    await session.commit()

    token = create_purpose_token(user.id, "verify")
    await send_email(user.email, "Подтверждение email — TG Channel Studio",
                     f"Подтверди адрес: {verify_url(token)}")
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
    user = await session.get(User, principal.user_id)
    return MeResponse(
        user_id=principal.user_id, email=principal.email,
        email_verified=user.email_verified,
        org_id=org.id, org_name=org.name,
        role=await _role(session, principal.user_id, org.id),
        credit_balance=org.credit_balance, plan=org.plan, referral_code=org.referral_code,
    )


@router.get("/orgs", response_model=list[OrgMembership])
async def my_orgs(
    principal: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> list[OrgMembership]:
    rows = (
        await session.execute(
            select(Organization, Membership.role)
            .join(Membership, Membership.org_id == Organization.id)
            .where(Membership.user_id == principal.user_id)
            .order_by(Organization.id)
        )
    ).all()
    return [OrgMembership(org_id=o.id, org_name=o.name, role=r.value) for o, r in rows]


@router.post("/switch-org", response_model=TokenResponse)
async def switch_org(
    body: SwitchOrgBody, principal: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    membership = await session.scalar(
        select(Membership).where(
            Membership.user_id == principal.user_id, Membership.org_id == body.org_id
        )
    )
    if membership is None:
        raise HTTPException(403, "Not a member of this organization")
    return TokenResponse(access_token=create_token(principal.user_id, body.org_id, principal.email))


@router.post("/request-verify")
async def request_verify(
    principal: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> dict:
    user = await session.get(User, principal.user_id)
    if user.email_verified:
        return {"sent": False, "detail": "already verified"}
    token = create_purpose_token(user.id, "verify")
    await send_email(user.email, "Подтверждение email — TG Channel Studio",
                     f"Подтверди адрес: {verify_url(token)}")
    return {"sent": True}


@router.post("/verify")
async def verify(body: TokenBody, session: AsyncSession = Depends(get_session)) -> dict:
    user_id = verify_purpose_token(body.token, "verify")
    if user_id is None:
        raise HTTPException(400, "Invalid or expired token")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    user.email_verified = True
    await session.commit()
    return {"verified": True}


@router.post("/request-reset")
async def request_reset(body: RequestResetBody, session: AsyncSession = Depends(get_session)) -> dict:
    user = await session.scalar(select(User).where(User.email == body.email.lower()))
    # Always return 200 to avoid leaking which emails are registered.
    if user:
        token = create_purpose_token(user.id, "reset", ttl_hours=2)
        await send_email(user.email, "Сброс пароля — TG Channel Studio",
                         f"Сбросить пароль: {reset_url(token)}")
    return {"sent": True}


@router.post("/reset")
async def reset(body: ResetBody, session: AsyncSession = Depends(get_session)) -> dict:
    user_id = verify_purpose_token(body.token, "reset")
    if user_id is None:
        raise HTTPException(400, "Invalid or expired token")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    user.password_hash = hash_password(body.password)
    await session.commit()
    return {"reset": True}


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(
    body: TokenBody, principal: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    """Logged-in user accepts an org invite sent to their email."""
    inv = await session.scalar(select(Invitation).where(Invitation.token == body.token))
    if inv is None or inv.accepted:
        raise HTTPException(400, "Invalid or used invitation")
    if inv.email.lower() != principal.email.lower():
        raise HTTPException(403, "Invitation was sent to a different email")
    existing = await session.scalar(
        select(Membership).where(
            Membership.user_id == principal.user_id, Membership.org_id == inv.org_id
        )
    )
    if existing is None:
        session.add(Membership(user_id=principal.user_id, org_id=inv.org_id, role=inv.role))
    inv.accepted = True
    await session.commit()
    # Issue a token scoped to the newly joined org.
    return TokenResponse(access_token=create_token(principal.user_id, inv.org_id, principal.email))
