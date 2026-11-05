#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
MODELS_DIR = REPO_ROOT / "models"
MODEL_DIR = MODELS_DIR / "SmolLM2-360M-Instruct"
HF_HOME = MODELS_DIR / "hf_home"
EVAL_PATH = EXPERIMENT_ROOT / "eval" / "dataset.jsonl"
TOOLS_PATH = EXPERIMENT_ROOT / "tools.json"
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "baselines"
