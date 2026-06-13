// Generate @font-face declarations from a theme manifest's [[fonts]] entries.
// Fonts are bundled per theme (themes/<id>/fonts/) so there's no network
// dependency and no missing-glyph fallback at print time.

import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

const MIME = {
  ".woff2": "font/woff2",
  ".woff": "font/woff",
  ".ttf": "font/ttf",
  ".otf": "font/otf",
};

function formatFor(ext) {
  return (
    { ".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype" }[
      ext
    ] || "woff2"
  );
}

export async function fontFaceCss(manifest, themeDir) {
  const fonts = manifest.fonts || [];
  const blocks = [];
  for (const font of fonts) {
    for (const rel of font.files || []) {
      const abs = path.join(themeDir, rel);
      if (!existsSync(abs)) {
        // Missing font file: skip rather than fail; the body font stack falls back.
        continue;
      }
      const ext = path.extname(abs).toLowerCase();
      const buf = await readFile(abs);
      const dataUrl = `data:${MIME[ext] || "font/woff2"};base64,${buf.toString(
        "base64"
      )}`;
      blocks.push(
        `@font-face {\n  font-family: "${font.family}";\n  src: url("${dataUrl}") format("${formatFor(
          ext
        )}");\n  font-display: swap;\n}`
      );
    }
  }
  return blocks.join("\n");
}
