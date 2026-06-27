import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import postcss from "postcss";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const styleDir = path.join(root, "src", "styles");

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(fullPath) : [fullPath];
  });
}

function relative(file) {
  return path.relative(root, file).replaceAll("\\", "/");
}

const cssFiles = walk(styleDir)
  .filter((file) => file.endsWith(".css"))
  .sort((left, right) => relative(left).localeCompare(relative(right)));

for (const file of cssFiles) {
  postcss.parse(fs.readFileSync(file, "utf8"), { from: file });
}

console.log(`CSS parse OK (${cssFiles.length} files)`);
