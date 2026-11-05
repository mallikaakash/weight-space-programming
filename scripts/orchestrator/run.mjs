#!/usr/bin/env node
/**
 * Launch Cursor **cloud** orchestrator: monitors Claude Code build, writes rubric.
 *
 * Requires: CURSOR_API_KEY, GITHUB_REPO_URL, GITHUB_REF (optional)
 * Cloud VM must have CLAUDE_CODE_OAUTH_TOKEN (or ANTHROPIC_API_KEY) in Cursor Cloud Agent environment.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Agent } from "@cursor/sdk";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const taskPath = path.join(
  root,
  "scripts/orchestrator/prompts/cursor-orchestrator-task.md",
);

const apiKey = process.env.CURSOR_API_KEY;
if (!apiKey) {
  console.error("CURSOR_API_KEY is required. See docs/ORCHESTRATION.md");
  process.exit(1);
}

const repoUrl = process.env.GITHUB_REPO_URL;
if (!repoUrl) {
  console.error(
    "GITHUB_REPO_URL is required for cloud runs. Set it in .env (see .env.example).",
  );
  process.exit(1);
}

const ref = process.env.GITHUB_REF || "main";
const modelId = process.env.CURSOR_MODEL || "composer-2.5";
const autoCreatePR = process.env.AUTO_CREATE_PR === "1";

const task = readFileSync(taskPath, "utf8");

const agent = await Agent.create({
  apiKey,
  model: { id: modelId },
  cloud: {
    repos: [{ url: repoUrl, startingRef: ref }],
    autoCreatePR,
  },
});

try {
  console.error(`Cloud orchestrator starting (repo=${repoUrl} ref=${ref})`);
  const run = await agent.send(task);
  console.error(`Run id: ${run.id} agent: ${agent.agentId}`);

  for await (const event of run.stream()) {
    if (event.type === "assistant") {
      for (const block of event.message.content) {
        if (block.type === "text") process.stdout.write(block.text);
      }
    }
  }

  const result = await run.wait();
  console.error(`\nStatus: ${result.status} run=${run.id}`);
  process.exit(result.status === "finished" ? 0 : 2);
} finally {
  await agent.close();
}
