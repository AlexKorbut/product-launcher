"""SQLAlchemy 2.0 ORM schema. Guarded so import never fails without sqlalchemy."""

from __future__ import annotations

from datetime import datetime, timezone

try:
    from sqlalchemy import (
        Boolean,
        DateTime,
        Float,
        ForeignKey,
        Integer,
        String,
        Text,
    )
    from sqlalchemy import JSON as SA_JSON
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

    _SA = True
except ImportError:
    _SA = False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _vector_type():
    """pgvector Vector(1024) when available, else JSON (SQLite-friendly)."""
    from .engine import HAS_PGVECTOR

    if HAS_PGVECTOR:
        from pgvector.sqlalchemy import Vector

        return Vector(1024)
    return SA_JSON


if _SA:

    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "users"

        id: Mapped[str] = mapped_column(String, primary_key=True)
        output_lang: Mapped[str] = mapped_column(String, default="ru")
        tz: Mapped[str] = mapped_column(String, default="UTC")
        default_theme: Mapped[str] = mapped_column(String, default="times-classic")
        created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

        source_accounts: Mapped[list["SourceAccount"]] = relationship(
            back_populates="user", cascade="all, delete-orphan"
        )

    class SourceAccount(Base):
        """Per-user per-source config + incremental cursor."""

        __tablename__ = "source_accounts"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
        source_id: Mapped[str] = mapped_column(String)
        enabled: Mapped[bool] = mapped_column(Boolean, default=True)
        options: Mapped[dict] = mapped_column(SA_JSON, default=dict)
        secret_ref: Mapped[str | None] = mapped_column(String, nullable=True)
        cursor: Mapped[str | None] = mapped_column(String, nullable=True)
        status: Mapped[str] = mapped_column(String, default="ok")
        updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

        user: Mapped["User"] = relationship(back_populates="source_accounts")

    class SignalRow(Base):
        __tablename__ = "signals"

        id: Mapped[str] = mapped_column(String, primary_key=True)
        user_id: Mapped[str] = mapped_column(String)
        source_id: Mapped[str] = mapped_column(String)
        kind: Mapped[str] = mapped_column(String)
        text: Mapped[str] = mapped_column(Text, default="")
        lang: Mapped[str | None] = mapped_column(String, nullable=True)
        strength: Mapped[float] = mapped_column(Float, default=0.5)
        entities_hint: Mapped[list] = mapped_column(SA_JSON, default=list)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
        is_private: Mapped[bool] = mapped_column(Boolean, default=False)
        raw_ref: Mapped[str | None] = mapped_column(String, nullable=True)

    class InterestProfileRow(Base):
        __tablename__ = "interest_profiles"

        user_id: Mapped[str] = mapped_column(String, primary_key=True)
        output_lang: Mapped[str] = mapped_column(String, default="ru")
        topics: Mapped[dict] = mapped_column(SA_JSON, default=dict)
        entities: Mapped[dict] = mapped_column(SA_JSON, default=dict)
        updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
        version: Mapped[int] = mapped_column(Integer, default=1)

    class InterestVectorRow(Base):
        __tablename__ = "interest_vectors"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        user_id: Mapped[str] = mapped_column(String, ForeignKey("interest_profiles.user_id"))
        vector = mapped_column(_vector_type())
        created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    class IssueRow(Base):
        __tablename__ = "issues"

        id: Mapped[str] = mapped_column(String, primary_key=True)
        user_id: Mapped[str] = mapped_column(String)
        theme_id: Mapped[str] = mapped_column(String)
        status: Mapped[str] = mapped_column(String)
        pdf_key: Mapped[str | None] = mapped_column(String, nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    class UsageEventRow(Base):
        __tablename__ = "usage_events"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        user_id: Mapped[str] = mapped_column(String(128), index=True)
        issue_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
        stage: Mapped[str] = mapped_column(String(32))
        model: Mapped[str] = mapped_column(String(64))
        tokens_in: Mapped[int] = mapped_column(Integer, default=0)
        tokens_out: Mapped[int] = mapped_column(Integer, default=0)
        cached_in: Mapped[int] = mapped_column(Integer, default=0)
        batch: Mapped[bool] = mapped_column(Boolean, default=False)
        cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

else:  # sqlalchemy not installed
    Base = None  # type: ignore[assignment]
    User = SourceAccount = SignalRow = None  # type: ignore[assignment]
    InterestProfileRow = InterestVectorRow = IssueRow = None  # type: ignore[assignment]
    UsageEventRow = None  # type: ignore[assignment]


def require_sqlalchemy() -> None:
    if not _SA:
        raise ImportError(
            "SQLAlchemy is required for the database layer. "
            "Install it with `pip install sqlalchemy` (and pgvector/psycopg for Postgres)."
        )


def create_all(engine) -> None:
    require_sqlalchemy()
    Base.metadata.create_all(engine)
