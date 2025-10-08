"""Entry point for Colonial Command."""
from __future__ import annotations

import os
import sys

import pygame

from core.app import App
from core.saveio import ensure_directories, load_config, save_config


def init_pygame() -> None:
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=512)
    pygame.init()
    pygame.display.set_caption("Colonial Command")



def main() -> None:
    ensure_directories()
    config = load_config()
    try:
        app = App(config)
        app.run()
    finally:
        save_config(app.config if 'app' in locals() else config)
        pygame.quit()


if __name__ == "__main__":
    try:
        init_pygame()
        main()
    except pygame.error as exc:  # pragma: no cover - top level guard
        print("Failed to initialize Colonial Command:", exc)
        sys.exit(1)
