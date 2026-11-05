# X thread: WSP on SmolLM2 / BFCL (in @malliktwts voice)

Session `wsp-tweet-thread-20261106T070656Z` · 2026-11-06

This replaces the rejected draft at `/opt/cursor/artifacts/wsp_tweet_charts/THREAD.md`. The facts are the same and the voice is new.

## What was wrong with the rejected draft (voice, not facts)

- Every post opened with a label ("Aim (honest):", "Dataset:", "Method:", "Caveats I'm not soft-pedaling:"), so it read like a slide deck cut into tweets.
- It stacked slogans: "No fine-tuning. No gradients. No extra training data." / "Expression surgery. Not knowledge infusion." / "Useful middle ground between…". That's founder-launch energy.
- The opener was a template: "I took X, made it better… Thread:" plus a 👇.
- Nearly every post was a bullet or numbered list with the same rhythm, so nothing read as thinking out loud.
- The humility was staged ("Not claiming a leaderboard win", "not soft-pedaling") instead of stating the caveat plainly.
- It had none of his words: FAFO, "tbh", "I dunno how to explain this…", "the dump", "semantic leftover", ellipses.

What changed: no labels, one short list in the whole thread (the three edits in 7/17), spoken rhythm, his words, and caveats written as plain statements ("that +200% is 1 → 3 items lol").

## Charts

All four are in `/opt/cursor/artifacts/wsp_tweet_charts/`:

| post | attach |
|---|---|
| 8/17 | `01_simple_python_practice_holdout.png` |
| 11/17 | `02_crossfmt_base_vs_edited.png` |
| 13/17 | `03_fused_paren_failure_mode.png` |
| 14/17 | `04_transfer_vs_no_transfer.png` |

Optional: also put `01_…` on 1/17 if you want an image on the opener. The 1/17 text works without one.

Character counts use X's weighted length: `→`, `…`, `≈` count as 2 and the URL counts as 23. Every post is ≤ 280. The `n/17` numbers are headers only; they aren't in the post text, so add them yourself if you want numbered posts (+5–6 chars, and every post still fits).

---

## Thread (one block = one post)

### 1/17 · 269 chars

```
ok so I've been FAFO-ing with weight-space programming for a bit and finally have numbers worth posting

took SmolLM2-360M-Instruct, didn't fine-tune it at all, just edited a few of its weight matrices directly (well… Claude did)

BFCL sealed holdout: 33/100 → 50/100
```

### 2/17 · 261 chars

```
idea is from "Sparks of Weight-Space Programming" (Takehi et al.)

you give an editor model a budget of forward passes on practice examples. it stares at the failures, writes small closed-form weight edits, keeps what helps, bins the rest. no gradients anywhere
```

### 3/17 · 250 chars

```
why I even tried this… wanted to see if a tiny model can get better at tool calls with zero SFT/RL, and if yes, what it's actually fixing

like is it learning something or just getting unblocked. that second q ended up being the interesting part tbh
```

### 4/17 · 254 chars

```
benchmark: BFCL v4 (bfcl-eval==2025.10.27.1), only the simple_python category. 400 items, each one = emit ONE python call with the right name, named args, values

split by file order, first 300 practice, last 100 holdout. official AST checker for scoring
```

### 5/17 · 241 chars

```
holdout stayed sealed the whole time (WSP_LOCK_TEST), quarantined till the editor burned its budget. it never saw a single holdout item

editor = Claude Opus 5.5, high thinking, 100 metered practice forwards. that's the entire "training" lol
```

### 6/17 · 250 chars

```
loop is pretty dumb in a good way: look at failures, guess the mechanism, try a small edit, score on practice, keep / dial / bin

a lot got binned. space-in-name fixes, forcing more `=`, an old edit from a prior run… helped a few items, broke others
```

### 7/17 · 271 chars

```
what survived is a 3-edit stack, current4. 32 late tensors, o_proj/down_proj in layers 16-31:

- project out fused paren tokens like (' and ("
- tone down copying the sys prompt's math.factorial demo
- shear boolean flags toward True

~216MB delta. a patch, not a retrain
```

### 8/17 · 214 chars · (attach: 01_simple_python_practice_holdout.png)

```
numbers on simple_python:

practice 123/300 → 185/300 (0.410 → 0.617, +50.4% rel, +69/-7 flips)
holdout 33/100 → 50/100 (+51.5% rel, +19/-2)

fused paren openings on holdout went 24 → 0. that one edit did a LOT
```

