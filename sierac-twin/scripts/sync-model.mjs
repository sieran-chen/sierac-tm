#!/usr/bin/env node
/**
 * Copy the GLB from repo 3d/ to public/models/001.glb so the viewer can load it.
 * Run from sierac-twin: node scripts/sync-model.mjs
 */
import { copyFileSync, readdirSync, existsSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const twinRoot = join(__dirname, "..");
const modelDir = join(twinRoot, "..", "3d");
const outFile = join(twinRoot, "public", "models", "001.glb");
const outDir = join(twinRoot, "public", "models");

if (!existsSync(modelDir)) {
  console.error("3d folder not found:", modelDir);
  process.exit(1);
}

const files = readdirSync(modelDir).filter((f) => f.toLowerCase().endsWith(".glb"));
if (files.length === 0) {
  console.error("No .glb file found in 3d folder:", modelDir);
  process.exit(1);
}

if (!existsSync(outDir)) {
  mkdirSync(outDir, { recursive: true });
}

const src = join(modelDir, files[0]);
copyFileSync(src, outFile);
console.log("Copied", files[0], "-> public/models/001.glb");
