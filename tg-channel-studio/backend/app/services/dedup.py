"""Raw-post deduplication and ad filtering."""
import hashlib
import re

AD_MARKERS = re.compile(
    r"(#реклама|#ad\b|erid[:=]|реклама\.|на правах рекламы|промокод|partner post)",
    re.IGNORECASE,
)
LINK_OR_MENTION = re.compile(r"(t\.me/|@[a-zA-Z]\w{3,})")


def normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", text.lower()).strip()
    text = re.sub(r"[^\w\s]", "", text)
    return text


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def looks_like_ad(text: str) -> bool:
    return bool(AD_MARKERS.search(text))


def passes_filters(text: str, media: dict, filters: dict) -> tuple[bool, str]:
    """Apply per-donor filters; returns (ok, reason)."""
    min_length = int(filters.get("min_length", 0))
    if len(text) < min_length:
        return False, f"shorter than {min_length} chars"

    if filters.get("require_media") and not media:
        return False, "no media"

    if filters.get("skip_ads", True) and looks_like_ad(text):
        return False, "looks like an ad"

    include = [k.lower() for k in filters.get("include_keywords", []) if k]
    if include and not any(k in text.lower() for k in include):
        return False, "no include keyword matched"

    exclude = [k.lower() for k in filters.get("exclude_keywords", []) if k]
    hit = next((k for k in exclude if k in text.lower()), None)
    if hit:
        return False, f"exclude keyword: {hit}"

    return True, ""
