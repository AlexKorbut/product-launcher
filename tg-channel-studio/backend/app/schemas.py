"""Pydantic request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth ---

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    org_name: str = "Моя организация"
    referral_code: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user_id: int
    email: str
    org_id: int
    org_name: str
    credit_balance: int
    plan: str
    referral_code: str


# --- Channels ---

class ChannelBase(BaseModel):
    name: str
    username: str
    topic: str = ""
    tone: str = "expert"
    audience: str = ""
    language: str = "ru"
    hashtags: str = ""
    banned_topics: str = ""
    prompt_template: str = ""
    signature: str = ""
    rewrite_level: int = Field(2, ge=1, le=3)
    llm_provider: str = ""   # "" => global default; "anthropic" | "openai"
    llm_model: str = ""      # "" => provider default model
    auto_publish: bool = True
    posts_per_day: int = Field(4, ge=1, le=48)
    quiet_hours_start: int = Field(23, ge=0, le=23)
    quiet_hours_end: int = Field(8, ge=0, le=23)
    tz_offset_minutes: int = 180


class ChannelCreate(ChannelBase):
    bot_token: str


class ChannelUpdate(ChannelBase):
    bot_token: str | None = None
    status: str | None = None


class ChannelOut(ChannelBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    created_at: datetime
    subscription_ids: list[int] = []


# --- Donors ---

class DonorBase(BaseModel):
    username: str
    poll_interval_min: int = Field(15, ge=1, le=1440)
    filters: dict = {}


class DonorCreate(DonorBase):
    channel_ids: list[int] = []


class DonorUpdate(DonorBase):
    status: str | None = None
    channel_ids: list[int] | None = None


class DonorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    title: str
    poll_interval_min: int
    filters: dict
    status: str
    last_polled_at: datetime | None
    channel_ids: list[int] = []


# --- Posts ---

class PostUpdate(BaseModel):
    text: str | None = None
    scheduled_at: datetime | None = None


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    channel_id: int
    raw_post_id: int | None
    text: str
    media: dict
    status: str
    scheduled_at: datetime | None
    published_at: datetime | None
    error: str
    similarity_to_source: float
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    credits_charged: int
    created_at: datetime


class GenerateRequest(BaseModel):
    channel_id: int
    raw_post_id: int | None = None


# --- Billing ---

class CheckoutRequest(BaseModel):
    price_id: str


class CheckoutResponse(BaseModel):
    url: str


class BalanceResponse(BaseModel):
    credit_balance: int


class LedgerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    delta: int
    balance_after: int
    kind: str
    ref: str
    created_at: datetime


# --- Dashboard / alerts ---

class ChannelStats(BaseModel):
    channel_id: int
    channel_name: str
    status: str
    queue: int
    published_today: int
    failed: int
    cost_today_usd: float


class DashboardOut(BaseModel):
    channels: list[ChannelStats]
    raw_new: int
    total_published: int
    total_cost_usd: float
    credit_balance: int


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    worker: str
    level: str
    message: str
    created_at: datetime


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    message: str
    is_read: bool
    created_at: datetime
