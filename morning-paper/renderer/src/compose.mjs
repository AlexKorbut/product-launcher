// Compose a full HTML document from a RenderDocument + a theme bundle.
// Content is theme-agnostic; all visual decisions come from themes/<id>/.

import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { parse as parseToml } from "smol-toml";
import { fontFaceCss } from "./fonts.mjs";
import { prepareImages } from "./images.mjs";

const PAGE_SIZES = {
  a4: "210mm 297mm",
  a3: "297mm 420mm",
  letter: "8.5in 11in",
  broadsheet: "11in 22in",
  tabloid: "11in 17in",
};

function esc(s) {
  return String(s ?? "").replace(
    /[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])
  );
}

function cssVarsBlock(manifest) {
  const g = manifest.grid || {};
  const t = manifest.type || {};
  const c = manifest.colors || {};
  const vars = {
    "--paper": c.paper || "#fff",
    "--ink": c.ink || "#000",
    "--accent": c.accent || "#000",
    "--masthead-font": `"${t.masthead_font}"`,
    "--headline-font": `"${t.headline_font}"`,
    "--body-font": `"${t.body_font}"`,
    "--columns": String(g.columns ?? 6),
    "--rule-weight": g.rule_weight || "1px",
    "--gutter": g.gutter || "10px",
  };
  const body = Object.entries(vars)
    .map(([k, v]) => `  ${k}: ${v};`)
    .join("\n");
  return `:root[data-theme="${manifest.id}"] {\n${body}\n}`;
}

function pageRule(manifest) {
  const fmt = manifest.format || {};
  const size = PAGE_SIZES[fmt.page || "a4"] || PAGE_SIZES.a4;
  const orient = fmt.orientation === "landscape" ? " landscape" : "";
  const bleed = Number(fmt.bleed_mm || 0);
  const marks = bleed > 0 ? "\n  marks: crop cross;" : "";
  const bleedRule = bleed > 0 ? `\n  bleed: ${bleed}mm;` : "";
  return `@page {\n  size: ${size}${orient};${bleedRule}${marks}\n}`;
}

function storyArticle(view, slot) {
  if (!view) return "";
  const cls = `story story--${slot.size}`;
  const span = `--span:${slot.columns}`;
  const photo =
    slot.with_photo && view.image_ref
      ? `<figure class="story__photo"><img src="${esc(view.image_ref)}" alt=""/>${
          view.caption ? `<figcaption>${esc(view.caption)}</figcaption>` : ""
        }</figure>`
      : "";
  const deck = view.deck ? `<p class="story__deck">${esc(view.deck)}</p>` : "";
  const byline = view.byline ? `<p class="story__byline">${esc(view.byline)}</p>` : "";
  const quote = slot.pull_quote
    ? `<blockquote class="story__pull">${esc(slot.pull_quote)}</blockquote>`
    : "";
  // body_html is trusted newspaper-register HTML produced by our own editorial stage.
  return `<article class="${cls}" style="${span}">
  <h2 class="story__headline">${esc(view.headline)}</h2>
  ${deck}
  ${byline}
  ${photo}
  ${quote}
  <div class="story__body">${view.body_html || ""}</div>
</article>`;
}

function renderSections(doc) {
  const slotsByStory = new Map(doc.grid_plan.slots.map((s) => [s.story_id, s]));
  const order =
    doc.grid_plan.section_order && doc.grid_plan.section_order.length
      ? doc.grid_plan.section_order
      : [...new Set(doc.grid_plan.slots.map((s) => s.section))];

  const lead = doc.grid_plan.slots.find((s) => s.size === "lead");
  const leadHtml = lead
    ? `<section class="lead">${storyArticle(doc.stories[lead.story_id], lead)}</section>`
    : "";

  const sections = order
    .map((sec) => {
      const slots = doc.grid_plan.slots.filter(
        (s) => s.section === sec && s.size !== "lead"
      );
      if (!slots.length) return "";
      const items = slots
        .map((s) => storyArticle(doc.stories[s.story_id], s))
        .join("\n");
      return `<section class="section section--${esc(sec)}">
  <h3 class="section__title">${esc(sec)}</h3>
  <div class="section__grid">${items}</div>
</section>`;
    })
    .join("\n");

  return leadHtml + "\n" + sections;
}

export async function composeHtml(doc, { themesDir, assetsDir, rendererDir }) {
  const warnings = [];
  const themeDir = path.join(themesDir, doc.theme_id);
  const manifestPath = path.join(themeDir, "theme.toml");
  if (!existsSync(manifestPath)) {
    throw new Error(`theme not found: ${doc.theme_id} (${manifestPath})`);
  }
  const manifest = parseToml(await readFile(manifestPath, "utf-8"));

  const baseCss = await readFile(
    path.join(themesDir, "_base", "base.css"),
    "utf-8"
  );
  const themeCssPath = path.join(themeDir, "theme.css");
  const themeCss = existsSync(themeCssPath)
    ? await readFile(themeCssPath, "utf-8")
    : "";

  const fontCss = await fontFaceCss(manifest, themeDir).catch((e) => {
    warnings.push(`fonts: ${e.message}`);
    return "";
  });

  // Resolve + treat images (bw/duotone), rewriting image_ref -> data/file URLs.
  await prepareImages(doc, { assetsDir, manifest }).catch((e) =>
    warnings.push(`images: ${e.message}`)
  );

  const mastheadSvg =
    manifest.assets && manifest.assets.masthead
      ? await readFile(path.join(themeDir, manifest.assets.masthead), "utf-8").catch(
          () => ""
        )
      : "";

  const m = doc.masthead || {};
  const mastheadHtml = `<header class="masthead">
  ${mastheadSvg ? `<div class="masthead__logo">${mastheadSvg}</div>` : `<h1 class="masthead__title">${esc(m.title)}</h1>`}
  <div class="masthead__meta">
    <span>${esc(m.date)}</span>
    ${m.issue_no ? `<span>№ ${esc(m.issue_no)}</span>` : ""}
    ${m.edition ? `<span>${esc(m.edition)}</span>` : ""}
  </div>
</header>`;

  const html = `<!doctype html>
<html lang="${esc(doc.locale || "ru")}">
<head>
<meta charset="utf-8"/>
<style>
${fontCss}
${pageRule(manifest)}
${cssVarsBlock(manifest)}
${baseCss}
${themeCss}
</style>
</head>
<body data-theme="${esc(doc.theme_id)}">
${mastheadHtml}
<main class="paper">
${renderSections(doc)}
</main>
</body>
</html>`;

  return { html, warnings, baseUrl: themeDir };
}
