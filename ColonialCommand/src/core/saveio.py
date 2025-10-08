"""Saving and loading helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .state import GameState, SAVES_DIR

CONFIG_PATH = Path("config.json")


def ensure_directories() -> None:
    SAVES_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            return {}
    return {}


def save_config(config: Dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def save_autosave(state: GameState) -> None:
    state.save("autosave")
