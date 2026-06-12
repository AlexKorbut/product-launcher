"""ORM models: tenancy (users/orgs), channels, donors, posts, billing, alerts."""
import enum
import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def gen_referral_code() -> str:
    return secrets.token_urlsafe(6)


# --- Enums ---

class Role(str, enum.Enum):
    owner = "owner"
    editor = "editor"


class ChannelStatus(str, enum.Enum):
    active = "active"
    paused = "paused"


class DonorStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    unavailable = "unavailable"


class RawPostStatus(str, enum.Enum):
    new = "new"
    processed = "processed"
    skipped = "skipped"


class PostStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    approved = "approved"
    scheduled = "scheduled"
    published = "published"
    failed = "failed"
    rejected = "rejected"


class LedgerKind(str, enum.Enum):
    purchase = "purchase"
    debit = "debit"
    bonus = "bonus"
    refund = "refund"
    referral = "referral"


class AlertKind(str, enum.Enum):
    donor_unavailable = "donor_unavailable"
    bot_no_rights = "bot_no_rights"
    out_of_credits = "out_of_credits"
    publish_failed = "publish_failed"


# --- Tenancy ---

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    credit_balance: Mapped[int] = mapped_column(Integer, default=0)
    plan: Mapped[str] = mapped_column(String(32), default="free")
    referral_code: Mapped[str] = mapped_column(String(32), unique=True, default=gen_referral_code)
    referred_by_org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "org_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.owner)

    user: Mapped[User] = relationship(back_populates="memberships")


# --- Billing ---

class CreditLedger(Base):
    """Append-only ledger of every credit movement (audit trail)."""

    __tablename__ = "credit_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    delta: Mapped[int] = mapped_column(Integer)  # +grant / -debit
    balance_after: Mapped[int] = mapped_column(Integer)
    kind: Mapped[LedgerKind] = mapped_column(Enum(LedgerKind))
    ref: Mapped[str] = mapped_column(String(128), default="")  # post id / stripe event / referral
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class StripeEvent(Base):
    """Processed Stripe webhook events — idempotency guard."""

    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # evt_...
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --- Channels ---

channel_subscriptions = Table(
    "channel_subscriptions",
    Base.metadata,
    Column("channel_id", ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True),
    Column("subscription_id", ForeignKey("donor_subscriptions.id", ondelete="CASCADE"), primary_key=True),
)


class Channel(Base):
    """A Telegram channel an org owns and publishes to (via Bot API)."""

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255))
    bot_token_encrypted: Mapped[str] = mapped_column(Text)

    topic: Mapped[str] = mapped_column(Text, default="")
    tone: Mapped[str] = mapped_column(String(64), default="expert")
    audience: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(16), default="ru")
    hashtags: Mapped[str] = mapped_column(Text, default="")
    banned_topics: Mapped[str] = mapped_column(Text, default="")
    prompt_template: Mapped[str] = mapped_column(Text, default="")
    signature: Mapped[str] = mapped_column(Text, default="")

    rewrite_level: Mapped[int] = mapped_column(Integer, default=2)  # 1 light, 2 deep, 3 inspired

    # Per-channel LLM override; empty => use global defaults (LLM_PROVIDER / model).
    llm_provider: Mapped[str] = mapped_column(String(32), default="")  # "" | anthropic | openai
    llm_model: Mapped[str] = mapped_column(String(64), default="")

    auto_publish: Mapped[bool] = mapped_column(Boolean, default=True)
    posts_per_day: Mapped[int] = mapped_column(Integer, default=4)
    quiet_hours_start: Mapped[int] = mapped_column(Integer, default=23)
    quiet_hours_end: Mapped[int] = mapped_column(Integer, default=8)
    tz_offset_minutes: Mapped[int] = mapped_column(Integer, default=180)

    status: Mapped[ChannelStatus] = mapped_column(Enum(ChannelStatus), default=ChannelStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    subscriptions: Mapped[list["DonorSubscription"]] = relationship(
        secondary=channel_subscriptions, back_populates="channels"
    )
    posts: Mapped[list["Post"]] = relationship(back_populates="channel", cascade="all, delete-orphan")


# --- Donors (shared source + per-org subscription) ---

class DonorSource(Base):
    """A public Telegram channel, scraped ONCE for all tenants."""

    __tablename__ = "donor_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    last_message_id: Mapped[int] = mapped_column(Integer, default=0)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[DonorStatus] = mapped_column(Enum(DonorStatus), default=DonorStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    raw_posts: Mapped[list["RawPost"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class DonorSubscription(Base):
    """An org subscribing to a DonorSource, with its own filters and target channels."""

    __tablename__ = "donor_subscriptions"
    __table_args__ = (UniqueConstraint("org_id", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("donor_sources.id", ondelete="CASCADE"))
    poll_interval_min: Mapped[int] = mapped_column(Integer, default=15)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[DonorStatus] = mapped_column(Enum(DonorStatus), default=DonorStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source: Mapped[DonorSource] = relationship()
    channels: Mapped[list[Channel]] = relationship(
        secondary=channel_subscriptions, back_populates="subscriptions"
    )


class RawPost(Base):
    """Source post scraped from a donor source (shared across tenants)."""

    __tablename__ = "raw_posts"
    __table_args__ = (UniqueConstraint("source_id", "tg_message_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("donor_sources.id", ondelete="CASCADE"))
    tg_message_id: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    media: Mapped[dict] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    fanned_out: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    source: Mapped[DonorSource] = relationship(back_populates="raw_posts")


class Post(Base):
    """Generated post in an org's publishing pipeline."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"))
    raw_post_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_posts.id", ondelete="SET NULL"), nullable=True
    )

    text: Mapped[str] = mapped_column(Text)
    media: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[PostStatus] = mapped_column(Enum(PostStatus), default=PostStatus.draft, index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tg_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    retries: Mapped[int] = mapped_column(Integer, default=0)

    similarity_to_source: Mapped[float] = mapped_column(Float, default=0.0)
    model: Mapped[str] = mapped_column(String(64), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    credits_charged: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    channel: Mapped[Channel] = relationship(back_populates="posts")
    raw_post: Mapped[RawPost | None] = relationship()


class WorkerLog(Base):
    __tablename__ = "worker_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    worker: Mapped[str] = mapped_column(String(32), index=True)
    level: Mapped[str] = mapped_column(String(16), default="info")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Invitation(Base):
    """Pending invite of a user (by email) to join an organization."""

    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.editor)
    token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: secrets.token_urlsafe(24))
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(Base):
    """Actionable notification surfaced in the dashboard."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    kind: Mapped[AlertKind] = mapped_column(Enum(AlertKind))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
