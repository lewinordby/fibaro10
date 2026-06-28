import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { smokeRoutes } from "./smoke-routes.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const moduleViewsPath = path.resolve(__dirname, "../src/moduleViews.ts");

function objectLiteralBounds(source, startIndex) {
  const openIndex = source.indexOf("{", startIndex);
  if (openIndex < 0) {
    throw new Error("Fant ikke MODULE_VIEWS objektet");
  }

  let depth = 0;
  for (let index = openIndex; index < source.length; index += 1) {
    const char = source[index];
    if (char === "{") depth += 1;
    if (char === "}") depth -= 1;
    if (depth === 0) return [openIndex, index];
  }

  throw new Error("MODULE_VIEWS objektet ble ikke avsluttet");
}

function extractModuleViews(source) {
  const markerIndex = source.indexOf("export const MODULE_VIEWS");
  if (markerIndex < 0) {
    throw new Error("Fant ikke MODULE_VIEWS i moduleViews.ts");
  }

  const [openIndex, closeIndex] = objectLiteralBounds(source, markerIndex);
  const body = source.slice(openIndex + 1, closeIndex);
  const modulePattern = /^\s*([a-z0-9_-]+):\s*\[/gm;
  const moduleMatches = [...body.matchAll(modulePattern)];
  const modules = new Map();

  for (let index = 0; index < moduleMatches.length; index += 1) {
    const match = moduleMatches[index];
    const moduleName = match[1];
    const blockStart = match.index + match[0].length;
    const blockEnd = index + 1 < moduleMatches.length ? moduleMatches[index + 1].index : body.length;
    const block = body.slice(blockStart, blockEnd);
    const keys = [...block.matchAll(/key:\s*"([^"]+)"/g)].map((keyMatch) => keyMatch[1]);
    modules.set(moduleName, keys);
  }

  return modules;
}

function duplicates(values) {
  const seen = new Set();
  const duplicateValues = new Set();
  for (const value of values) {
    if (seen.has(value)) duplicateValues.add(value);
    seen.add(value);
  }
  return [...duplicateValues].sort();
}

const source = await fs.readFile(moduleViewsPath, "utf8");
const moduleViews = extractModuleViews(source);
const expectedPaths = [...moduleViews.entries()].flatMap(([moduleName, views]) =>
  views.map((view) => `/${moduleName}/${view}`),
);
const smokePaths = smokeRoutes.map((route) => route.path);
const expectedSet = new Set(expectedPaths);
const smokeSet = new Set(smokePaths);

const missing = expectedPaths.filter((routePath) => !smokeSet.has(routePath));
const extra = smokePaths.filter((routePath) => !expectedSet.has(routePath));
const duplicateSmokeRoutes = duplicates(smokePaths);

const result = {
  moduleCount: moduleViews.size,
  expectedRouteCount: expectedPaths.length,
  smokeRouteCount: smokePaths.length,
  missing,
  extra,
  duplicateSmokeRoutes,
};

console.log(JSON.stringify(result, null, 2));

if (missing.length || extra.length || duplicateSmokeRoutes.length) {
  process.exit(1);
}
