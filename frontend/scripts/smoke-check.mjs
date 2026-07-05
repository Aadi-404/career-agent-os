import { readFileSync } from "node:fs";
import { resolve } from "node:path";


const root = resolve(import.meta.dirname, "..");

const checks = [
  {
    name: "score workflow task",
    file: "src/main.tsx",
    patterns: ["Resume Match", "Command Center", "Refresh Command Center", "/ai/command-center", "Requirement Match Matrix", "Explainable Score Breakdown"],
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
    patterns: ["Saved Comparisons", "Application Pipeline", "Preparation Progress", "Open Action", "/ai/opportunities/next-actions", "pipelineNextActions"],
  },
  {
    name: "research notes workflow",
    file: "src/main.tsx",
    patterns: ["Research Notes", "Generate From Latest Score", "decodeResearchHandoff", "Saved Research Memory", "Citation quality", "Sources and Citation Quality"],
  },
  {
    name: "application decision workflow",
    file: "src/main.tsx",
    patterns: ["Apply Decision", "Build Apply Decision", "Research Signals Used"],
  },
  {
    name: "career agent planner workflow",
    file: "src/main.tsx",
    patterns: ["Career Agent Plan", "Build Next-Step Plan", "Recommended Tool Order", "Run / Open", "/ai/agent/plan"],
  },
  {
    name: "resume rewrite workflow",
    file: "src/main.tsx",
    patterns: ["Resume Rewrite", "Build Rewrite Suggestions", "Evidence-Constrained Rewrite", "Apply to Resume Draft", "Accepted Rewrite History", "Resume Version Snapshots", "Version Compare", "Restore to Editor", "Restore Audit History", "accepted-resume-rewrites", "resume-versions", "resume-version-restores", "gap_do_not_claim"],
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
    patterns: ["Production Readiness", "Manual Launch Tracker", "Deployment Runbook", "Run Production Smoke", "Seed Demo Data", "Clean Demo Data", "Launch Readiness", "Resolve launch blockers before deploy"],
  },
  {
    name: "launch tracker styles",
    file: "src/styles.css",
    patterns: [".launchTrackerSummary", ".launchTrackerList", ".statusPill.pass", ".nextTaskBox", ".recommendationActions", ".prepNextAction", ".opportunityNextAction", ".commandCenter", ".commandTopActions", ".commandReadiness", ".commandReadinessList", ".runbookGrid", ".productionSmokeList"],
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
