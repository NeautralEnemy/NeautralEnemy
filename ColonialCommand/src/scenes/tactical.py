"""Tactical battle scene placeholder."""
from __future__ import annotations

import pygame

from core import gfx
from .base import SceneBase


class TacticalScene(SceneBase):
    def on_enter(self, **kwargs) -> None:
        battle_state = kwargs.get("battle_state", {})
        self.summary = battle_state.get("summary", "Battle complete")
        self.return_to = battle_state.get("return_to", "campaign")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            self.app.switch_scene(self.return_to)

    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        rect = pygame.Rect(40, 60, 240, 80)
        gfx.draw_panel(surface, rect, self.app.palette_id)
        gfx.draw_text(surface, "Tactical Battle", (rect.x + 10, rect.y + 10), color_index=25)
        gfx.draw_text(surface, self.summary, (rect.x + 10, rect.y + 30))
        gfx.draw_text(surface, "Click to return", (rect.x + 10, rect.y + 50), color_index=20)

    def on_escape(self) -> bool:
        self.app.switch_scene(self.return_to)
        return True
