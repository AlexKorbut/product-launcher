# swiss-grotesk — Font Downloads

All fonts are released under the SIL Open Font License 1.1 (OFL-1.1).

Run `python scripts/fetch_fonts.py --theme swiss-grotesk` from the morning-paper/
directory to fetch these automatically (OFL-1.1), or download manually from the
Google Fonts links below.

Expected files (names must match `theme.toml`):

- `DMSans-Regular.woff2`, `DMSans-Bold.woff2`, `DMSans-Medium.woff2`
- `DMSerifText-Regular.woff2`, `DMSerifText-Italic.woff2`

## DM Sans

A geometric sans-serif typeface designed for digital interfaces and print.
Used for masthead, headlines, section titles, and UI elements in this theme.
Provides a clean, modern Swiss International feel with excellent legibility.

- Source: https://fonts.google.com/specimen/DM+Sans
- License: OFL-1.1
- Files needed:
  - `DMSans-Regular.woff2`
  - `DMSans-Medium.woff2`
  - `DMSans-Bold.woff2`

Note: DM Sans also includes ExtraBold (800) weight in the variable font.
For the masthead title, the 800 weight is used — download from the variable
font package or use `DMSans[ital,opsz,wght].woff2` and declare as variable.

## DM Serif Text

The serif companion to DM Sans, designed for body text use. Its contrast with
the sans-serif headers creates the classical Swiss typographic tension between
modern structure and readable humanist text.

- Source: https://fonts.google.com/specimen/DM+Serif+Text
- License: OFL-1.1
- Files needed:
  - `DMSerifText-Regular.woff2`
  - `DMSerifText-Italic.woff2`

## Note

The renderer will warn (but not fail) if font files are absent.
System sans-serif fallbacks (Helvetica Neue, Arial) will be used instead.
