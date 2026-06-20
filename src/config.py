"""Shared config + env loading for the fit toolset."""

from __future__ import annotations

import os
from pathlib import Path

ENV_PATH = Path.home() / ".config" / "fit" / "strava.env"
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
FIT_ARCHIVE_DIR = DATA_DIR / "fit_files"
DB_PATH = DATA_DIR / "fit.db"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def save_env(env: dict[str, str]) -> None:
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text("".join(f"{k}={v}\n" for k, v in env.items()))
    os.chmod(ENV_PATH, 0o600)
