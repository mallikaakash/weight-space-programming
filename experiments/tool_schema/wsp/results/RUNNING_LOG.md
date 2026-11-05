# WSP running log

Track weight-space programming editor runs here. Append-only during a run.

## Baseline (pre-edit)

- Model: `HuggingFaceTB/SmolLM2-360M-Instruct`
- Test `strict_ok`: **20%** (n=20); parse 80%; tool 25%; no_hallucinated_keys 40%
- Stability: 3× greedy, `strict_ok_range = 0.0`
- Train practice size: 40

## Runs

_Awaiting first editor launch…_

## Run started 2026-11-05T08:15:27Z

- session_id: `wsp-run1-20261105T081527Z`
- budget: `12`
- claude_log: `/workspace/experiments/tool_schema/wsp/results/claude_editor_wsp-run1-20261105T081527Z.log`
- status: **running**

- trial `L29 down_proj top-1% magnitude x1.15`: 0.4 strict (base 0.40), parse 0.75, tool 0.575

### Monitor note (2026-11-05 UTC)

- Editor is live and already ran multiple train forwards + localized `L29 down_proj` magnitude edits.
- **Bug found:** each new Python process re-inited the harness and reset budget/edits. Fixed mid-run: sessions now persist `working_state.pt` + `budget.json` and **resume** on the same `session_id`.
- Reconstructed `budget.json` from `events.jsonl` so remaining budget is honest going forward.

- trial `L29 down_proj top-1% magnitude x0.85`: 0.4 strict (base 0.40), parse 0.675, tool 0.55
- trial `L20 o_proj top-2% x1.2`: 0.4 strict (base 0.40), parse 0.8, tool 0.6
- trial `L12 o_proj top-2% x1.2`: 0.4 strict (base 0.40), parse 0.775, tool 0.575
- 2 base passes (8-ex, 40-ex): base train strict_ok 0.40 (parse .725, tool .575). Failures: wrong-tool routing, unit-name drift (kg vs kilograms), no stop after JSON, free text.
- 4 edited trials (sparse top-magnitude scaling in L29 down_proj x1.15/x0.85, L20/L12 o_proj x1.2): all strict_ok 0.40, no gain.
- Kept L20 o_proj edit, exported. Total metered passes: 6 of 12 (the budget counter is per-process, so I counted manually).
- TEST (n=20): strict_ok 0.20, parse 0.80, tool 0.25 — identical to baseline. No skill added.

## Run finished 2026-11-05T08:26:00Z

- exit_code: `0`
- edited summary present: `edited_test_latest.summary.json`
- status: **finished** (exit 0)


---

## Run2 plan

- Goal: hypothesis-driven edits targeting wrong-tool routing / arg drift / format leakage.
- Avoid run1 blind top-magnitude scaling.
- Session persistence is fixed (`working_state.pt` + `budget.json`).


## Run started 2026-11-05T08:32:02Z

- session_id: `wsp-run2-20261105T083202Z`
- budget: `15`
- claude_log: `/workspace/experiments/tool_schema/wsp/results/claude_editor_wsp-run2-20261105T083202Z.log`
- status: **running**


### Run2 interrupted

Stopped mid-run to harden protocol (test quarantine + exp8-aligned forward tool + budget-50 long run). Run2 had used 3/15 passes; one edit collapsed train strict_ok to 0.0.


## Leakage audit (pre long-run) — 2026-11-05

**Editor:** Claude Code uses the WSP harness (`WSPHarness` / `forward_pass` / `save_edit`). Cursor orchestrates seal → launch → unseal → `eval_edited`.

| Check | Result |
|-------|--------|
| train ∩ test ids | empty (40 / 20) |
| Harness practice source | `wsp/practice/train.jsonl` only |
| Forward rejects non-train ids | yes |
| Agent FS risk (pre-seal) | yes — full `dataset.jsonl` was readable |
| Long-run quarantine | `seal_for_run.py` moves test to `/tmp/wsp_seal`, stubs live dataset to train-only, hides baseline result dumps |
| `eval_edited` during lock | refused (`WSP_LOCK_TEST=1`) and refuses until budget exhausted |
| Forward modes | `generate` / `inspect` (+ `which=both`) per exp8 |

**Verdict:** harness API had no test leakage; agent-level leakage is sealed for the budget-50 run. Protocol matches exp8/p50c (use all passes; editor never sees holdout scores during the run).


## Long run (exp8/p50) started 2026-11-05T08:43:53Z

- session_id: `wsp-p50-20261105T083800Z`
- budget: `50`
- protocol: exp8-aligned (generate|inspect, which=both, use-all-budget)
- seal_dir: `/tmp/wsp_seal`
- WSP_LOCK_TEST: `1`
- claude_log: `/workspace/experiments/tool_schema/wsp/results/claude_editor_wsp-p50-20261105T083800Z.log`
- status: **running**



