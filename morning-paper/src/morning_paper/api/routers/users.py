"""User preferences (output language, theme, timezone, delivery channel)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ... import accounts
from ..deps import Principal, get_principal, require_owner
from ..schemas import UserOut, UserUpdate

router = APIRouter(tags=["users"])


def _to_out(acc: accounts.UserAccounts) -> UserOut:
    return UserOut(
        user_id=acc.user_id,
        output_lang=acc.output_lang,
        theme=acc.theme,
        tz=acc.tz,
        deliver_channel=acc.deliver_channel,
    )


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: str, principal: Principal = Depends(get_principal)) -> UserOut:
    require_owner(principal, user_id)
    return _to_out(accounts.load(user_id))


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: str, body: UserUpdate, principal: Principal = Depends(get_principal)
) -> UserOut:
    require_owner(principal, user_id)
    acc = accounts.load(user_id)
    if body.output_lang is not None:
        acc.output_lang = body.output_lang
    if body.theme is not None:
        acc.theme = body.theme
    if body.tz is not None:
        acc.tz = body.tz
    if body.deliver_channel is not None:
        acc.deliver_channel = body.deliver_channel
    accounts.save(acc)

    try:  # best-effort mirror into the DB
        from ...db.repository import upsert_user

        upsert_user(
            user_id, tz=acc.tz, output_lang=acc.output_lang, default_theme=acc.theme
        )
    except Exception:
        pass

    return _to_out(acc)
