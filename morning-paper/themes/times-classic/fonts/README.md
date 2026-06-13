# Fonts for `times-classic`

Drop the following OFL-licensed font files here (filenames must match `theme.toml`):

- `UnifrakturCook-Regular.woff2` — blackletter masthead.
  Source: https://fonts.google.com/specimen/UnifrakturCook (OFL-1.1)
- `EBGaramond-Regular.woff2`, `EBGaramond-Bold.woff2` — body + headlines.
  Source: https://fonts.google.com/specimen/EB+Garamond (OFL-1.1)

Convert TTF → WOFF2 with `woff2_compress` or `fonttools ttLib.woff2`.

Until the files are present the renderer falls back to the CSS font stack
(`EB Garamond, Garamond, "Times New Roman", serif`); add the files for the real
look. Keep the upstream `OFL.txt` alongside as `LICENSE.txt`.
