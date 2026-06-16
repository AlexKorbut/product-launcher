"""Source catalog + per-user source configuration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from ... import accounts
from ...sources import registry
from ..deps import Principal, get_principal, require_owner
from ..schemas import SourceAccountIn, SourceAccountOut, SourceInfo, redact_options

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=list[SourceInfo])
def list_sources() -> list[SourceInfo]:
    out: list[SourceInfo] = []
    for cls in registry.all_sources():
        out.append(
            SourceInfo(
                source_id=cls.source_id,
                display_name=cls.display_name,
                requires_auth=cls.requires_auth,
                config_schema=cls.config_schema.model_json_schema(),
            )
        )
    return out


def _account_out(sa: accounts.SourceAccount) -> SourceAccountOut:
    return SourceAccountOut(
        source_id=sa.source_id,
        enabled=sa.enabled,
        status=sa.status,
        options=redact_options(sa.options),
    )


@router.get("/users/{user_id}/sources/{source_id}", response_model=SourceAccountOut)
def get_user_source(
    user_id: str, source_id: str, principal: Principal = Depends(get_principal)
) -> SourceAccountOut:
    require_owner(principal, user_id)
    sa = accounts.load(user_id).sources.get(source_id)
    if sa is None:
        raise HTTPException(404, f"source {source_id!r} not configured")
    return _account_out(sa)


@router.put("/users/{user_id}/sources/{source_id}", response_model=SourceAccountOut)
def put_user_source(
    user_id: str,
    source_id: str,
    body: SourceAccountIn,
    principal: Principal = Depends(get_principal),
) -> SourceAccountOut:
    require_owner(principal, user_id)
    # `get_source` raises KeyError for unknown ids -> 404 via app handler.
    source = registry.get_source(source_id)
    try:
        source.config_schema.model_validate(body.options)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors())

    acc = accounts.set_source(user_id, source_id, options=body.options, enabled=body.enabled)
    return _account_out(acc.sources[source_id])
