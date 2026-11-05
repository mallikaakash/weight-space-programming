#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

WSP_ROOT = Path(__file__).resolve().parent
EXPERIMENT_ROOT = WSP_ROOT.parent
REPO_ROOT = EXPERIMENT_ROOT.parents[1]

MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
MODELS_DIR = REPO_ROOT / "models"
MODEL_DIR = MODELS_DIR / "SmolLM2-360M-Instruct"
HF_HOME = MODELS_DIR / "hf_home"

# Sealed practice (editor-visible) and sealed holdout (post-run only).
PRACTICE_DIR = WSP_ROOT / "practice"
PRACTICE_TRAIN_PATH = PRACTICE_DIR / "train.jsonl"
SEALED_DIR = EXPERIMENT_ROOT / "eval" / "sealed"
SEALED_TEST_PATH = SEALED_DIR / "test.jsonl"
SEALED_FULL_PATH = SEALED_DIR / "dataset_full.jsonl"

# Legacy full dataset path (may be quarantined / train-stubbed during a long run).
EVAL_PATH = EXPERIMENT_ROOT / "eval" / "dataset.jsonl"
TOOLS_PATH = EXPERIMENT_ROOT / "tools.json"
BASELINES_DIR = REPO_ROOT / "artifacts" / "baselines"
SESSIONS_DIR = REPO_ROOT / "artifacts" / "wsp_sessions"

# Blog / exp8-style guardrails: refuse edits to embeddings / lm_head / final norm.
PROTECTED_PARAM_SUBSTRINGS = (
    "embed_tokens",
    "wte",
    "lm_head",
    "model.norm",
)