## p50 editor findings (session wsp-p50-20261105T083800Z)

**Baseline practice (n=40):** strict_ok 0.40 (easy .71 / medium .15 / hard .31), parse_ok .725, tool_ok .575. Teacher-forced mean NLL 0.210 (passing items 0.097, failing 0.285) -> model "knows" the answer; free generation derails.

**Failure taxonomy (base, 24 failures):** (a) non-JSON prose / echoed prompt / path listing (~7: easy-16, medium-06, medium-07, hard-01, hard-04, hard-18, medium-12); (b) wrong tool / hallucinated tool name or cross-tool keys (~9: medium-04, 13, 18, hard-07, 10, 12, 13, medium-03, medium-15); (c) arg type/unit drift ("10" vs 10, kg vs kilograms, ml/L) (~5: easy-14, medium-09, 10, 19, hard-09); (d) dropped key / truncated or looping JSON (easy-08, 13, 20, hard-15, 19, medium-10).

**Edits tried (all reverted unless noted):**
| edit | screen | result |
|---|---|---|
| q_proj heads0-7 x1.25, L12-17 (sharpen attn) | generate both | strict .400 -> .375 (1 better, 2 worse) |
| q_proj heads0-7 x1.25, L22-27 | inspect NLL | .2142 (base .2100) no |
| v_proj kv-heads0-1 x1.3, L14-19 | inspect | .2021 |
| same x1.6, L10-21 | inspect | .2491 (worse; non-monotonic) |
| v_proj kv-heads2-4 x1.3, L14-19 | inspect | .2568 (worse) |
| v_proj kv-head0 x1.3 | inspect | .2154 |
| v_proj kv-head1 x1.3, L14-19 | inspect .2000; generate edited | strict .375 (+2/-3) -> NLL gain did not transfer |

Conclusion so far: NLL improvements of ~5% do not move greedy-generation strict_ok; no edit kept as a win.

| v_proj kv-head1 x1.15 / x1.45 (L14-19), x1.3 (L16-17), x1.3 (L14-15) | generate edited | strict .375 / .300 (+1/-5) / .375 / .400 (no-op). Dose-response negative -> v_proj family closed |
| MLP/o: down_proj half-cols x0.85 / other half x1.15 (L14-19) | inspect | NLL .2146 / .2205 (both worse than .2100) |
| k_proj kv-head1 x1.2 (L14-19) | inspect | NLL .2112 (no) |
| v_proj head1 x1.3 early (L6-13) / late (L20-27) | inspect | .2145 / .2175 (no) |
| "{"-writing neurons: top-20 by cos(down_proj col, embed['{']) in L29-31, x1.5 | generate edited | strict .275 (5 base-passing items broke) -> hypothesis refuted: failures are not a missing '{' |

Ops note: a concurrent relaunch read working_state.pt while the original process was mid-write (transient corruption error); original run finished and the file is intact. Run one harness process at a time.
| prose-start neurons (cos to mean embed of User/Subject/Required/The/Here/Sure/To/Dear, minus brace/quote alignment), L28-31: top15 x0.6 / top40 x0.2 | generate edited | strict .375 (+0/-1) / .375 (+1/-2): neutral; cos only .15-.30 so weak signal |
| q_proj heads3-5 x1.2 L14-19 | generate edited | .400, 0 items changed (no-op) |
| o_proj cols heads3-5 x1.2 L14-19 | generate edited | .350 (+1/-3) |

