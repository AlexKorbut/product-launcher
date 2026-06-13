// Dev helper: render a RenderDocument to a PNG screenshot of the first page.
// Usage: node preview.mjs --in doc.json --out preview.png --themes ../themes
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { composeHtml } from "./src/compose.mjs";

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const args = {};
const a = process.argv.slice(2);
for (let i = 0; i < a.length; i += 2) args[a[i].replace(/^--/, "")] = a[i + 1];

const doc = JSON.parse(await readFile(args.in, "utf-8"));
const themesDir = path.resolve(args.themes || path.join(__dirname, "..", "themes"));
const { html, baseUrl } = await composeHtml(doc, {
  themesDir,
  assetsDir: process.cwd(),
  rendererDir: __dirname,
});

const { chromium } = await import("playwright");
const entry = require.resolve("pagedjs");
const polyfill = await readFile(
  path.join(path.dirname(entry), "..", "dist", "paged.polyfill.js"),
  "utf-8"
);

const browser = await chromium.launch({ args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1100, height: 1500 } });
const withBase = html.replace(/<head>/i, `<head><base href="${pathToFileURL(baseUrl + path.sep).href}">`);
await page.setContent(withBase, { waitUntil: "networkidle" });
await page.addScriptTag({ content: polyfill });
await page.waitForFunction(() => document.querySelector(".pagedjs_page"), { timeout: 60000 });
const first = await page.$(".pagedjs_page");
await first.screenshot({ path: args.out });
await browser.close();
process.stdout.write(`wrote ${args.out}\n`);
