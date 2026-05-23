#!/usr/bin/env node
/**
 * Generate PNG icons and favicons from SVG sources.
 * Run: node scripts/generate-icons.mjs
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const iconsDir = path.join(root, "public", "icons");
const appDir = path.join(root, "src", "app");

const ICON_SIZES = [32, 64, 180, 192, 512];

async function renderPng(svgPath, size, outPath) {
  const svg = await readFile(svgPath);
  await sharp(svg, { density: 300 })
    .resize(size, size, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .png({ compressionLevel: 9, adaptiveFiltering: true })
    .toFile(outPath);
}

async function renderOg(svgPath, outPath) {
  const svg = await readFile(svgPath);
  await sharp(svg, { density: 150 })
    .resize(1200, 630, { fit: "cover" })
    .png({ compressionLevel: 9 })
    .toFile(outPath);
}

async function main() {
  await mkdir(iconsDir, { recursive: true });

  const lightSvg = path.join(iconsDir, "mark-light.svg");
  const darkSvg = path.join(iconsDir, "mark-dark.svg");

  console.log("Generating PWA icons (light)…");
  for (const size of ICON_SIZES) {
    const out = path.join(iconsDir, `icon-${size}.png`);
    await renderPng(lightSvg, size, out);
    console.log(`  ✓ icon-${size}.png`);
  }

  const applePath = path.join(iconsDir, "apple-touch-icon.png");
  await renderPng(lightSvg, 180, applePath);
  console.log("  ✓ apple-touch-icon.png");

  console.log("Generating dark icon…");
  await renderPng(darkSvg, 512, path.join(iconsDir, "icon-dark-512.png"));
  console.log("  ✓ icon-dark-512.png");

  console.log("Generating favicon…");
  const favicon32 = await readFile(path.join(iconsDir, "icon-32.png"));
  await writeFile(path.join(root, "public", "favicon.png"), favicon32);
  await writeFile(path.join(appDir, "icon.png"), await readFile(path.join(iconsDir, "icon-192.png")));
  await writeFile(path.join(appDir, "apple-icon.png"), await readFile(applePath));

  console.log("Generating OpenGraph image…");
  await renderOg(path.join(root, "public", "og-image.svg"), path.join(root, "public", "og-image.png"));
  console.log("  ✓ og-image.png");

  console.log("Done.");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
