Implement and run the BFCL cross-format base vs edited benchmark for SmolLM2-360M-Instruct.

Session label: `{{SESSION_ID}}`

Do this end-to-end:

1. Read `experiments/tool_schema/bfcl_simple_eval.py` and bfcl-eval’s AST eval path.
2. Implement a multi-category eval CLI (or generalize the existing one) covering:
   `simple_python`, `simple_java`, `simple_javascript`, `multiple`, `parallel`, `parallel_multiple`.
3. For each category, run **base** (no edited state) and **edited** (`artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt`).
4. Write per-run summaries under `experiments/tool_schema/results/bfcl/`.
5. Produce `experiments/tool_schema/results/bfcl/CROSSFMT_BASE_VS_EDITED.md` with a table:

   | category | n | base AST acc | edited AST acc | delta |

6. Add a short “Cross-format probe” subsection to the root README pointing at that table.
7. Append a diary to `experiments/tool_schema/wsp/results/CROSSFMT_RUNNING_LOG.md`.
8. `git add` / `git commit` / `git push -u origin cursor/bfcl-crossfmt-base-vs-edited-317b`.

Constraints: eval only (no weight editing); CPU OK; skip live/multi-turn/web/memory; be honest if edited hurts off-distribution categories.

Start by sketching the eval design, then implement, then run categories (you may parallelize base/edited sequentially per category to avoid RAM blowups).
