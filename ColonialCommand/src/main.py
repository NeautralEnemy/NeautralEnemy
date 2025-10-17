"""Entry point for Colonial Command."""
from __future__ import annotations

import sys

try:
    import pygame
except ModuleNotFoundError as exc:  # pragma: no cover - friendly runtime guard
    print("Colonial Command requires pygame. Please install it with 'pip install pygame'.")
    raise SystemExit(1) from exc

from core.app import App
from core.saveio import ensure_directories, load_config, save_config


def init_pygame() -> None:
    try:
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=512)
    except pygame.error as exc:
        print(f"Warning: audio pre-init failed ({exc}). Continuing without pre-init.")
    _, init_failed = pygame.init()
    if init_failed:
        print(f"Warning: {init_failed} pygame subsystem(s) failed to initialize.")
    if not pygame.display.get_init():
        raise RuntimeError("Pygame display subsystem failed to initialise.")
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
    except (pygame.error, RuntimeError) as exc:  # pragma: no cover - top level guard
        print("Failed to initialize Colonial Command:", exc)
        sys.exit(1)
