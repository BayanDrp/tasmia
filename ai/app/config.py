"""Loader for the shared project config (repo-root config.json).

One JSON file feeds the Python service (ai/) and the Go backend
(web/backend/) so both stacks never drift apart. Values are exposed as
module level constants; nothing here imports torch/gradio.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Repo root = two levels above this file (ai/app/config.py).
# Override with TASMIA_CONFIG=/path/to/config.json if needed.
_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config.json"
CONFIG_PATH = Path(os.environ.get("TASMIA_CONFIG", _DEFAULT_PATH))

with CONFIG_PATH.open(encoding="utf-8") as _fh:
    _cfg = json.load(_fh)

# --- models ---
MODEL_ALIASES: dict[str, str] = _cfg["models"]["aliases"]
DEFAULT_MODEL_ALIAS: str = _cfg["models"]["default"]

# --- audio pipeline (same values as the HF Space) ---
SAMPLE_RATE: int = _cfg["audio"]["sample_rate"]
MAX_AUDIO_SECONDS: int = _cfg["audio"]["max_seconds"]
MAX_CHUNK_SECONDS: int = _cfg["audio"]["chunk_seconds"]
CHUNK_OVERLAP_SECONDS: int = _cfg["audio"]["chunk_overlap_seconds"]
SILENCE_RMS: float = _cfg["audio"]["silence_rms"]
TRIM_SILENCE: bool = _cfg["audio"]["trim_silence"]

# --- compute: asr.py resolves this with torch (cuda+fp16 / cpu+fp32) ---
DEVICE_PREFERENCE: str = _cfg["compute"]["device"]

# --- HTTP service (what the Go backend calls) ---
SERVER_HOST: str = _cfg["server_web"]["host"]
SERVER_PORT: int = _cfg["server_web"]["port"]

# --- Docker service (what the Go backend calls) ---
SERVER_DOCKER_HOST: str = _cfg["server_docker"]["host"]
SERVER_DOCKER_PORT: int = _cfg["server_docker"]["port"]

# --- optional cloud fallback (read by the Go backend) ---
SPACE_FALLBACK_ENABLED: bool = _cfg["space_fallback"]["enabled"]
SPACE_FALLBACK_URL: str = _cfg["space_fallback"]["url"]
SPACE_FALLBACK_TIMEOUT: int = _cfg["space_fallback"]["timeout_seconds"]


