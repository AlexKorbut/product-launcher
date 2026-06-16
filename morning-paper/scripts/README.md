# scripts

Helper scripts for the Morning Paper project.

## `fetch_fonts.py` — font fetcher

The 8 themes under `themes/<id>/` reference OFL-licensed `.woff2` fonts in
`themes/<id>/fonts/`, but the binary font files are not committed to the repo.
`fetch_fonts.py` downloads them on demand so the renderer produces
fully-styled PDFs (instead of falling back to system font stacks).

For each theme it reads `theme.toml`, collects every `[[fonts]]` `files`
entry, and downloads any that are missing into the theme's `fonts/` directory.

### Usage

Run from the `morning-paper/` directory:

```bash
python scripts/fetch_fonts.py            # fetch fonts for all 8 themes
python scripts/fetch_fonts.py --theme vintage   # one theme only
python scripts/fetch_fonts.py --force    # re-download even if files exist
```

The script is **idempotent**: files that already exist are skipped. It is also
tolerant of individual failures — if one font can't be fetched it prints a
warning and continues, then lists the manual Google Fonts links for anything
that failed in the final summary.

### Source

Fonts are fetched from the **google-webfonts-helper** API
(<https://gwfh.mranftl.com>), which repackages the Google Fonts catalogue and
serves ready-to-use `.woff2` files (including specific weights/styles and the
`cyrillic` subset for the `old-russian` theme). The script queries the JSON
endpoint per font to find the exact `woff2` URL for each requested variant,
falling back to the closest available variant if an exact one is missing.

### Requirements

- Python 3.11+ (uses the stdlib `tomllib`)
- `httpx` (already a project dependency)

### Licensing

All fonts referenced by the themes are licensed under the **SIL Open Font
License 1.1 (OFL-1.1)** and are freely redistributable.
