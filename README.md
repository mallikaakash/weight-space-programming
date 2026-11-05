# weight-space-programming

Spec-driven builds with **Claude Code** (implementer) and a **Cursor orchestrator** (monitor + rubric). See [docs/ORCHESTRATION.md](docs/ORCHESTRATION.md).

Quick start:

1. Edit requirements in `docs/SPEC.md`.
2. Set secrets in `.env` (see `.env.example`) and in Cursor Cloud Agent secrets for cloud runs.
3. `cd scripts/orchestrator && npm install && npm run start:local` (local checkout) or `npm start` (cloud clone).