### 9/17 · 270 chars

```
ok now the dump, the honest version. I dunno how to explain this without underselling it but… the gains are mostly formatting bottlenecks getting fixed. basically a better policy for how to write the call

not new knowledge. not some emergent ability the base never had
```

### 10/17 · 264 chars

```
and not the semantic leftover either. by that I mean stuff that was already wrong before any edits: wrong values, mangled names, bad optional-arg picks. edits didn't clearly clean that up

model was already close on a lot of these, it just kept fumbling the syntax
```

### 11/17 · 250 chars · (attach: 02_crossfmt_base_vs_edited.png)

```
then the obvious q… current4 was tuned ONLY on simple_python practice. does any of it carry to other BFCL formats?

ran base vs edited on the full sets of simple_java, simple_javascript, multiple, parallel, parallel_multiple. eval only, no new edits
```

### 12/17 · 250 chars

```
multiple (pick 1 of N functions): 0.290 → 0.395, +36.2% rel, +26/-5, p≈2e-4. that one's real

java 0.05 → 0.08, js 0 → 0.02, parallel 0.020 → 0.015, parallel_multiple 0.005 → 0.015. all n.s., all basically floor

nothing regressed significantly
```

### 13/17 · 244 chars · (attach: 03_fused_paren_failure_mode.png)

```
why multiple moved: the fused paren fix just… transferred. fused openings 81 → 0 on simple_python, 36 → 0 on multiple

multiple missing_required went 34 → 9 bc base wrote positional args and edited writes named ones. that's most of the gain
```

### 14/17 · 214 chars · (attach: 04_transfer_vs_no_transfer.png)

```
what didn't move: parallel. wrong_count is 171/200 for BOTH models, still emits one call when it needs several

which makes sense, the edits fix call syntax, not the decision to emit more calls. never targeted that
```

### 15/17 · 205 chars

```
one small L: java demo-copying went UP, 28 → 35

the anti-copy edit learned "don't paste math.factorial", not "don't paste demos" in general. it's hidden in the accuracy column bc java is near zero anyway
```

### 16/17 · 271 chars

```
caveats so this doesn't get misread: custom prompt protocol (not the official leaderboard setup), one small model, one greedy run, skipped live / multi-turn / web / memory

and near-floor cats make relative % look wild. that +200% on parallel_multiple is 1 → 3 items lol
```

### 17/17 · 252 chars

```
so yeah… what WSP bought here is unblocking how the model writes stuff it already almost had. not teaching it tools. still kinda goated that 100 forwards + closed-form edits gets you this far

harness, edit ledger, full tables:
https://github.com/mallikaakash/weight-space-programming
```

---

## Fact check (every number in the thread → source)

| claim in thread | source |
|---|---|
| holdout 33/100 → 50/100, +51.5% rel, +19/-2 | `CROSSFMT_BASE_VS_EDITED.md` main table; README results |
| practice 123/300 → 185/300 (0.410 → 0.617), +50.4% rel, +69/-7 | same |
| holdout fused parens 24 → 0 | README results |
| bfcl-eval==2025.10.27.1, simple_python 400 = 300 practice + 100 holdout, file order, official AST checker | README "Dataset and scope" |
| Claude Opus 5.5 high thinking, 100 metered practice forwards, holdout sealed (`WSP_LOCK_TEST`) | README / run brief |
| current4: 32 late tensors, o_proj/down_proj L16-31, fused-paren projection, math.factorial demo attenuation, boolean shear toward True, ~216MB delta | README "What we changed"; run brief |
| rejected ideas: space-in-name, force more `=`, older edit | README "What we changed" |
| multiple 0.290 → 0.395, +36.2%, +26/-5, p≈2e-4 | `CROSSFMT_BASE_VS_EDITED.md` (p = 1.9e-4) |
| java 0.05 → 0.08, js 0 → 0.02, parallel 0.020 → 0.015, parallel_multiple 0.005 → 0.015, all n.s. | same |
| fused openings 81 → 0 (simple_python, all 400), 36 → 0 (multiple) | same, "What transferred" |
| multiple missing_required 34 → 9 (positional → named args) | same |
| parallel wrong_count 171/200 both | same |
| java demo-copy 28 → 35 | same |
| parallel_multiple +200% = 1 → 3 items (of 200) | same |

Interpretation (9/ and 10/) follows the README's own framing: formatting bottlenecks / call-writing policy, not new knowledge, not emergent ability, not a clear cleanup of the semantic leftover.

---

