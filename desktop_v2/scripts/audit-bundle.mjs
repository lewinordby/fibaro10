import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const distDir = path.join(root, "dist");
const assetsDir = path.join(distDir, "assets");

const limits = {
  maxJsAssetBytes: Number(process.env.FIBARO10_BUNDLE_MAX_JS_ASSET_BYTES || 1_200_000),
  maxCssAssetBytes: Number(process.env.FIBARO10_BUNDLE_MAX_CSS_ASSET_BYTES || 120_000),
  maxTotalGzipBytes: Number(process.env.FIBARO10_BUNDLE_MAX_TOTAL_GZIP_BYTES || 785_000),
};

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(fullPath) : [fullPath];
  });
}

function gzipSize(file) {
  return zlib.gzipSync(fs.readFileSync(file)).length;
}

function relative(file) {
  return path.relative(root, file).replaceAll("\\", "/");
}

if (!fs.existsSync(assetsDir)) {
  console.error("dist/assets mangler. Kjor npm run build forst.");
  process.exit(1);
}

const assets = walk(assetsDir)
  .filter((file) => /\.(js|css)$/.test(file))
  .map((file) => ({
    file: relative(file),
    type: path.extname(file).slice(1),
    bytes: fs.statSync(file).size,
    gzipBytes: gzipSize(file),
  }))
  .sort((left, right) => right.bytes - left.bytes);

const jsAssets = assets.filter((asset) => asset.type === "js");
const cssAssets = assets.filter((asset) => asset.type === "css");
const totalGzipBytes = assets.reduce((sum, asset) => sum + asset.gzipBytes, 0);

const failures = [];
for (const asset of jsAssets) {
  if (asset.bytes > limits.maxJsAssetBytes) {
    failures.push(`${asset.file} er ${asset.bytes} byte, over JS-grense ${limits.maxJsAssetBytes}`);
  }
}
for (const asset of cssAssets) {
  if (asset.bytes > limits.maxCssAssetBytes) {
    failures.push(`${asset.file} er ${asset.bytes} byte, over CSS-grense ${limits.maxCssAssetBytes}`);
  }
}
if (totalGzipBytes > limits.maxTotalGzipBytes) {
  failures.push(`Total gzip er ${totalGzipBytes} byte, over grense ${limits.maxTotalGzipBytes}`);
}

const summary = {
  assetCount: assets.length,
  jsAssetCount: jsAssets.length,
  cssAssetCount: cssAssets.length,
  totalBytes: assets.reduce((sum, asset) => sum + asset.bytes, 0),
  totalGzipBytes,
  limits,
  largestAssets: assets.slice(0, 12),
};

console.log(JSON.stringify(summary, null, 2));

if (failures.length) {
  console.error(`Bundle audit feilet:\n${failures.join("\n")}`);
  process.exit(1);
}
