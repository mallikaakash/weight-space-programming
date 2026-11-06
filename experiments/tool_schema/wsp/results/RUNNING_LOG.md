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


## BFCL-native pivot 2026-11-05T14:36:03Z

- Practice = BFCL v4 simple_python train **300** (`practice/train.jsonl`)
- Holdout = remaining **100** (`eval/sealed/test.jsonl`)
- Forward metric = official AST (`strict_ok` alias)
- Budget = 100; editor = Claude Opus 5.5 `--effort high`
- Launcher: `wsp/run_editor_bfcl_native.sh`


## BFCL-native WSP run started 2026-11-05T14:39:01Z

- session_id: `wsp-bfcl-p100-20261105T143615Z`
- budget: `100`
- practice: BFCL simple_python train **300**
- holdout: BFCL simple_python test **100** (sealed)
- metric: official AST (`strict_ok`)
- editor model: `claude-opus-5-5` effort=`high`
- seal_dir: `/tmp/wsp_seal`
- WSP_LOCK_TEST: `1`
- claude_log: `/workspace/experiments/tool_schema/wsp/results/claude_editor_wsp-bfcl-p100-20261105T143615Z.log`
- status: **running**


## Editor log — session wsp-bfcl-p100-20261105T143615Z (Opus 5.5)

Plan: pass 1 = base generate on all 300 practice items (deterministic greedy → per-item base reference, so later `edited` passes are paired against it). Split practice into DEV (even ids, used to choose edits) and CONFIRM (odd ids, used only to validate a chosen edit). Lesson from p50 run: v_proj kv-head1 damp L16-17 helped homemade JSON; re-test here rather than assume.

### Pass 1 — base taxonomy (n=300, greedy): strict_ok **0.41** (123/300), parse_ok 0.973
| failure class (177) | n | example |
|---|---|---|
| positional args (first arg unnamed) | 75 | `[math.gcd(40, 50)]`, `[get_directions('Sydney', 'Melbourne', 'fastest')]` |
| wrong/hallucinated function (incl. 16 `math.` prefix, expression calls) | 40 | `[math.sqrt(base*base+height*height)]` |
| wrong value (units, sign, bool, location string) | 42 | `gravity=9.81` vs -9.81, `"New York"` vs `"New York, NY"` |
| omitted optional-but-gold param / nested type (int vs float list) | ~20 | `numbers=[12, 15]` expected floats |
| syntax error / prose | 8 | `[stats.t_test]` |
Tokenization finding: 57 failures begin the arg list with a **merged paren-value token** (`('` 52, `(['`, `("`, `([`); only 10 positional failures are digit-after-`(`.
Splits: DEV = even ids (150, base 61 ok), CONF = odd ids (150, base 62 ok); SCREEN = 91 dev items (41 positional fails + 20 other fails + 30 passes).

