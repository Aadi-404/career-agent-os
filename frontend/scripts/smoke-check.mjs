import { readFileSync } from "node:fs";
import { resolve } from "node:path";


const root = resolve(import.meta.dirname, "..");

const checks = [
  {
    name: "score workflow task",
    file: "src/main.tsx",
    patterns: ["Resume Match", "Requirement Match Matrix", "Explainable Score Breakdown"],
  },
  {
    name: "review and parser workflow",
    file: "src/main.tsx",
    patterns: ["Structured resume editor", "Structured JD editor", "Parse JD"],
  },
  {
    name: "optional AI modules",
    file: "src/main.tsx",
    patterns: ["Preparation Intelligence", "Cross-Question Chains", "Resume Improvements"],
  },
  {
    name: "history and comparison workflow",
    file: "src/main.tsx",
    patterns: ["Saved Comparisons", "Application Pipeline", "Preparation Progress"],
  },
  {
    name: "research notes workflow",
    file: "src/main.tsx",
    patterns: ["Research Notes", "Generate From Latest Score", "decodeResearchHandoff", "Saved Research Memory"],
  },
  {
    name: "application decision workflow",
    file: "src/main.tsx",
    patterns: ["Apply Decision", "Build Apply Decision", "Research Signals Used"],
  },
  {
    name: "resume rewrite workflow",
    file: "src/main.tsx",
    patterns: ["Resume Rewrite", "Build Rewrite Suggestions", "Evidence-Constrained Rewrite"],
  },
  {
    name: "extension workflow",
    file: "src/main.tsx",
    patterns: ["Extension Setup", "Check Extension Readiness", "Real Site Validation", "Record parser quality"],
  },
  {
    name: "evaluation and calibration workflow",
    file: "src/main.tsx",
    patterns: ["Score Evaluation", "Role-family weights", "Generate Suggestion"],
  },
  {
    name: "settings launch readiness workflow",
    file: "src/main.tsx",
    patterns: ["Production Readiness", "Manual Launch Tracker", "Smoke Runbook", "Seed Demo Data"],
  },
  {
    name: "launch tracker styles",
    file: "src/styles.css",
    patterns: [".launchTrackerSummary", ".launchTrackerList", ".statusPill.pass"],
  },
  {
    name: "package smoke script wiring",
    file: "package.json",
    patterns: ["\"smoke\"", "scripts/smoke-check.mjs"],
  },
];

const failures = [];

for (const check of checks) {
  const path = resolve(root, check.file);
  const content = readFileSync(path, "utf8");
  const missing = check.patterns.filter((pattern) => !content.includes(pattern));
  if (missing.length) {
    failures.push(`${check.name}: missing ${missing.map((item) => JSON.stringify(item)).join(", ")}`);
  } else {
    console.log(`[PASS] ${check.name}`);
  }
}

if (failures.length) {
  console.error("\nFrontend smoke check failed:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log(`\nFrontend smoke check passed (${checks.length} checks).`);
