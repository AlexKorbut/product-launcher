#!/usr/bin/env node
// Entry point. Reads a RenderDocument JSON, composes HTML from the base template
// + theme bundle, and prints a print-ready PDF via Paged.js + Playwright/Chromium.
//
// Usage: node render.mjs --in doc.json --out issue.pdf --themes ../themes --assets ../.data/objects
// On success prints a single JSON line of metadata: {"page_count": N, "warnings": [...]}

import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { composeHtml } from "./src/compose.mjs";
import { printPdf } from "./src/paged.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i]?.replace(/^--/, "");
    if (key) args[key] = argv[i + 1];
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const required = ["in", "out"];
  for (const r of required) {
    if (!args[r]) {
      process.stderr.write(`missing --${r}\n`);
      process.exit(2);
    }
  }
  const themesDir = args.themes
    ? path.resolve(args.themes)
    : path.resolve(__dirname, "..", "themes");
  const assetsDir = args.assets ? path.resolve(args.assets) : process.cwd();

  const doc = JSON.parse(await readFile(args.in, "utf-8"));

  const { html, warnings, baseUrl } = await composeHtml(doc, {
    themesDir,
    assetsDir,
    rendererDir: __dirname,
  });

  const { pageCount } = await printPdf({
    html,
    baseUrl,
    outPath: path.resolve(args.out),
    rendererDir: __dirname,
  });

  process.stdout.write(
    JSON.stringify({ page_count: pageCount, warnings }) + "\n"
  );
}

main().catch((err) => {
  process.stderr.write(String(err?.stack || err) + "\n");
  process.exit(1);
});
