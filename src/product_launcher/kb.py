"""
Product Knowledge Base — the central data model.
Single source of truth for all agents.
"""
from pydantic import BaseModel, Field
from typing import Optional


class ToneOfVoice(BaseModel):
    primary: str = Field(min_length=1)
    adjectives: list[str] = Field(default_factory=list)
    donts: list[str] = Field(default_factory=list)


class Colors(BaseModel):
    primary: str = Field(min_length=1, pattern=r"^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$")
    secondary: str = Field(min_length=1, pattern=r"^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$")
    accent: str = Field(min_length=1, pattern=r"^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$")


class TargetAudience(BaseModel):
    demographics: str = ""
    pain_points: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)


class ProductInfo(BaseModel):
    name: str = Field(min_length=1)
    tagline: Optional[str] = None
    description: str = ""
    usp: str = ""
    features: list[str] = Field(default_factory=list)
    specs: dict = Field(default_factory=dict)
    price_range: Optional[str] = None
    category: Optional[str] = None


class BrandInfo(BaseModel):
    tone_of_voice: ToneOfVoice
    colors: Colors
    target_audience: TargetAudience


class MarketInfo(BaseModel):
    competitors: list[str] = Field(default_factory=list)
    differentiator: str = ""
    geo_focus: str = ""


class SourceInfo(BaseModel):
    event: str = ""
    location: str = ""
    date: str = ""
    raw_text: str = ""
    images: list[str] = Field(default_factory=list)


class ProductKB(BaseModel):
    """Central knowledge base — all agents read from here."""
    product: ProductInfo
    brand: BrandInfo
    market: MarketInfo = Field(default_factory=MarketInfo)
    source: SourceInfo = Field(default_factory=SourceInfo)
