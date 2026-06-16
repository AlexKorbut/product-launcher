#!/usr/bin/env python3
"""Fetch OFL-licensed woff2 fonts for the Morning Paper themes.

Each theme under ``themes/<id>/`` declares ``[[fonts]]`` blocks in its
``theme.toml`` listing a ``family`` and the ``files`` (relative woff2 paths)
the renderer expects in ``themes/<id>/fonts/``. The binary woff2 files are not
committed; this script downloads them on demand from the
google-webfonts-helper API (https://gwfh.mranftl.com), which serves the same
OFL-1.1 fonts that Google Fonts hosts, in ready-to-use woff2 form.

Usage::

    python scripts/fetch_fonts.py                 # fetch all themes
    python scripts/fetch_fonts.py --theme vintage # one theme only
    python scripts/fetch_fonts.py --force         # re-download existing files

Run from anywhere; paths are resolved relative to this script. The script is
idempotent (skips files that already exist), tolerant of individual font
failures, and prints a summary at the end with manual download links for any
files it could not fetch.

All fonts referenced by the themes are licensed under the SIL Open Font
License 1.1 (OFL-1.1) and are freely redistributable.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

import httpx

GWFH_API = "https://gwfh.mranftl.com/api/fonts"
GOOGLE_SPECIMEN = "https://fonts.google.com/specimen"

# Themes that need Cyrillic glyphs; their fonts are requested with the
# cyrillic subset in addition to the Latin subsets.
CYRILLIC_THEMES = {"old-russian"}

DEFAULT_SUBSETS = ["latin", "latin-ext"]
CYRILLIC_SUBSETS = ["latin", "latin-ext", "cyrillic"]

# Map the trailing token of a woff2 filename (e.g. "Bold" from
# "EBGaramond-Bold.woff2") to a google-webfonts-helper variant id.
STYLE_TO_VARIANT = {
    "Regular": "regular",
    "Italic": "italic",
    "Bold": "700",
    "BoldItalic": "700italic",
    "Medium": "500",
    "MediumItalic": "500italic",
    "SemiBold": "600",
    "Light": "300",
    "Thin": "100",
}

# Map the "base" portion of a woff2 filename (everything before the final
# "-<Style>") to (gwfh font-id, Google Fonts specimen slug). The font-id is the
# family name lowercased with spaces as hyphens; the specimen slug uses '+'.
FONT_BASE_TO_SOURCE = {
    "UnifrakturCook": ("unifrakturcook", "UnifrakturCook"),
    "EBGaramond": ("eb-garamond", "EB+Garamond"),
    "Archivo": ("archivo", "Archivo"),
    "SourceSerif4": ("source-serif-4", "Source+Serif+4"),
    "PlayfairDisplay": ("playfair-display", "Playfair+Display"),
    "PlayfairDisplaySC": ("playfair-display-sc", "Playfair+Display+SC"),
    "PTSerif": ("pt-serif", "PT+Serif"),
    "SpaceMono": ("space-mono", "Space+Mono"),
    "SpaceGrotesk": ("space-grotesk", "Space+Grotesk"),
    "IBMPlexSans": ("ibm-plex-sans", "IBM+Plex+Sans"),
    "CormorantGaramond": ("cormorant-garamond", "Cormorant+Garamond"),
    "Vollkorn": ("vollkorn", "Vollkorn"),
    "LibreBaskerville": ("libre-baskerville", "Libre+Baskerville"),
    "CinzelDecorative": ("cinzel-decorative", "Cinzel+Decorative"),
    "Cinzel": ("cinzel", "Cinzel"),
    "IMFellEnglish": ("im-fell-english", "IM+Fell+English"),
    "DMSans": ("dm-sans", "DM+Sans"),
    "DMSerifText": ("dm-serif-text", "DM+Serif+Text"),
}


class ResolveError(Exception):
    """Raised when a filename cannot be mapped to a font source."""


def parse_filename(filename: str) -> tuple[str, str]:
    """Split a woff2 filename into its (base, style) parts.

    e.g. ``EBGaramond-Bold.woff2`` -> ``("EBGaramond", "Bold")``.
    """
    stem = Path(filename).name
    if stem.endswith(".woff2"):
        stem = stem[: -len(".woff2")]
    if "-" not in stem:
        raise ResolveError(f"cannot parse style from {filename!r} (no '-')")
    base, style = stem.rsplit("-", 1)
    return base, style


def resolve_source(filename: str, theme_id: str) -> tuple[str, str, list[str], str]:
    """Resolve a woff2 filename to (font_id, variant, subsets, specimen_slug)."""
    base, style = parse_filename(filename)
    if base not in FONT_BASE_TO_SOURCE:
        raise ResolveError(f"no font source mapping for base {base!r} ({filename})")
    font_id, specimen = FONT_BASE_TO_SOURCE[base]
    if style not in STYLE_TO_VARIANT:
        raise ResolveError(f"no variant mapping for style {style!r} ({filename})")
    variant = STYLE_TO_VARIANT[style]
    subsets = CYRILLIC_SUBSETS if theme_id in CYRILLIC_THEMES else DEFAULT_SUBSETS
    return font_id, variant, subsets, specimen


def specimen_url(filename: str) -> str:
    """Best-effort Google Fonts specimen URL for a filename (manual fallback)."""
    try:
        base, _ = parse_filename(filename)
        _, slug = FONT_BASE_TO_SOURCE[base]
        return f"{GOOGLE_SPECIMEN}/{slug}"
    except (ResolveError, KeyError):
        return GOOGLE_SPECIMEN


def fetch_font_metadata(
    client: httpx.Client, font_id: str, subsets: list[str]
) -> list[dict]:
    """Query the gwfh JSON API and return the list of variant dicts.

    Raises httpx.HTTPStatusError on non-2xx (e.g. 404 unknown font-id).
    """
    url = f"{GWFH_API}/{font_id}"
    resp = client.get(url, params={"subsets": ",".join(subsets)})
    resp.raise_for_status()
    data = resp.json()
    return data.get("variants", [])


def select_variant(variants: list[dict], wanted: str) -> tuple[dict, str | None]:
    """Pick the variant matching ``wanted``; fall back to the closest one.

    Returns (variant_dict, note). ``note`` is None for an exact match, else a
    human-readable description of the fallback that was used.
    """
    by_id = {v.get("id"): v for v in variants}
    if wanted in by_id:
        return by_id[wanted], None

    # Fallback ladder: try sensible alternatives before giving up.
    fallbacks: list[str] = []
    if wanted == "regular":
        fallbacks = ["400", "500", "300"]
    elif wanted.endswith("italic"):
        # e.g. 700italic -> italic -> regular
        fallbacks = ["italic", "400italic", "regular"]
    elif wanted == "700":
        fallbacks = ["800", "600", "500", "regular"]
    elif wanted == "500":
        fallbacks = ["600", "400", "regular", "700"]
    else:
        fallbacks = ["regular", "400"]

    for candidate in fallbacks:
        if candidate in by_id:
            return by_id[candidate], f"variant {wanted!r} unavailable; used {candidate!r}"

    # Last resort: any variant at all.
    if variants:
        chosen = variants[0]
        return chosen, f"variant {wanted!r} unavailable; used {chosen.get('id')!r}"

    raise ResolveError(f"no variants available (wanted {wanted!r})")


def download_font_file(
    client: httpx.Client,
    filename: str,
    theme_id: str,
    dest: Path,
) -> str | None:
    """Download a single woff2 file to ``dest``.

    Returns an optional note (fallback message) on success; raises on failure.
    """
    font_id, variant, subsets, _specimen = resolve_source(filename, theme_id)
    variants = fetch_font_metadata(client, font_id, subsets)
    chosen, note = select_variant(variants, variant)

    woff2_url = chosen.get("woff2")
    if not woff2_url:
        raise ResolveError(f"variant {chosen.get('id')!r} has no woff2 url")

    resp = client.get(woff2_url)
    resp.raise_for_status()
    content = resp.content
    if not content:
        raise ResolveError("downloaded woff2 was empty")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return note


def iter_theme_files(theme_dir: Path) -> list[str]:
    """Read a theme's theme.toml and collect all declared font ``files``."""
    toml_path = theme_dir / "theme.toml"
    if not toml_path.exists():
        return []
    with toml_path.open("rb") as fh:
        data = tomllib.load(fh)
    files: list[str] = []
    for block in data.get("fonts", []):
        files.extend(block.get("files", []))
    return files


