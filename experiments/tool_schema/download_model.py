#!/usr/bin/env python3
"""Download SmolLM2-360M-Instruct into the local gitignored models/ cache."""
from __future__ import annotations

import os
import sys

from paths import HF_HOME, MODEL_DIR, MODEL_ID, MODELS_DIR


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    HF_HOME.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(HF_HOME)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(HF_HOME / "hub")

    from huggingface_hub import snapshot_download

    print(f"Downloading {MODEL_ID} -> {MODEL_DIR}", flush=True)
    path = snapshot_download(
        repo_id=MODEL_ID,
        local_dir=str(MODEL_DIR),
        ignore_patterns=["onnx/**", "runs/**", "*.onnx", "training_args.bin"],
    )
    print(f"Ready: {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
