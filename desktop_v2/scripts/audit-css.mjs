import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const srcDir = path.join(root, "src");
const styleDir = path.join(srcDir, "styles");

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(fullPath) : [fullPath];
  });
}

function read(file) {
  return fs.readFileSync(file, "utf8");
}

function relative(file) {
  return path.relative(root, file).replaceAll("\\", "/");
}

const cssFiles = walk(styleDir)
  .filter((file) => file.endsWith(".css"))
  .sort((left, right) => relative(left).localeCompare(relative(right)));
const codeFiles = walk(srcDir).filter((file) => /\.(ts|tsx)$/.test(file));
const codeText = codeFiles.map(read).join("\n");

const dynamicClassPatterns = [
  /^ant-/,
  /^leaflet-/,
  /^domain-/,
  /^tone-/,
  /^kind-/,
  /^zone-/,
  /^(ok|warn|bad|error|empty|missing|plain|neutral|positive|negative)$/,
  /^(income|cost|sum|payout)$/,
  /^row-/,
  /^source-/,
  /^with-/,
];

function isDynamicClass(className) {
  return dynamicClassPatterns.some((pattern) => pattern.test(className));
}

function staticClassUsed(className) {
  return codeText.includes(className);
}

const selectorPattern = /\.(-?[_a-zA-Z]+[_a-zA-Z0-9-]*)/g;
const classes = new Map();
const hardcodedColors = [];

for (const file of cssFiles) {
  const text = read(file);
  const rel = relative(file);
  for (const match of text.matchAll(selectorPattern)) {
    const className = match[1];
    if (className.startsWith("ant-")) continue;
    const list = classes.get(className) ?? [];
    list.push(rel);
    classes.set(className, list);
  }
  for (const match of text.matchAll(/#[0-9a-fA-F]{3,8}\b|rgba?\([^)]+\)|hsla?\([^)]+\)/g)) {
    hardcodedColors.push({ file: rel, value: match[0] });
  }
}

const duplicateClassSelectors = Array.from(classes.entries())
  .map(([className, files]) => ({
    className,
    count: files.length,
    files: Array.from(new Set(files)),
  }))
  .filter((item) => item.count > 1)
  .sort((left, right) => right.count - left.count || left.className.localeCompare(right.className));

const crossFileClassSelectors = duplicateClassSelectors
  .filter((item) => item.files.length > 1)
  .sort((left, right) => right.files.length - left.files.length || right.count - left.count || left.className.localeCompare(right.className));

const possibleUnusedClasses = Array.from(classes.keys())
  .filter((className) => !isDynamicClass(className))
  .filter((className) => !staticClassUsed(className))
  .sort();

const cssFileStats = cssFiles.map((file) => {
  const text = read(file);
  return {
    file: relative(file),
    lines: text.split(/\r?\n/).length,
    bytes: Buffer.byteLength(text),
  };
});

const summary = {
  cssFiles: cssFileStats,
  codeFiles: codeFiles.length,
  classCount: classes.size,
  duplicateClassSelectors: duplicateClassSelectors.length,
  crossFileClassSelectors: crossFileClassSelectors.length,
  possibleUnusedClasses: possibleUnusedClasses.length,
  hardcodedColorValues: hardcodedColors.length,
  largestCssFiles: [...cssFileStats].sort((left, right) => right.lines - left.lines).slice(0, 5),
  mostRepeatedClasses: duplicateClassSelectors.slice(0, 20),
  crossFileClasses: crossFileClassSelectors.slice(0, 20),
  possibleUnusedClassNames: possibleUnusedClasses.slice(0, 80),
};

console.log(JSON.stringify(summary, null, 2));
