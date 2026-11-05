You are ghostwriting an **X/Twitter thread** as **Aakash Mallik** (@malliktwts).

## Non-negotiable: write in HIS lingo, not “AI tech Twitter”

A previous draft was rejected as “not how I write.” Do **not** reproduce that voice.

### Rejected voice (DO NOT write like this)
- Over-clean numbered threads: “Aim (honest):”, “Caveats I’m not soft-pedaling:”
- Corporate-crisp bullets with en-dashes everywhere
- “Expression surgery. Not knowledge infusion.” slogan stacking
- Founder-Twitter polish / LinkedIn-energy recap posts
- Generic “Thread:” openers with three parallel “No X. No Y. No Z.” lines

### His actual voice (MATCH THIS)
From https://aakashmallik.vercel.app/ and @malliktwts:

- Bio energy: “AI something something yada | Generalist FAFO”
- Site: “Lil bit about me”, “FAFO-ing AI research stuff in my free time”, “not the MERN kind”, “A bit better every day.”
- Tweets: “So from today we start clearing the drafts and prepping for research…or rather TRUE engineering”
- “I dunno how to explain this…”
- “actually pretty darn goated”
- Occasional Hinglish is fine when it fits; don’t force it
- Casual, slightly messy, first-person, thinks out loud
- Can be technical without sounding like a press release
- Short punchy posts mixed with denser ones — not every tweet a bullet list

From how he talks in this project’s chat (signal):
- “The dump”
- “Wdym”
- “Ok now i want…”
- Blunt: gains = formatting bottlenecks / call-writing policy, **not** new knowledge
- “semantic leftover”
- Wants honesty over hype; hates AI-sounding prose

### Style rules
1. Sound like Aakash texting a sharp research update to mutuals — not a product launch.
2. Prefer spoken rhythm over outline structure. One idea per tweet is fine; don’t start every tweet with a label.
3. Keep numbers exact and sourced (below). Don’t invent stats.
4. It’s OK to say “lol”, “basically”, “tbh”, “idk if that lands”, ellipses… if it fits him.
5. Still include methodology, aim, dataset, results, cross-format, caveats — just not in brochure form.
6. Each post ≤ 280 chars counting X’s URL shortening (URLs ≈ 23 chars). Number as `n/N`.
7. Mark where to attach charts with `(attach: 01_…png)` etc.

## Facts you MUST keep accurate (do not round creatively)

### Setup
- Model: SmolLM2-360M-Instruct
- Method: Weight-Space Programming (Takehi et al. “Sparks of Weight-Space Programming”) — closed-form weight edits, no fine-tuning / gradients
- Editor: Claude Opus 5.5, high thinking, 100 metered practice forwards
- Recipe: `current4` — 32 late tensors (o_proj/down_proj, layers 16–31): fused-paren projection, math.factorial demo attenuation, boolean shear toward True
- Delta ~216MB; not full retrain
- Leakage: holdout sealed (`WSP_LOCK_TEST`), quarantined until budget done

### Dataset
- BFCL v4 via `bfcl-eval==2025.10.27.1`
- Edit category: `simple_python` only, 400 items → 300 practice + 100 sealed holdout (file order)
- Official AST scorer

### simple_python results
- Practice: 123/300 = 0.410 → 185/300 = 0.617 (+50.4% rel, +69/−7)
- Holdout: 33/100 = 0.33 → 50/100 = 0.50 (+51.5% rel, +19/−2)
- Holdout fused parens: 24 → 0

### Interpretation (his take — keep this framing)
Gains primarily from fixing formatting bottlenecks / better policy for writing a call — **not** new knowledge infusion, not emergent ability, not cleaning semantic leftover.

### Cross-format (current4 tuned only on simple_python practice)
| category | base | edited | abs | rel |
|---|---|---|---|---|
| simple_python holdout | 0.330 | 0.500 | +0.170 | +51.5% |
| simple_java | 0.050 | 0.080 | +0.030 | +60.0% (n.s.) |
| simple_javascript | 0.000 | 0.020 | +0.020 | n/a |
| multiple | 0.290 | 0.395 | +0.105 | +36.2% (+26/−5, p≈2e-4) |
| parallel | 0.020 | 0.015 | −0.005 | −25% (n.s.) |
| parallel_multiple | 0.005 | 0.015 | +0.010 | +200% (n.s., tiny n) |

Mechanism: fused openings wipe (python 81→0, multiple 36→0); multiple `missing_required` 34→9. Parallel “emit several calls” untouched (`wrong_count` 171/200 both). Java demo-copy side-effect 28→35.

### Caveats
Custom prompt protocol (not official leaderboard), one small model, greedy once, near-floor cats inflate relative %, skipped live/multi-turn/web/memory.

### Links / assets
- Repo: https://github.com/mallikaakash/weight-space-programming
- Writeup: `experiments/tool_schema/results/bfcl/CROSSFMT_BASE_VS_EDITED.md` + root README
- Charts (pixel-accurate, already generated): `/opt/cursor/artifacts/wsp_tweet_charts/`
  - `01_simple_python_practice_holdout.png`
  - `02_crossfmt_base_vs_edited.png`
  - `03_fused_paren_failure_mode.png`
  - `04_transfer_vs_no_transfer.png`
- Bad draft to avoid copying: `/opt/cursor/artifacts/wsp_tweet_charts/THREAD.md`

## Working style
- High thinking. Read the style samples + README plain section + CROSSFMT writeup before drafting.
- Optionally skim a few more of his recent X posts via web if helpful.
- Draft → self-critique against “does this sound like malliktwts or like LinkedIn AI?” → revise once.
- Write final thread to `experiments/tool_schema/wsp/results/TWEET_THREAD_AAKASH.md`
- Also copy/symlink charts note in that file.
- Do **not** git commit unless the thread file is clearly ready; if you commit, use branch `cursor/bfcl-crossfmt-results-317b` or stay uncommitted — prefer writing the file; the supervisor will handle git.
- No weight editing. No eval runs needed unless you want to re-check a number from summary JSON.
