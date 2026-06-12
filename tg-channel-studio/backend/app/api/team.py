from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Invitation, Membership, Role, User
from app.schemas import InvitationOut, InviteBody, MemberOut, RoleBody
from app.security import Principal, require_org
from app.services.email import invite_url, send_email

router = APIRouter(prefix="/api/team", tags=["team"])


async def require_owner(p: Principal, session: AsyncSession) -> None:
    role = await session.scalar(
        select(Membership.role).where(
            Membership.user_id == p.user_id, Membership.org_id == p.org_id
        )
    )
    if role != Role.owner:
        raise HTTPException(403, "Только владелец может управлять командой")


@router.get("/members", response_model=list[MemberOut])
async def members(
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> list[MemberOut]:
    rows = (
        await session.execute(
            select(User, Membership.role)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.org_id == p.org_id)
            .order_by(User.id)
        )
    ).all()
    return [MemberOut(user_id=u.id, email=u.email, role=r.value) for u, r in rows]


@router.get("/invites", response_model=list[InvitationOut])
async def invites(
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> list[InvitationOut]:
    await require_owner(p, session)
    rows = (
        await session.scalars(
            select(Invitation).where(Invitation.org_id == p.org_id, Invitation.accepted.is_(False))
            .order_by(Invitation.id.desc())
        )
    ).all()
    return [InvitationOut.model_validate(i) for i in rows]


@router.post("/invite", response_model=InvitationOut, status_code=201)
async def invite(
    body: InviteBody, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> InvitationOut:
    await require_owner(p, session)
    email = body.email.lower()
    role = Role(body.role) if body.role in (r.value for r in Role) else Role.editor
    dup = await session.scalar(
        select(Invitation).where(
            Invitation.org_id == p.org_id, Invitation.email == email, Invitation.accepted.is_(False)
        )
    )
    if dup:
        raise HTTPException(409, "Приглашение уже отправлено")
    inv = Invitation(org_id=p.org_id, email=email, role=role)
    session.add(inv)
    await session.commit()
    await send_email(email, "Приглашение в команду — TG Channel Studio",
                     f"Тебя пригласили в организацию. Прими приглашение: {invite_url(inv.token)}")
    return InvitationOut.model_validate(inv)


@router.delete("/invites/{invite_id}", status_code=204)
async def cancel_invite(
    invite_id: int, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> None:
    await require_owner(p, session)
    inv = await session.scalar(
        select(Invitation).where(Invitation.id == invite_id, Invitation.org_id == p.org_id)
    )
    if inv is None:
        raise HTTPException(404, "Invitation not found")
    await session.delete(inv)
    await session.commit()


@router.post("/members/{user_id}/role", response_model=MemberOut)
async def change_role(
    user_id: int, body: RoleBody,
    p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session),
) -> MemberOut:
    await require_owner(p, session)
    if body.role not in (r.value for r in Role):
        raise HTTPException(400, "Invalid role")
    m = await session.scalar(
        select(Membership).where(Membership.user_id == user_id, Membership.org_id == p.org_id)
    )
    if m is None:
        raise HTTPException(404, "Member not found")
    m.role = Role(body.role)
    await session.commit()
    user = await session.get(User, user_id)
    return MemberOut(user_id=user.id, email=user.email, role=m.role.value)


@router.delete("/members/{user_id}", status_code=204)
async def remove_member(
    user_id: int, p: Principal = Depends(require_org), session: AsyncSession = Depends(get_session)
) -> None:
    await require_owner(p, session)
    if user_id == p.user_id:
        raise HTTPException(400, "Нельзя удалить себя")
    m = await session.scalar(
        select(Membership).where(Membership.user_id == user_id, Membership.org_id == p.org_id)
    )
    if m is None:
        raise HTTPException(404, "Member not found")
    await session.delete(m)
    await session.commit()
