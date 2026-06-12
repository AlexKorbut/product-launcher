"""ORM models: channels, donors, raw posts, generated posts, worker logs."""
import enum
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


channel_donors = Table(
    "channel_donors",
    Base.metadata,
    Column("channel_id", ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True),
    Column("donor_id", ForeignKey("donors.id", ondelete="CASCADE"), primary_key=True),
)


class Channel(Base):
    """A Telegram channel we own and publish to (via Bot API)."""

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255), unique=True)  # @channel or -100… chat id
    bot_token_encrypted: Mapped[str] = mapped_column(Text)            # Fernet-encrypted

    # Topic profile — drives the generation prompt
    topic: Mapped[str] = mapped_column(Text, default="")
    tone: Mapped[str] = mapped_column(String(64), default="expert")   # expert | casual | meme | formal
    audience: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(16), default="ru")
    hashtags: Mapped[str] = mapped_column(Text, default="")
    banned_topics: Mapped[str] = mapped_column(Text, default="")
    prompt_template: Mapped[str] = mapped_column(Text, default="")    # optional manual override
    signature: Mapped[str] = mapped_column(Text, default="")          # appended to every post

    # Rewrite behavior: 1 = light rewrite, 2 = deep rewrite, 3 = "inspired by" (new post on topic)
    rewrite_level: Mapped[int] = mapped_column(Integer, default=2)

    # Publishing
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=True)  # False => manual review queue
    posts_per_day: Mapped[int] = mapped_column(Integer, default=4)
    quiet_hours_start: Mapped[int] = mapped_column(Integer, default=23)  # local hour
    quiet_hours_end: Mapped[int] = mapped_column(Integer, default=8)
    tz_offset_minutes: Mapped[int] = mapped_column(Integer, default=180)  # default UTC+3

    status: Mapped[ChannelStatus] = mapped_column(Enum(ChannelStatus), default=ChannelStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    donors: Mapped[list["Donor"]] = relationship(secondary=channel_donors, back_populates="channels")
    posts: Mapped[list["Post"]] = relationship(back_populates="channel", cascade="all, delete-orphan")


class Donor(Base):
    """A public Telegram channel we read via userbot (MTProto)."""

    __tablename__ = "donors"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True)  # @username or t.me link slug
    title: Mapped[str] = mapped_column(String(255), default="")
    poll_interval_min: Mapped[int] = mapped_column(Integer, default=15)
    last_message_id: Mapped[int] = mapped_column(Integer, default=0)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Raw-material filters: {"min_length": 100, "require_media": false,
    #                        "include_keywords": [], "exclude_keywords": [], "skip_ads": true}
    filters: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[DonorStatus] = mapped_column(Enum(DonorStatus), default=DonorStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    channels: Mapped[list[Channel]] = relationship(secondary=channel_donors, back_populates="donors")
    raw_posts: Mapped[list["RawPost"]] = relationship(back_populates="donor", cascade="all, delete-orphan")


class RawPost(Base):
    """Source post scraped from a donor channel."""

    __tablename__ = "raw_posts"
    __table_args__ = (UniqueConstraint("donor_id", "tg_message_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("donors.id", ondelete="CASCADE"))
    tg_message_id: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    media: Mapped[dict] = mapped_column(JSON, default=dict)  # {"type": "photo", "file_ref": ...}
    content_hash: Mapped[str] = mapped_column(String(64), index=True)  # dedup
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[RawPostStatus] = mapped_column(Enum(RawPostStatus), default=RawPostStatus.new)

    donor: Mapped[Donor] = relationship(back_populates="raw_posts")


class Post(Base):
    """Generated post in the publishing pipeline."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
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

    # Anti-plagiarism / cost telemetry
    similarity_to_source: Mapped[float] = mapped_column(Float, default=0.0)
    model: Mapped[str] = mapped_column(String(64), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    channel: Mapped[Channel] = relationship(back_populates="posts")
    raw_post: Mapped[RawPost | None] = relationship()


class WorkerLog(Base):
    """Operational log shared by all workers (visible in the dashboard)."""

    __tablename__ = "worker_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    worker: Mapped[str] = mapped_column(String(32), index=True)   # ingest | generator | publisher
    level: Mapped[str] = mapped_column(String(16), default="info")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