def discover_themes(themes_root: Path) -> list[Path]:
    """Return theme directories (those containing a theme.toml), sorted."""
    out = []
    for child in sorted(themes_root.iterdir()):
        if child.is_dir() and (child / "theme.toml").exists():
            out.append(child)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download OFL woff2 fonts for Morning Paper themes."
    )
    parser.add_argument(
        "--theme",
        help="Limit to a single theme id (e.g. vintage). Default: all themes.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download files even if they already exist.",
    )
    args = parser.parse_args(argv)

    themes_root = Path(__file__).resolve().parents[1] / "themes"
    if not themes_root.is_dir():
        print(f"error: themes directory not found at {themes_root}", file=sys.stderr)
        return 2

    theme_dirs = discover_themes(themes_root)
    if args.theme:
        theme_dirs = [d for d in theme_dirs if d.name == args.theme]
        if not theme_dirs:
            print(f"error: no theme named {args.theme!r} under {themes_root}", file=sys.stderr)
            return 2

    downloaded = 0
    skipped = 0
    failed: list[tuple[str, str]] = []  # (rel_path, specimen_url)

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for theme_dir in theme_dirs:
            theme_id = theme_dir.name
            files = iter_theme_files(theme_dir)
            if not files:
                continue
            print(f"\n[{theme_id}] {len(files)} font file(s) declared")
            for rel in files:
                dest = theme_dir / rel
                label = f"{theme_id}/{rel}"
                if dest.exists() and not args.force:
                    print(f"  skip    {label} (already present)")
                    skipped += 1
                    continue
                try:
                    note = download_font_file(client, Path(rel).name, theme_id, dest)
                    size = dest.stat().st_size
                    suffix = f"  [{note}]" if note else ""
                    print(f"  ok      {label} ({size:,} bytes){suffix}")
                    downloaded += 1
                except Exception as exc:  # noqa: BLE001 - tolerate per-file errors
                    print(f"  WARN    {label}: {exc}", file=sys.stderr)
                    failed.append((label, specimen_url(Path(rel).name)))

    print("\n" + "=" * 60)
    print(f"Summary: {downloaded} downloaded, {skipped} skipped, {len(failed)} failed")
    if failed:
        print("\nFailed files — download manually from Google Fonts (OFL-1.1):")
        for label, url in failed:
            print(f"  {label}\n      {url}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