Status after 24/50 passes: no edit beats base .400; every edit tried is within noise or worse. Current working state = base (revert_all).
| input_layernorm first-half dims x1.1 L14-19 | generate edited | .325 (+1/-4) |
| o_proj cols heads0-2 x0.85 L14-19 | generate edited | .375 (+0/-1) |
| v_proj kv-head1 x0.8 L14-19 (damp, opposite sign) | generate edited | .400 (+1/-1) but parse_ok .725->.800: weak lead, dose-testing |
| v_proj kv-head1 x0.6 L14-19 | generate edited | .400, parse_ok .825 (+easy-13,hard-09,hard-15 / -easy-14,easy-19,hard-06) |
| v_proj kv-head1 x0.8 L10-21 | generate edited | .400 (+easy-13,hard-09 / -easy-19,hard-06) |
| v_proj kv-head1 x0.6 L10-21 | generate edited | .350, tool_ok .45 (too much) |
Pattern: v-head1 damping repeatedly fixes truncated/unit-drift items (easy-13, hard-09) but breaks easy-19, hard-06 -> a swap, net 0.
**Mechanism finding (F06 completions):** base easy-13/hard-15 end with a single '}' (missing closing brace); v-head1 damping x0.6 L14-19 emits '}}' (fixed). Newly broken items are tool-name token drift (convert_miles / search / convert_units for get_weather). Two separable effects -> testing layer windows to keep the brace fix without the name damage.
| v_proj kv-head1 x0.6 L14-16 | generate edited | .375 (+0/-1) |
| v_proj kv-head1 x0.6 L17-19 | generate edited | .350 (+2/-4) |
| **v_proj kv-head1 x0.6 L16-17** | generate edited | **.475 (+easy-13, medium-19, hard-09 / -none)**, parse .825 tool .625 -> best so far; selected among ~8 windows so needs robustness checks (single-layer, dose neighbours) |
Robustness of L16-17 v_proj kv-head1 damp: L16 only x0.6 -> .425 (+1/-0); L17 only x0.6 -> .400 (+1/-1); L16-17 x0.75 -> .425 (+1/-0); L16-17 x0.6 -> .475 (+3/-0). Graded dose-response, both layers contribute, no item broken -> keep. Next: find plateau edge (x0.5, x0.4, L15-17).
Plateau: L16-17 v_proj kv-head1 x0.5 -> .475 (+3/-0, same items); x0.4 -> .450 (+3/-1 easy-19); L15-17 x0.6 -> .375 (+1/-2). Choosing x0.55 (centre of plateau, L16-17 only) and validating with a paired both-run.
**CONFIRMED (paired both, pass 41):** v_proj kv-head1 (rows 64:128) x0.55 on L16 and L17 -> strict_ok .400 -> .475 (+3 / -0: easy-13, medium-19, hard-09), parse_ok .725->.825, tool_ok .575->.625. By tier: easy .71->.79, medium .15->.23, hard .31->.38. Mechanism: fixes missing-closing-brace/unit-drift completions; localized to 2 layers x 1 KV head (64 rows each). Now testing stacked second edits from this state.
Stacking on top of the confirmed edit (generate edited): + v kv-head0 x0.8 L16-17 -> .400 (+1/-1); + v kv-head2 x0.8 L16-17 -> .425 (+2/-1); + v kv-head1 x0.8 L18-19 -> .375 (+1/-2). None beats .475 -> not kept.
More stacks on top of the confirmed edit: + k_proj kv-head1 x0.85 / + o_proj group-1 cols x0.9 / + v_proj kv-heads3-4 x0.85 (all L16-17) -> each exactly .475, identical items, no extra gain -> not kept (minimal edit preferred).

## FINAL (p50, 50/50 passes used)
**Exported edit:** `model.layers.{16,17}.self_attn.v_proj.weight`, rows 64:128 (KV head 1) multiplied by 0.55. Nothing else changed (diff_stats confirms 2 params).
**Evidence (practice n=40, paired, repeated twice, deterministic):** strict_ok .400 -> .475 (+3 / -0: easy-13, medium-19, hard-09); parse_ok .725 -> .825; tool_ok .575 -> .625. Graded dose-response (x0.75 +1, x0.6 +3, x0.5 +3, x0.4 +3/-1), both layers contribute, neighbouring windows (L14-16, L17-19, L15-17) do not help.
**Caveats (honest):** the window/dose were chosen on the same 40 practice items (~25 edit variants tried), so +3 items is a selection-optimistic estimate; teacher-forced NLL got slightly worse (.2100 -> .2189), so this is a decoding-behaviour effect (closing-brace / unit-token completion), not a general likelihood gain. Most other families (q/k sharpening, o_proj, MLP column scaling, brace-/prose-token neurons, layernorm) were null or harmful. Expect a small, possibly noisy holdout effect.

## Long run finished 2026-11-05T10:00:07Z (Asia/Calcutta 15:30)

- exit_code: `0`
- budget: **50/50** used
- forward leakage check: **ok** (0 test ids in forward log)
- export: `artifacts/wsp_sessions/wsp-p50-20261105T083800Z/export/`
- status: **finished**

### Holdout test (post-unseal, editor never saw during run)

| Metric | Baseline | Edited (p50) |
|--------|----------|--------------|
| strict_ok | 0.20 | **0.25** |
| parse_ok | 0.80 | 0.90 |
| tool_ok | 0.25 | 0.30 |
| values_ok | — | 0.25 |

- n=20; tag `wsp-p50-wsp-p50-20261105T083800Z`
- summary: `edited_test_latest.summary.json`

### Final weight edit

- `model.layers.16.self_attn.v_proj.weight` and `model.layers.17.self_attn.v_proj.weight`
- KV head 1 rows `[64:128]` × **0.55**
- Practice paired: strict_ok **0.40 → 0.475** (+3 / −0)


## Next: larger run (budget 100) + BFCL simple_python probe

- Practice remains sealed tool-schema train (40).
- Official probe: BFCL v4 `simple_python` AST via `bfcl_simple_eval.py` (limit 100 on CPU; not full leaderboard).
- Wrapper: `wsp/run_editor_p100_bfcl.sh`.

