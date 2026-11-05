#!/usr/bin/env node
/**
 * Local orchestrator against current checkout (for testing).
 * Requires CURSOR_API_KEY and Claude auth (CLAUDE_CODE_OAUTH_TOKEN or local login) for claude-build.sh.
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

const modelId = process.env.CURSOR_MODEL || "composer-2.5";
const task = readFileSync(taskPath, "utf8");

const agent = await Agent.create({
  apiKey,
  model: { id: modelId },
  local: { cwd: root },
  disallowedTools: ["edit", "write", "notebookEdit", "ApplyPatch"],
});

try {
  console.error(`Local orchestrator starting (cwd=${root})`);
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