### Hypotheses / edits
| pass | edit | set | result |
|---|---|---|---|
| 2 | prior p50 lesson: v_proj kv-head1 x0.55 L16-17 | screen | 30→31 (+3/-2) noise → retired for BFCL |
| 3 | project out raw d = g⊙E['('']−g⊙E['('] from o_proj+down_proj L20-31 (β=1) | screen | 30→16 (+7/-21): named args appear (`math.hcf(number1=36,...)`) but d ≈ −readout('(' , ',' , '[') → first token flips to ```` ```python ```` |
| 4 | **same idea, protected-orthogonal**: subspace of 8 paren-family readouts (`('` `("` `(['` `([` `(["` `(-` `({` `((`) orthogonalized against readouts of 311 protected tokens (top-300 base-completion tokens + code/prose starters) → logits of protected tokens provably unchanged; project out of o_proj+down_proj L16-31, β=1 | screen | **30→54 (+27/-3)** |
| 5 | same edit, validation | all 300 | **0.41→0.543 (123→163, +48/-8)**; DEV 61→85 (+28/-4); **CONF (untouched) 62→78 (+20/-4)** |
Mechanism: late layers write the merged `('`-family token at the function-name position (positional start); removing that write forces `(` and the model then emits `name=`. Breaks are small value drifts (True→False, 1→1000).
| 6 | family proj **β=2 (reflection)** L16-31 | DEV | 61→73; vs current 85→73 (+7/-19): overshoot, rejected |
| 7 | family proj β=1 **L8-31** | DEV | 85 (+5/-5 swap vs current): mid layers add nothing |
| 8 | family proj β=1 **L24-31** | DEV | 84 (+4/-5 vs current): effect lives in last 8 layers; L16-31 kept (validated) |
After the edit, 0 completions use a paren-family token; residual positional = 9 digit-after-`(` (`math.gcd(12, 15)`). Remaining failures (137/300): value_err 64 (53 required-param semantic, 11 hallucinated optional), wrong_func 31 (renamed/hallucinated names, 9 `math.` prefix, system-example copy `[math.factorial(number=5)]`), missing_param 15, type 12, syntax 9.
| 9-13 | + v_proj kv-group g ×1.3 L20-31 (g=0..4), hypothesis: amplify name-copying attention | DEV vs current 85 | 83 / 84 / 84 / 83 / 84 (each ~3-6 fixed / 4-7 broken) → closed. **Noise floor:** any small perturbation swaps ~8-12 of 150 items; |net| ≤ 4 on DEV is noise. |
| 14 | + **bool readout shear** W←W+α·d̂ b̂ᵀW (o_proj+down L24-31, α=1); d=True−False readout, b=True+False readout, both orthogonalized vs 309 protected tokens | 37 bool-schema items vs current | **22→26 (+5/−1)**; dev 8→10, conf 14→16; changes = False→True flips (formatted, equal_variance, avoid_tolls, format_as_ratio, standardize). Kept (α not tuned). |
| 15 | + programmed layer-0 neuron #1983: gate=up=k·u (protected-orthogonal '(' detector: '(' 1.38, family ≤0.72, protected tokens 0), down = −4·ŵ(digits) — hypothesis: suppress digit after '(' (`math.gcd(12, 15)`) | 9 digit-positional + 50 dev passes | 0/9 fixed, 7 broken (`math.density`, `math.sqrt(...)` hallucinations — '(' also occurs in system-prompt examples) → refuted/abandoned |
| 16 | **current = family projection + bool shear**, full reference | all 300 | **167/300 = 0.557** (base 0.41; +51/−7 vs base); vs projection-only +7/−3; dev 85→87, conf 78→80; only 16 non-bool completions changed (net ≈0) |
| 17-18 | + 8 strongest late OV-copy heads (static copy score; L31h14,L29h10,L31h10,L30h10,L31h2,L29h14,L26h5,L30h12) o_proj cols ×1.25 / ×1.6 | DEV vs current 87 | 87 (+2/−2) / 87 (+4/−4) → swap noise, closed |
| 19 | + project out protected-orthogonal **`math` readout** (L16-31, β=1). Hypothesis: 11/20 `[math...` outputs are hallucinations copied from the system example `[math.factorial(number=5)]` (wrong_func diverges at FIRST name token in 32/34) | 20 math-start/math-gold items + 30 dev passes | 32→39 (+10/−3): hallucinations fixed, but true math.factorial → copies other system example; math.gcd → `[import math]` (too strong) |
| 20 | same, **β=0.5** | same screen | **32→42 (+10/−0)**; all genuine math.* names preserved (gcd/hypot/factorial/pow/hcf) |
| 21 | **current3 = family proj + bool shear + math proj β=0.5**, full | all 300 | **176/300 = 0.587** (base 0.41; +62/−9 vs base); vs current2 +11/−2; dev 87→91, conf 80→85; non-screen 250 items 135→134 (no side effects) |
| 22-23 | family proj β=1.25 / β=0.75 (rest of current3 fixed) | DEV vs current3 91 | 90 (+1/−2) / 92 (+2/−1) → flat plateau around β=1; keep β=1 |
| 24 | '(' detector neuron again, α=12, on top of current3 | 9 digit-pos + 50 guard | 0/9 changed at all, 3 broken → early-layer conditional write does not reach the decision; closed |
| (no pass) | bias toward fewer optional params? 96 passes give optional params, 39 of them need them → would break more than fix; not tried |
| 25 | multi-pair quote shear ('→" for 11 quote-token pairs, L24-31 α=1) to fix apostrophe syntax errors (211, 216) | 2 + 52 single-quote passes | **52→6**: openers flip to `"` but closers stay `'` (`to="john.doe@example.com'`) → quote style is context-coupled, closed |
| 26-27 | bool shear α=0.5 / α=2 | 37 bool items vs current3 26 | 26 / 26, identical items → flat plateau, keep α=1 |
| 28-29 | math proj β=0.35 / β=0.7 | math screen vs current3 42 | 42 / 42, identical items → flat plateau, keep β=0.5 |
| 30-31 | localization: family proj on **o_proj only** / **down_proj only** (L16-31) | DEV vs current3 91 | o-only **77** (+3/−17) / down-only **93** (+3/−1, incl. digit-pos item 20 fixed) → the `('`-family token is written by late **MLPs** |
| 32-33 | bool shear o_proj only / down_proj only | 37 bool vs 26 | 27 (+1/−0, fixes the one earlier break 137) / 26 → both carry it |
| 34-35 | math proj o only / down only | math screen vs 42 | 41 / 41 (each loses item 14) → both needed |
| 36 | minimal combo: family proj down-only + bool shear o-only + math both | all 300 | 181/300 (+11/−6 vs current3); conf 85→92, dev 91→89; bool 25 (o-only shear loses formatted=True) |
| 37 | **current4 = family proj down_proj only (L16-31, β=1) + bool shear o+down (L24-31) + math proj o+down (L16-31, β=0.5)** | all 300 | **185/300 = 0.617** (base 0.41); dev 93 (reproduces pass-31 DEV 93), conf 92 (base 62), bool 26 |
| 38-39 | current4 with family proj down-only restricted to L24-31 / β=1.5 | DEV vs current4 93 | 92 (+5/−6) / 89 (+1/−5) → keep L16-31 β=1 |
| (no pass) | leading-space hypothesis for ` lawsuit`→`s`+`ue`: protected-orthogonal mean(R[' w']−R['w']) over 5739 pairs is dominated by capitalized sentence-start tokens; ` lawsuit` z=0.37 → not a targeted lever, dropped |
| 40 | close→continue readout shear (`)]`→`,`, `')]`→`',`, `")]`→`",`), α=0.3, L24-31 | DEV vs current4 93 | 84 (+7/−16): fixes exactly the early-closers (90,110,156,160 now include data_field/location/details/info_type) but adds hallucinated params elsewhere → calibration already near-optimal; closed |
| 41 | inspect (teacher-forced NLL of gold call), which=both, current4 | 100 items (50 dev + 50 conf) | mean NLL **0.254 → 0.230 (−9.4%)**, 78/100 items improve → edits raise gold likelihood broadly, not just a greedy-decoding artifact (contrast p50 edit: NLL worse) |

## BFCL-native RESUME 2026-11-05T18:53:18Z
- session_id: `wsp-bfcl-p100-20261105T143615Z`
- seal_dir: `/tmp/wsp_seal`
- model: `claude-opus-5-5` effort=`high`
- CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS: `0`
- status: **finished** (100/100, exported)

| 42-48 | (pre-interrupt, reconstructed) **localization sweep**: zero o_proj cols of one KV group (3 q-heads) in 4-layer block, on top of current4 | abl_screen (87 items; ref current4 = 30 ok) | L20-23 g0..g4: 23/21/24/26/14 (−7..−16 net each; ~13-21 broken) → mid-late attention in L20-23 is **necessary** for every group (copying args/names); L24-27 g0: 32 (+5/−3), g1: 32 (+5/−3) → within swap noise. Sweep (L24 g2-4, L28 g0-4) **stopped**: ablation is not a constructive lever and noise floor is ±4. |
| 49 | + q_proj rows ×1.25 (attention sharpening) on 7 mid-layer copy heads (L19h9, L22h3/h9/h11, L23h2/h3/h9; static OV-copy score) — hypothesis: more faithful name/arg copying | DEV vs current4 93 | **91** (+0/−2); only 9/150 completions changed → nearly inert; closed |
| (no pass) | **new diagnosis: tokenizer space-boundary copy failure.** Prompt has `Function name: lawsuit_info` → first token `Ġlawsuit`; output after `[` needs no-space `law`+`su`+`it`. Items whose first name token cannot be reused verbatim ("boundary mismatch", 60/300): wrong_func **12/60 (20%)**, strict 45%; reusable first token (240): wrong_func 9/240 (3.8%), strict 66%. All 6 `lawsuit*`-initial names fail (`[sue_details`, `[lucas_search`). Scorer accepts `[ lawsuit_info(...)]` (checked offline with bfcl_score on gold row; BFCL also strips spaces in string compare). |
| 50 | + project out protected-orthogonal **space-ness** readout s = mean(R['Ġw']−R['w']) over 4565 vocab lowercase word pairs (vocab-wide, not practice-derived), o+down L16-31, β=1 | space_screen (60 hazard + 40 dev-pass guard; ref 67) | 61 (+6/−12): fixes exactly as predicted (`[ lawsuit_info(`, `[ lawsuit.check_case(`, `[ lawsuit_details.find(`, `detailed_weather_forecast`), but 48/100 completions changed — value truncation, `[EMFI]` loop → overdosed |
| 51 | space projection β=0.5 (o+down L16-31) | space_screen vs 67 | 66 (+2/−3; 20 changed): fixes 184 `[ lawsuit.check_case`, 233 `[ european_history...`; breaks = multi-word value truncation (`'ATP synthase'`→`'ATP'`, `'Yellowstone National Park'`→`'Yellowstone'`) → late layers write +space inside values and −space at name start; symmetric projection removes both → localize |
| 52 | space proj o_proj only β=1 L16-31 | space_screen vs 67 | 64 (+1/−4): no name fixes, value truncation (58, 68) |
| 53 | space proj down_proj only β=1 L16-31 | space_screen vs 67 | 60 (+6/−13): carries **all** name fixes (176,184 lawsuit, 185, 233, 299 `musical_scale`) and most damage (`[ sculpt_locator`, `[EMFI]`, value drift) |
| 54 | space proj down only L24-31 β=1 | space_screen vs 67 | 63 (+7/−11): all name fixes (176,182,184,185,233,299,45) + same breaks |
| 55 | space proj down only L16-23 β=1 | space_screen vs 67 | 67 (+0/−0, identical) → effect lives entirely in L24-31 MLPs |
| 56 | space proj down only L28-31 β=1 | space_screen vs 67 | 64 (+6/−9; 43 changed): all name fixes; damage = **space after `_` inside names** (`calculate_ electric_field_strength`, `locate_ tallest_ mountains`), paraphrase competition once a space is allowed (`[ invest_stock_profit`, `[ hypothesize_test`); guard 6/40 broken |
| 57 | space proj down only L24-27 β=1 | space_screen vs 67 | 64 (+0/−3): value truncation only (58,68,124) → L24-27 = "continue multi-word value" writes, L28-31 = "no space after `[`/`_`" writes |
| 58 | space proj down only L28-31 β=0.5 | space_screen vs 67 | 66 (+3/−4: 176,184,233 fixed; 41,58,68,124 broken) → **space lever closed**: mechanism confirmed but "no space after `[`" is the same late-MLP signal as "no space after `_`"; not separable by a linear readout projection. Items 58/68/124 are fragile (break under most perturbations). |
| (no pass) | "close call earlier" (inverse of pass 40)? Offline count on current4: 10 fails fixable by dropping an invented optional (`category='Drama'`, `location='global'`, `dividends=True`) vs **40 passing items whose gold needs a schema-optional param** the user mentioned → context-dependent; not tried |
| (no pass) | other `(`-merged tokens (69 in vocab, e.g. `()`, `({'`, `([[`): base used only `('`53 `(['`2 `("`1 `([`1; current4 uses plain `(` in 300/300 → extending family = risk without measurable benefit; skipped |
| 59 | robustness: family proj built with protected set k=150 (instead of 300) | DEV vs current4 93 | 91 (+1/−3, 20 changed, 0 family tokens) → effect stable |
| 60 | family proj with k=600 | DEV vs 93 | 88 (+7/−12): over-protection weakens the edit (`('` returns in 3 completions, `math.hcf(36, 24)` positional again) → k=300 kept |
| (no pass) | neuron-level separation of `[`-start vs `_`-continuation space suppression (L28-31 down cols by space-loading × gate·E['['] vs gate·E['_']): selectivities co-vary (generic punctuation reading) → no clean subset; space line closed |
| (no pass) | string-value calibration on current4 failures: truncated 13 (5× city without state: `'Chicago'` vs `'Chicago, IL'`; `'M'` vs `'monthly'`) vs over-extended 4 (`'Louvre Museum in Paris'`); 52 passing multi-word string values at risk |
| 61 | close-string→comma-in-string shear (`',`→`,`, `",`→`,`), α=0.3, L24-31 | DEV vs 93 | 91 (+3/−5; 27 changed): city/state completion works (`'New York, NY'`, `'Seattle, WA'`) but generic comma boost adds unit params (`radius=10, units='meters'`) and bare-identifier args (`math.hcf(number1, number2)`) → closed |
| 62 | **component ablation**: current4 minus bool shear | all 300 vs current4 185 | **177** (+2/−10): dev 93→87, conf 92→90, bool items 26→22 → bool shear contributes ≈ +8 |
| 63 | **component ablation**: current4 minus math projection | all 300 vs 185 | **169** (+0/−16); wrong_func 21→36 → math proj contributes ≈ +16 (system-example `math.factorial` copying returns) |
| 64 | **component ablation**: current4 minus family projection | all 300 vs 185 | **141** (+7/−51): dev 93→68, conf 92→73 → family proj contributes ≈ +44 (main effect). Attribution: family +44, math +16, bool +8 (sum > +62 total → components interact positively) |
| 65 | prior p50 lesson (v_proj kv-head1 ×0.55 L16-17) re-tested **on top of current4** | DEV vs 93 | 91 (+2/−4) → does not transfer to BFCL; retired (second time) |
| 66 | `,`→`=` protected-orthogonal shear α=0.2 L24-31 (fix bare-identifier positional `(group1, group2, …)`) | DEV + 4 conf id-positional (154) vs 93 | 93 (+1/−1; only 12 changed): 19 `math.gcd(num1=40, num2=50)` fixed; 120/123 now `group1=array(3, 4, …)` (named, but value written as call) |
| 67 | `,`→`=` shear α=0.4 | same 154 vs 93 | 94 (+3/−2; 22 changed): extra fixes (40,188) come from earlier call closing (lower `,`), which also drops needed optionals (132,172); list args become `group1=array(3, …)` because the model emits bare `=` instead of merged `=[` → noise-level |
| 68 | `,`→{`=`, `=[`} shear α=0.3 (tokenizer: list values open with merged `=[`) | same 154 vs 93 | 95 (+5/−3): **targeted fixes** 120 `group1=[3, 4, 5, 6, 4]`, 119 `sample1=[22,…]`, 19 `math.gcd(num1=40, num2=50)`; breaks (74,132,172) = calls closed early because `,` logit drops |
| 69 | **eq-boost, comma kept**: write dirs for `=`,`=[` orthogonal to protected AND to `,` readout; trigger = `,` readout; α=0.3 L24-31 o+down | same 154 vs 93 | 95 (+4/−2; 14 changed): 120,119,19 fixed + 158; early-closing breaks gone; new minor side effect: bare `=` beats merged `='` → unquoted strings (`case_number=XYZ123`, already-failing items); DEV-only +2/−2 |
| 70 | eq-boost α=0.3 on full **CONF** (146/150 untouched by design) | CONF vs current4 92 | 93 (+3/−2): fixes 19, 119, 65; breaks 169 `docket_number=123456`, 255 `papal_name=Innocent3` = bare `=` outcompeting merged `='` (quote dropped); 147/299 now pick the right function name |
| 71 | **eq-dual**: one write vector giving equal +1 logit to all 7 value openers (`=`,`=[`,`='`,`="`,`={`,`=-`,`=(`; dual basis), 0 to protected + `,`; trigger `,`; α=0.3 L24-31 | 154 vs 93 | 95 (+4/−2; only 9 changed): 120,119,19,158 fixed, quote-dropping gone; breaks 208, 212 (value drift); DEV-only +2/−2 |
| 72 | eq-dual α=0.3 on full CONF | CONF vs 92 | 93 (+3/−2): 19, 65, 119 fixed; 169, 297 broken (value drift) → all-300 estimate ≈ +1 = not a clear paired gain; not adopted at α=0.3 |
| 73 | eq-dual α=0.2 | **all 300** vs 185 | 187 (+4/−2): fixes 120, 119, 19 (targeted, reproduce at every dose/variant) + 65; breaks 208, 212 (fragile items, also broke under passes 59/61/69). On items not used to design it: DEV +1/−2, CONF\screen +1/−0 → **not a clear paired gain; documented, not adopted** |
| 74 | amplify space-ness in late attention outputs (o_proj L24-31, ×2 along ŝ; MLPs untouched) | space_screen vs 67 | 67 (3 changed) → inert |
| 75 | same, ×5 along ŝ | space_screen vs 67 | 66 (+2/−3; 26 changed): no name fixes (lawsuit items drift to `lucid_search`, `santa_calif_sue_search`) → attention-side space amplification refuted; **space-boundary class closed** |
| 76-78 | **null-edit noise calibration** on top of current4: random protected-orthogonal direction projected out β=0.5 o+down L16-31 (seeds 1, 2; same geometry as math proj) and random protected-orthogonal shear α=1 L24-31 (same geometry as bool shear) | all 300 vs 185 | **185 (+1/−1, 8 changed) / 182 (+2/−5, 16 changed) / 180 (+1/−6, 18 changed)** → a random edit of this size costs ≈ −3 and never fixes >2. Component contributions (family +44, math +16, bool +8) are far outside the null range; eq-dual (+4/−2) is just above it. |
| 79 | inspect (teacher-forced gold NLL), which=both, current4 | all 300 | **0.2733 → 0.2463 (−9.9%)**; improved on **250/300**; DEV 125/150, CONF 125/150 (identical) → gold likelihood rises broadly on held-aside items |
| (rule, pre-registered) | adopt eq-dual α=0.2 only if gold NLL vs current4 falls on mean AND >60% items on BOTH dev and conf, and a same-size null edit does clearly worse (~50%) |
| 80 | inspect gold NLL: eq-dual α=0.2 vs current4 | all 300 | 0.2463 → 0.2464; improved 123/300 (dev 59, conf 64) → **fails rule; eq-dual rejected** (its greedy +2 was boundary noise) |
| 81 | NLL screen: family β=1.25 | all 300 vs current4 | 0.2463→0.2459; improved 145/300 (dev 63, conf 82) → flat |
| 82 | NLL screen: math β=0.7 | all 300 | 0.2463→0.2465; improved 214/300 but mean worse (few items much worse) → fails |
| 83 | NLL screen: bool α=2 | all 300 | 0.2463→0.2488 (worse); 188/300 → fails |
| 84 | NLL screen: family L12-31 | all 300 | 0.2463→0.2463; 150/300 → flat |
| 85 | NLL screen: family β=0.75 | all 300 | 0.2463→0.2481 (worse), 126/300 |
| 86 | NLL screen: math β=0.35 | all 300 | 0.2463→0.2470 (worse), 75/300 |
| 87 | NLL screen: bool α=0.5 | all 300 | 0.2463→0.2449, but only 108/300 improve → mixed; current4 at local NLL optimum on all three dose axes |
| 88 | NLL screen: **null** random protected-orthogonal projection (seed 2, β=0.5) | all 300 | 0.2463→0.2452; improved **199/300** although its greedy accuracy is −3 (pass 77) → protected-orthogonal projections generically lower gold NLL (they drain rare-token mass; gold calls are mostly protected tokens). The pre-registered "majority improves" rule is therefore weak; current4's −9.9% (pass 79) is ~20× the null's −0.45% and stands, but its "250/300" is partly generic. |
| 89-92 | single-layer space projection (down_proj only, β=1) L28 / L29 / L30 / L31 | space_screen vs 67 | 66 (1 changed) / 65 (3) / 67 (7) / **66 (+6/−7, 34 changed)** → the entire space-boundary effect lives in the **L31 MLP**: all 6 name fixes, but also 3 `_ ` artifacts + paraphrase breaks |
| 93 | **neuron-level**: project ŝ out of only 5 L31 down cols with most negative space-loading (n1081, n2327, n1329, n2417, n791) | space_screen vs 67 | **68 (+1/−0; only 2 changed)**: `[ lawsuit.check_case(` fixed, no `_ ` artifacts |
| 94 | neuron-level space proj, top-20 negative L31 cols | space_screen vs 67 | 68 (+2/−1; 9 changed): 184 + 233 `[ european_history…` fixed; 15 now `[integrate(` (value still wrong); 58 broken (fragile) |
| (rule, pre-registered) | adopt a neuron-level variant only if on all 300: net ≥ +1 AND zero breaks outside the 100-item space_screen |
| 95 | neuron-level space proj top-5 L31 | **all 300** vs 185 | **182 (+1/−4)**; conf 92→89; 15 completions changed outside the screen (`museo_working_hours.get`, `generate_law_contract(John='John', …)`) → fails rule; **rejected**; top-20 not run. Space-boundary failure remains open. |
| 96 | **family-specificity control**: current4 with the family subspace replaced by a random 8-dim protected-orthogonal subspace (seed 11), down_proj L16-31 β=1 | all 300 | **154** (vs no-family 141, real family 185): dev 81, conf 73 → ≈ +13 of the family's +44 is a generic "drain rare-token mass" effect; ≈ +31 is specific to the merged-paren readouts |
| 97 | family-specificity control, seed 12 | all 300 | **135** (below no-family 141). **Correction to pass 96:** `('`-family completions: no-family 54, seed-11 19, seed-12 57, real family 0 → seed 11 partially aligned with the family by chance. Accuracy tracks family-token suppression (141/54, 154/19, 135/57, 185/0); random subspaces give no reliable generic gain (−6…+13) → **family effect is specific** |
| 98 | **math-specificity control**: math projection replaced by random protected-orthogonal 1-dim projection (β=0.5, o+down L16-31) | all 300 | **166** (no-math 169, real math 185); math_set 3/20 (real 13/20) → math effect is specific |
| 99 | **bool-specificity control**: bool shear replaced by random protected-orthogonal shear (α=1, o+down L24-31) | all 300 | **179** (no-bool 177, real bool 185); bool items 22 (real 26) → bool effect is specific |
| 100 | **final paired confirmation** `which="both"`, current4 | all 300 | **base 123 → edited 185 (0.410 → 0.617)**, +69/−7; DEV 61→93 (+36/−4), CONF 62→92 (+33/−3); completions byte-identical to pass 37 (deterministic) |

## FINAL — session wsp-bfcl-p100-20261105T143615Z (100/100 passes, exported)

**Exported edit = current4** (32 tensors: `o_proj` + `down_proj`, layers 16-31; no embed/lm_head/norm; verified export == fresh rebuild, max diff 0.0). All three parts are closed-form protected-orthogonal readout edits: they leave the logits of 311 protected tokens (top-300 base-completion tokens + code/prose starters) untouched, so only the targeted tokens move.
1. **Merged-paren family projection** — down_proj L16-31, β=1: removes late-MLP writes along the readouts of `('`, `("`, `(['`, `([`, `(["`, `(-`, `({`, `((`. Mechanism: the model began positional arg lists with a merged paren+value token; blocking it forces `(` then `name=`. Contribution ≈ **+44**.
2. **System-example `math` projection** — o+down L16-31, β=0.5: stops hallucinated `[math.factorial(number=5)]`/`math.*` copies of the system-prompt example while keeping genuine `math.gcd`/`math.hypot`. Contribution ≈ **+16**.
3. **Bool shear** — o+down L24-31, α=1: when the residual reads "bool", tilt toward `True` (fixes under-set flags such as `equal_variance`, `avoid_tolls`). Contribution ≈ **+8**.

**Evidence:** practice strict_ok (official BFCL AST) **0.410 → 0.617** on all 300; gain is the same on the held-aside CONF half (62→92), which was not used to design edits 1-3; gold-call NLL −9.9 %. Specificity controls replacing each part with a random edit of identical geometry: family 135-154 (vs 185; accuracy tracks `('`-suppression), math 166, bool 179; random edits added on top of current4 cost 0 to −5. Dose plateaus: family β 0.75-1.25, k_protect 150-300, bool α 0.5-2, math β 0.35-0.7 are all ≤ current4.

**Tried and rejected after resume (passes 42-99):** kv-group ablations (diagnostic only); q-sharpening of copy heads (inert); space-boundary projection (mechanism confirmed — `[ lawsuit_info(` — but same L31-MLP signal also suppresses spaces after `_`; not separable by layer or by top-k neurons, all-300 182); string continuation / comma shears (comma is shared by "continue string" and "continue call"); `,`→`=`/`=[` eq-boost and eq-dual (targeted positional fixes 19/119/120 reproduce, but +4/−2 overall, flat NLL → not adopted); prior p50 v_proj lesson (does not transfer, twice).

**Open failure classes (115/300 remain):** semantic value errors 56 (gold-idiosyncratic strings, units, percent vs fraction), tokenizer space-boundary function names (~12; e.g. all `lawsuit*` names), bare-identifier positional args (~6), schema-optional params needed/hallucinated (~19), int-vs-float list types (~3).

**Expected holdout effect:** holdout = 100 sealed items from the same BFCL simple_python distribution. The two failure modes the edit fixes (merged-paren positional starts, system-example copies) are distribution-wide and the CONF half improved as much as the DEV half, so a similar ~+15-20 pt gain is plausible; it has wide uncertainty at n=100 (±~7 pt), and DEV/CONF were both used for some variant comparisons, so the practice number is mildly optimistic. Not scored here (sealed).

## BFCL-native resume finished 2026-11-05T23:55:42Z
- exit_code: `0`
- edited_state: `/workspace/artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt`
- status: **finished** (exit 0)


### Holdout test (post-unseal, editor never saw during run)

Session `wsp-bfcl-p100-20261105T143615Z` — official BFCL v4 `simple_python` AST via `bfcl_eval.ast_checker`, offset=300, limit=100.

| condition | n_correct / n | AST accuracy |
|---|---|---|
| base (pre-WSP) | **33 / 100** | **0.33** |
| edited (`current4` export) | **50 / 100** | **0.50** |

Paired: **+19 / −2** (net **+17**). Merged-paren family tokens in completions: base **24 → edited 0**.

Artifacts:
- base: `experiments/tool_schema/results/bfcl/bfcl-holdout-base-pre-wsp-bfcl-p100-20261105T143615Z_*`
- edited: `experiments/tool_schema/results/bfcl/bfcl-holdout-edited-wsp-bfcl-p100-20261105T143615Z_*` (timestamp `20261105T235817Z`)
- edited_state: `artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt`

Holdout gain (+17 pt) matches the pre-registered ~+15–20 pt expectation from practice CONF generalization.
