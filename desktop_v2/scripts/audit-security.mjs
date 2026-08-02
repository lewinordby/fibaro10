import { spawnSync } from "node:child_process";

const audit = process.platform === "win32"
  ? spawnSync("cmd.exe", ["/d", "/s", "/c", "npm.cmd audit --json"], { encoding: "utf8" })
  : spawnSync("npm", ["audit", "--json"], { encoding: "utf8" });

if (!audit.stdout) {
  console.error(audit.stderr || "npm audit returnerte ikke et lesbart resultat.");
  process.exit(1);
}

let report;
try {
  report = JSON.parse(audit.stdout);
} catch (error) {
  console.error("Kunne ikke tolke npm audit-resultatet.", error);
  process.exit(1);
}

const allowedAdvisories = new Set([1124282]);
const vulnerabilities = report.vulnerabilities || {};

function isAllowed(name, vulnerability) {
  if (!vulnerability) return false;
  if (name === "react-router") {
    return vulnerability.via.every(
      (item) => typeof item === "object" && allowedAdvisories.has(Number(item.source)),
    );
  }
  if (name === "react-router-dom") {
    return vulnerability.via.every((item) => item === "react-router") && isAllowed("react-router", vulnerabilities["react-router"]);
  }
  return false;
}

const severityRank = { info: 0, low: 1, moderate: 2, high: 3, critical: 4 };
const actionable = Object.entries(vulnerabilities).filter(
  ([name, vulnerability]) => severityRank[vulnerability.severity] >= severityRank.moderate && !isAllowed(name, vulnerability),
);

if (actionable.length) {
  console.error("Avhengighetskontrollen fant sårbarheter som må håndteres:");
  for (const [name, vulnerability] of actionable) {
    console.error(`- ${name}: ${vulnerability.severity}`);
  }
  process.exit(1);
}

if (vulnerabilities["react-router"]) {
  console.warn(
    "Tillatt avvik: GHSA-qwww-vcr4-c8h2 gjelder React Routers RSC-modus. Fibaro10 bruker kun BrowserRouter og har ingen React Server Components eller router-actions.",
  );
}

console.log("Frontend-avhengigheter kontrollert uten relevante sårbarheter.");
