#!/usr/bin/env bash
# BFCL cross-format probe: base vs current4-edited SmolLM2-360M-Instruct on the
# non-live AST categories. Eval only. Runs base then edited sequentially (RAM/CPU).
set -euo pipefail
cd "$(dirname "$0")/../.."
EDITED="${EDITED:-artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt}"
STYLE="${STYLE:-card}"
SUFFIX=""; [ "$STYLE" != card ] && SUFFIX="-$STYLE"
CATS=(simple_python simple_java simple_javascript multiple parallel parallel_multiple)
OUT=experiments/tool_schema/results/bfcl
LOGDIR=$OUT/crossfmt_logs; mkdir -p "$LOGDIR"
python3 experiments/tool_schema/bfcl_category_eval.py --prompt-style "$STYLE" \
  --category "${CATS[@]}" --tag "crossfmt-base$SUFFIX" 2>&1 | tee "$LOGDIR/crossfmt-base$SUFFIX.log"
python3 experiments/tool_schema/bfcl_category_eval.py --prompt-style "$STYLE" \
  --category "${CATS[@]}" --edited-state "$EDITED" --tag "crossfmt-edited$SUFFIX" 2>&1 | tee "$LOGDIR/crossfmt-edited$SUFFIX.log"
