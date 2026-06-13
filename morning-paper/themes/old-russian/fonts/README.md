# old-russian — Font Downloads

All fonts are released under the SIL Open Font License 1.1 (OFL-1.1).

Run `python scripts/fetch_fonts.py --theme old-russian` from the morning-paper/
directory to fetch these automatically (OFL-1.1), or download manually from the
Google Fonts links below. Both families are fetched with the `cyrillic` subset.

Expected files (names must match `theme.toml`):

- `CormorantGaramond-Regular.woff2`, `CormorantGaramond-Bold.woff2`,
  `CormorantGaramond-Italic.woff2`, `CormorantGaramond-BoldItalic.woff2`
- `Vollkorn-Regular.woff2`, `Vollkorn-Bold.woff2`, `Vollkorn-Italic.woff2`

## Cormorant Garamond

A refined serif with full Cyrillic support, ideal for the pre-1917 Russian
newspaper aesthetic. Includes regular, bold, italic, and bold-italic weights.

- Source: https://github.com/CatharsisFonts/Cormorant
- License: OFL-1.1
- Files needed:
  - `CormorantGaramond-Regular.woff2`
  - `CormorantGaramond-Bold.woff2`
  - `CormorantGaramond-Italic.woff2`
  - `CormorantGaramond-BoldItalic.woff2`

Also available on Google Fonts:
https://fonts.google.com/specimen/Cormorant+Garamond

## Vollkorn

A full-featured oldstyle serif with complete Cyrillic support. Used for body
text to achieve authentic period readability.

- Source: https://github.com/FAlthausen/Vollkorn-Typeface
- License: OFL-1.1
- Files needed:
  - `Vollkorn-Regular.woff2`
  - `Vollkorn-Bold.woff2`
  - `Vollkorn-Italic.woff2`

Also available on Google Fonts:
https://fonts.google.com/specimen/Vollkorn

## Note

The renderer will warn (but not fail) if font files are absent.
System serif fallbacks (Georgia, Times New Roman) will be used instead.
