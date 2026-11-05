#!/usr/bin/env node
/**
 * Seeds artifacts/RUBRIC.md from docs/SPEC.md checklist + git diff since baseline.
 */
import { readFileSync, existsSync } from "node:fs";
import { execSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const specPath = process.env.SPEC_PATH || path.join(root, "docs/SPEC.md");
const baselineFile = path.join(root, ".orchestrator/baseline.sha");

function git(cmd) {
  try {
    return execSync(cmd, { cwd: root, encoding: "utf8" }).trim();
  } catch {
    return "";
  }
}

const spec = existsSync(specPath)
  ? readFileSync(specPath, "utf8")
  : "(missing spec file)";

const checklist = [];
for (const line of spec.split("\n")) {
  // Match REQ-001 and REQ-RAG-01 style checklist lines
  const m = line.match(/^- \[ \] \*\*(REQ-(?:[A-Z]+-)?\d+:)\*\*\s+(.*)$/);
  if (m) checklist.push({ id: m[1].replace(":", ""), label: m[2].trim() });
}

let baseline = "unknown";
if (existsSync(baselineFile)) {
  baseline = readFileSync(baselineFile, "utf8").trim();
}

const changed =
  baseline && baseline !== "unknown"
    ? git(`git diff --name-status ${baseline}`) ||
      git("git diff --name-status")
    : git("git diff --name-status") || git("git status --porcelain");

const stat =
  baseline && baseline !== "unknown"
    ? git(`git diff --stat ${baseline}`) || git("git diff --stat")
    : git("git diff --stat");

const now = new Date().toISOString();

console.log("# Build verification rubric");
console.log("");
console.log(`Generated: ${now}`);
console.log(`Spec: ${path.relative(root, specPath)}`);
console.log(`Baseline commit: ${baseline}`);
console.log("");

console.log("## Changed files (since baseline)");
console.log("");
console.log(changed ? "```\n" + changed + "\n```" : "_No git diff detected._");
console.log("");

if (stat) {
  console.log("## Diff stat");
  console.log("");
  console.log("```");
  console.log(stat);
  console.log("```");
  console.log("");
}

console.log("## Requirements checklist (from spec)");
console.log("");
if (checklist.length === 0) {
  console.log("_No `- [ ] **REQ-…**` lines found in spec. Add them under Rubric checklist._");
} else {
  for (const item of checklist) {
    console.log(`- [ ] **${item.id}** — ${item.label}`);
  }
}
console.log("");
console.log("## Orchestrator assessment");
console.log("");
console.log("_To be filled by the Cursor orchestrator after reviewing the diff._");
console.log("");
