"""Request dependencies: principal resolution, store handle, ownership checks.

Today this is a FIRST-PARTY API: the caller is trusted and identified by a
simple header. The seams for a public B2B API (API keys, plans, quotas, scopes)
are marked `FUTURE:` so they can be filled in without reshaping the routers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Header


@dataclass
class Principal:
    """The authenticated caller. For now, always an internal first-party user."""

    subject: str
    plan: str = "internal"
    scopes: tuple[str, ...] = field(default_factory=lambda: ("*",))


def get_principal(
    x_mp_user: str | None = Header(default=None, alias="X-MP-User"),
) -> Principal:
    """Resolve the calling principal.

    First-party today: trust the X-MP-User header (defaulting to "me").

    FUTURE (public B2B API): replace this with an API-key lookup —
        - read an `Authorization: Bearer <key>` / `X-API-Key` header,
        - look the key up in an `api_keys` table (hashed) -> {subject, plan, scopes},
        - reject unknown/revoked keys with 401,
        - enforce per-key quota by checking `user_usage` for the billing window
          and raising 429 when the plan's limit is exceeded.
      None of that key store is built here.
    """
    return Principal(subject=x_mp_user or "me")


def get_store():
    """The configured object store (local fs or S3)."""
    from ..store import get_object_store

    return get_object_store()


def require_owner(principal: Principal, user_id: str) -> None:
    """Authorize the principal to act on `user_id`'s resources.

    Permissive today (first-party trusts itself).

    FUTURE: when scopes are real, deny (403) unless the principal owns
    `user_id` or holds an admin/cross-tenant scope, e.g.::

        if "*" not in principal.scopes and principal.subject != user_id:
            raise HTTPException(403, "forbidden")
    """
    return None