## Whole thread, plain (for pasting into a drafts app)

1/17
ok so I've been FAFO-ing with weight-space programming for a bit and finally have numbers worth posting

took SmolLM2-360M-Instruct, didn't fine-tune it at all, just edited a few of its weight matrices directly (well… Claude did)

BFCL sealed holdout: 33/100 → 50/100

2/17
idea is from "Sparks of Weight-Space Programming" (Takehi et al.)

you give an editor model a budget of forward passes on practice examples. it stares at the failures, writes small closed-form weight edits, keeps what helps, bins the rest. no gradients anywhere

3/17
why I even tried this… wanted to see if a tiny model can get better at tool calls with zero SFT/RL, and if yes, what it's actually fixing

like is it learning something or just getting unblocked. that second q ended up being the interesting part tbh

4/17
benchmark: BFCL v4 (bfcl-eval==2025.10.27.1), only the simple_python category. 400 items, each one = emit ONE python call with the right name, named args, values

split by file order, first 300 practice, last 100 holdout. official AST checker for scoring

5/17
holdout stayed sealed the whole time (WSP_LOCK_TEST), quarantined till the editor burned its budget. it never saw a single holdout item

editor = Claude Opus 5.5, high thinking, 100 metered practice forwards. that's the entire "training" lol

6/17
loop is pretty dumb in a good way: look at failures, guess the mechanism, try a small edit, score on practice, keep / dial / bin

a lot got binned. space-in-name fixes, forcing more `=`, an old edit from a prior run… helped a few items, broke others

7/17
what survived is a 3-edit stack, current4. 32 late tensors, o_proj/down_proj in layers 16-31:

- project out fused paren tokens like (' and ("
- tone down copying the sys prompt's math.factorial demo
- shear boolean flags toward True

~216MB delta. a patch, not a retrain

8/17   [attach 01_simple_python_practice_holdout.png]
numbers on simple_python:

practice 123/300 → 185/300 (0.410 → 0.617, +50.4% rel, +69/-7 flips)
holdout 33/100 → 50/100 (+51.5% rel, +19/-2)

fused paren openings on holdout went 24 → 0. that one edit did a LOT

9/17
ok now the dump, the honest version. I dunno how to explain this without underselling it but… the gains are mostly formatting bottlenecks getting fixed. basically a better policy for how to write the call

not new knowledge. not some emergent ability the base never had

10/17
and not the semantic leftover either. by that I mean stuff that was already wrong before any edits: wrong values, mangled names, bad optional-arg picks. edits didn't clearly clean that up

model was already close on a lot of these, it just kept fumbling the syntax

11/17   [attach 02_crossfmt_base_vs_edited.png]
then the obvious q… current4 was tuned ONLY on simple_python practice. does any of it carry to other BFCL formats?

ran base vs edited on the full sets of simple_java, simple_javascript, multiple, parallel, parallel_multiple. eval only, no new edits

12/17
multiple (pick 1 of N functions): 0.290 → 0.395, +36.2% rel, +26/-5, p≈2e-4. that one's real

java 0.05 → 0.08, js 0 → 0.02, parallel 0.020 → 0.015, parallel_multiple 0.005 → 0.015. all n.s., all basically floor

nothing regressed significantly

13/17   [attach 03_fused_paren_failure_mode.png]
why multiple moved: the fused paren fix just… transferred. fused openings 81 → 0 on simple_python, 36 → 0 on multiple

multiple missing_required went 34 → 9 bc base wrote positional args and edited writes named ones. that's most of the gain

14/17   [attach 04_transfer_vs_no_transfer.png]
what didn't move: parallel. wrong_count is 171/200 for BOTH models, still emits one call when it needs several

which makes sense, the edits fix call syntax, not the decision to emit more calls. never targeted that

15/17
one small L: java demo-copying went UP, 28 → 35

the anti-copy edit learned "don't paste math.factorial", not "don't paste demos" in general. it's hidden in the accuracy column bc java is near zero anyway

16/17
caveats so this doesn't get misread: custom prompt protocol (not the official leaderboard setup), one small model, one greedy run, skipped live / multi-turn / web / memory

and near-floor cats make relative % look wild. that +200% on parallel_multiple is 1 → 3 items lol

17/17
so yeah… what WSP bought here is unblocking how the model writes stuff it already almost had. not teaching it tools. still kinda goated that 100 forwards + closed-form edits gets you this far

harness, edit ledger, full tables:
https://github.com/mallikaakash/weight-space-programming
