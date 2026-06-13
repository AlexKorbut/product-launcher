"""Thin façade between pydantic models and ORM rows."""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import InterestProfile, Signal


def _engine(url=None, engine=None):
    from .engine import get_engine

    return engine if engine is not None else get_engine(url)


def init_db(engine=None, *, url=None) -> None:
    """Create all tables (dev convenience; use Alembic in prod)."""
    from .schema import create_all

    create_all(_engine(url, engine))


def upsert_user(
    user_id: str,
    *,
    tz: str = "UTC",
    output_lang: str = "ru",
    default_theme: str = "times-classic",
    url=None,
    engine=None,
) -> None:
    from .engine import get_session
    from .schema import User

    with get_session(engine=_engine(url, engine)) as s:
        row = s.get(User, user_id)
        if row is None:
            s.add(
                User(
                    id=user_id,
                    tz=tz,
                    output_lang=output_lang,
                    default_theme=default_theme,
                )
            )
        else:
            row.tz = tz
            row.output_lang = output_lang
            row.default_theme = default_theme
        s.commit()


def get_source_accounts(user_id: str, *, url=None, engine=None) -> list[dict]:
    from sqlalchemy import select

    from .engine import get_session
    from .schema import SourceAccount

    with get_session(engine=_engine(url, engine)) as s:
        rows = s.scalars(
            select(SourceAccount).where(SourceAccount.user_id == user_id)
        ).all()
        return [
            {
                "source_id": r.source_id,
                "enabled": r.enabled,
                "options": r.options or {},
                "secret_ref": r.secret_ref,
                "cursor": r.cursor,
                "status": r.status,
            }
            for r in rows
        ]


def upsert_source_account(
    user_id: str,
    source_id: str,
    *,
    options: dict,
    enabled: bool = True,
    secret_ref: str | None = None,
    url=None,
    engine=None,
) -> None:
    from sqlalchemy import select

    from .engine import get_session
    from .schema import SourceAccount

    with get_session(engine=_engine(url, engine)) as s:
        row = s.scalars(
            select(SourceAccount).where(
                SourceAccount.user_id == user_id,
                SourceAccount.source_id == source_id,
            )
        ).first()
        if row is None:
            s.add(
                SourceAccount(
                    user_id=user_id,
                    source_id=source_id,
                    options=options,
                    enabled=enabled,
                    secret_ref=secret_ref,
                )
            )
        else:
            row.options = options
            row.enabled = enabled
            row.secret_ref = secret_ref
        s.commit()


def update_cursor(
    user_id: str, source_id: str, cursor: str | None, *, url=None, engine=None
) -> None:
    from sqlalchemy import select

    from .engine import get_session
    from .schema import SourceAccount

    with get_session(engine=_engine(url, engine)) as s:
        row = s.scalars(
            select(SourceAccount).where(
                SourceAccount.user_id == user_id,
                SourceAccount.source_id == source_id,
            )
        ).first()
        if row is not None:
            row.cursor = cursor
            s.commit()


def save_signals(signals: list[Signal], *, url=None, engine=None) -> int:
    """Insert-or-ignore by id. Private signals are persisted with blanked text."""
    from .engine import get_session
    from .schema import SignalRow

    inserted = 0
    with get_session(engine=_engine(url, engine)) as s:
        for sig in signals:
            if s.get(SignalRow, sig.id) is not None:
                continue
            text = "" if sig.is_private else sig.text
            s.add(
                SignalRow(
                    id=sig.id,
                    user_id=sig.user_id,
                    source_id=sig.source_id,
                    kind=sig.kind.value if hasattr(sig.kind, "value") else str(sig.kind),
                    text=text,
                    lang=sig.lang,
                    strength=sig.strength,
                    entities_hint=list(sig.entities_hint),
                    created_at=sig.created_at,
                    is_private=sig.is_private,
                    raw_ref=sig.raw_ref,
                )
            )
            inserted += 1
        s.commit()
    return inserted


def save_profile(profile: InterestProfile, *, url=None, engine=None) -> None:
    """Upsert the profile row and replace its interest_vectors."""
    from sqlalchemy import delete

    from .engine import get_session
    from .schema import InterestProfileRow, InterestVectorRow

    with get_session(engine=_engine(url, engine)) as s:
        row = s.get(InterestProfileRow, profile.user_id)
        if row is None:
            s.add(
                InterestProfileRow(
                    user_id=profile.user_id,
                    output_lang=profile.output_lang,
                    topics=dict(profile.topics),
                    entities=dict(profile.entities),
                    updated_at=profile.updated_at,
                    version=profile.version,
                )
            )
        else:
            row.output_lang = profile.output_lang
            row.topics = dict(profile.topics)
            row.entities = dict(profile.entities)
            row.updated_at = profile.updated_at
            row.version = profile.version

        s.execute(
            delete(InterestVectorRow).where(InterestVectorRow.user_id == profile.user_id)
        )
        for vec in profile.interest_vectors:
            s.add(InterestVectorRow(user_id=profile.user_id, vector=list(vec)))
        s.commit()


