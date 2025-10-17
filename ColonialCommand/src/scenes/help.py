"""Help overlay scene."""
from __future__ import annotations

import pygame

from core import gfx
from .base import SceneBase

HELP_TEXT = [
    "Colonial Command Quick Reference",
    "Mouse: select regions, press buttons",
    "Recruit: adds Line Infantry (60 gold)",
    "Build: +economy, +stability",
    "Research: cycles tech categories",
    "Move: click destination; Z to undo",
    "End: resolves economy, AI, research",
    "Hotkeys: H help, G +1000, F reveal, R research",
    "~: debug toggle (not implemented)",
]


class HelpScene(SceneBase):
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            self.app.switch_scene("campaign")

    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        rect = pygame.Rect(30, 30, 260, 140)
        gfx.draw_panel(surface, rect, self.app.palette_id)
        for i, line in enumerate(HELP_TEXT):
            gfx.draw_text(surface, line, (rect.x + 6, rect.y + 6 + i * 10), color_index=24)

    def on_escape(self) -> bool:
        self.app.switch_scene("campaign")
        return True
