import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import postcss from "postcss";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(root, "..");
const styleDirs = [
  path.join(root, "src", "styles"),
  path.join(repoRoot, "static"),
  path.join(repoRoot, "maintenance_mobile", "app", "static"),
  path.join(repoRoot, "fibaro10ipad", "app", "static"),
  path.join(repoRoot, "owntracks_service", "frontend", "src"),
  path.join(repoRoot, "browser_extensions"),
];

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(fullPath) : [fullPath];
  });
}

function relative(file) {
  return path.relative(repoRoot, file).replaceAll("\\", "/");
}

const cssFiles = styleDirs
  .filter((dir) => fs.existsSync(dir))
  .flatMap(walk)
  .filter((file) => file.endsWith(".css"))
  .sort((left, right) => relative(left).localeCompare(relative(right)));

for (const file of cssFiles) {
  postcss.parse(fs.readFileSync(file, "utf8"), { from: file });
}

console.log(`CSS parse OK (${cssFiles.length} files)`);
