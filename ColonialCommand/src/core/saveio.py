"""Saving and loading helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .state import GameState, SAVES_DIR

CONFIG_PATH = Path("config.json")


def ensure_directories() -> None:
    """Ensure runtime directories exist, raising a clear error when they cannot."""

    try:
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"Unable to create save directory '{SAVES_DIR}': {exc}"
        ) from exc


def load_config() -> Dict[str, Any]:
    """Load persisted settings, falling back to defaults when invalid."""

    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception as exc:
            # Corrupt configuration files should not crash startup – report and continue.
            print(f"Warning: failed to read config.json ({exc}); using defaults.")
            return {}
    return {}


def save_config(config: Dict[str, Any]) -> None:
    """Persist configuration without interrupting shutdown on failure."""

    try:
        CONFIG_PATH.write_text(json.dumps(config, indent=2))
    except OSError as exc:
        print(f"Warning: unable to save config.json ({exc}).")


def save_autosave(state: GameState) -> None:
    state.save("autosave")