def load_profile(user_id: str, *, url=None, engine=None) -> InterestProfile | None:
    from sqlalchemy import select

    from .engine import get_session
    from .schema import InterestProfileRow, InterestVectorRow

    with get_session(engine=_engine(url, engine)) as s:
        row = s.get(InterestProfileRow, user_id)
        if row is None:
            return None
        vecs = s.scalars(
            select(InterestVectorRow)
            .where(InterestVectorRow.user_id == user_id)
            .order_by(InterestVectorRow.id)
        ).all()
        vectors = [list(v.vector) for v in vecs if v.vector is not None]
        return InterestProfile(
            user_id=row.user_id,
            output_lang=row.output_lang,
            topics=dict(row.topics or {}),
            entities=dict(row.entities or {}),
            interest_vectors=vectors,
            updated_at=row.updated_at or datetime.now(timezone.utc),
            version=row.version,
        )


def record_issue(
    issue_id: str,
    user_id: str,
    theme_id: str,
    *,
    status: str,
    pdf_key: str | None = None,
    url=None,
    engine=None,
) -> None:
    from .engine import get_session
    from .schema import IssueRow

    with get_session(engine=_engine(url, engine)) as s:
        row = s.get(IssueRow, issue_id)
        if row is None:
            s.add(
                IssueRow(
                    id=issue_id,
                    user_id=user_id,
                    theme_id=theme_id,
                    status=status,
                    pdf_key=pdf_key,
                )
            )
        else:
            row.status = status
            row.pdf_key = pdf_key
        s.commit()


def record_usage(
    *,
    user_id: str,
    issue_id: str | None,
    stage: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cached_in: int = 0,
    batch: bool = False,
    cost_usd: float,
    url=None,
    engine=None,
) -> None:
    """Insert one usage event row."""
    from .engine import get_session
    from .schema import UsageEventRow

    with get_session(engine=_engine(url, engine)) as s:
        s.add(
            UsageEventRow(
                user_id=user_id,
                issue_id=issue_id,
                stage=stage,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cached_in=cached_in,
                batch=batch,
                cost_usd=cost_usd,
            )
        )
        s.commit()


def issue_cost(issue_id: str, *, url=None, engine=None) -> dict:
    """Sum cost/tokens for one issue, plus a per-(stage,model) breakdown."""
    from sqlalchemy import select

    from .engine import get_session
    from .schema import UsageEventRow

    with get_session(engine=_engine(url, engine)) as s:
        rows = s.scalars(
            select(UsageEventRow).where(UsageEventRow.issue_id == issue_id)
        ).all()

    cost = sum(r.cost_usd or 0.0 for r in rows)
    tin = sum(r.tokens_in or 0 for r in rows)
    tout = sum(r.tokens_out or 0 for r in rows)
    agg: dict[tuple[str, str], dict] = {}
    for r in rows:
        key = (r.stage, r.model)
        e = agg.setdefault(
            key,
            {"stage": r.stage, "model": r.model, "cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0},
        )
        e["cost_usd"] += r.cost_usd or 0.0
        e["tokens_in"] += r.tokens_in or 0
        e["tokens_out"] += r.tokens_out or 0
    return {
        "cost_usd": cost,
        "tokens_in": tin,
        "tokens_out": tout,
        "events": list(agg.values()),
    }


def user_usage(user_id: str, *, since=None, url=None, engine=None) -> dict:
    """Aggregate cost/tokens for a user (optionally created_at >= since)."""
    from sqlalchemy import select

    from .engine import get_session
    from .schema import UsageEventRow

    with get_session(engine=_engine(url, engine)) as s:
        stmt = select(UsageEventRow).where(UsageEventRow.user_id == user_id)
        if since is not None:
            stmt = stmt.where(UsageEventRow.created_at >= since)
        rows = s.scalars(stmt).all()

    cost = sum(r.cost_usd or 0.0 for r in rows)
    tin = sum(r.tokens_in or 0 for r in rows)
    tout = sum(r.tokens_out or 0 for r in rows)
    issues = {r.issue_id for r in rows if r.issue_id is not None}
    return {
        "cost_usd": cost,
        "tokens_in": tin,
        "tokens_out": tout,
        "issues": len(issues),
    }
