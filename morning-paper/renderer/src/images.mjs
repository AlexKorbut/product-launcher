// Resolve image refs from the object store and apply the theme's photo treatment
// (bw / duotone / color), rewriting doc.stories[*].image_ref to an inline data URL.

import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

async function loadSharp() {
  try {
    const mod = await import("sharp");
    return mod.default;
  } catch {
    return null; // sharp optional; without it we pass images through untreated
  }
}

function resolveRef(ref, assetsDir) {
  if (!ref) return null;
  if (ref.startsWith("http://") || ref.startsWith("https://")) return ref; // remote, leave as-is
  const abs = path.isAbsolute(ref) ? ref : path.join(assetsDir, ref);
  return existsSync(abs) ? abs : null;
}

async function treat(absPath, manifest, sharp) {
  const treatment = (manifest.photo && manifest.photo.treatment) || "color";
  const maxW = (manifest.photo && manifest.photo.max_width_px) || 1600;
  let img = sharp(absPath).resize({ width: maxW, withoutEnlargement: true });

  if (treatment === "bw") {
    img = img.grayscale();
  } else if (treatment === "duotone") {
    const [dark = "#1a1a1a", light = "#f7f4ec"] =
      (manifest.format && manifest.format.duotone) || [];
    img = img.grayscale().tint(hexToRgb(light)); // simple duotone approximation
  }
  const buf = await img.jpeg({ quality: 82 }).toBuffer();
  return `data:image/jpeg;base64,${buf.toString("base64")}`;
}

function hexToRgb(hex) {
  const h = hex.replace("#", "");
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  };
}

export async function prepareImages(doc, { assetsDir, manifest }) {
  const sharp = await loadSharp();
  for (const view of Object.values(doc.stories || {})) {
    if (!view.image_ref) continue;
    const abs = resolveRef(view.image_ref, assetsDir);
    if (!abs) {
      view.image_ref = null; // unresolved -> drop the photo slot gracefully
      continue;
    }
    if (abs.startsWith("http")) {
      view.image_ref = abs;
      continue;
    }
    if (sharp) {
      view.image_ref = await treat(abs, manifest, sharp);
    } else {
      const buf = await readFile(abs);
      view.image_ref = `data:image/jpeg;base64,${buf.toString("base64")}`;
    }
  }
}
