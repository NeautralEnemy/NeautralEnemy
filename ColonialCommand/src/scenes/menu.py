"""Main menu scene."""
from __future__ import annotations

import pygame

from core import gfx
from core.saveio import ensure_directories
from .base import SceneBase
from core.ui import Button, layout_vertical


class MenuScene(SceneBase):
    def __init__(self, context) -> None:
        super().__init__(context)
        self.buttons: list[Button] = []
        ensure_directories()

    def on_enter(self, **kwargs) -> None:
        rects = layout_vertical(pygame.Rect(110, 70, 100, 18), 18, 6, 5)
        actions = [
            ("New Game", self._new_game, "Start a new campaign"),
            ("Load", self._load_game, "Load the latest autosave"),
            ("Settings", self._open_settings, "Adjust visual and audio options"),
            ("Credits", self._show_credits, "Meet the crew"),
            ("Exit", self._exit, "Leave Colonial Command"),
        ]
        self.buttons = []
        for rect, (label, callback, tip) in zip(rects, actions):
            self.buttons.append(Button(rect=rect, text=label, on_click=callback, tooltip=tip))
        self.credits_visible = False

    def _new_game(self) -> None:
        self.app.start_new_game()

    def _load_game(self) -> None:
        if not self.app.load_game("autosave"):
            self.message_log.add("No autosave found")

    def _open_settings(self) -> None:
        self.app.switch_scene("settings")

    def _show_credits(self) -> None:
        self.credits_visible = not getattr(self, "credits_visible", False)

    def _exit(self) -> None:
        self.app.exit()

    def handle_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            button.handle_event(event)

    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        palette = self.app.palette_id
        title_rect = pygame.Rect(40, 20, 240, 40)
        gfx.draw_panel(surface, title_rect, palette)
        gfx.draw_text(surface, "Colonial Command", (60, 30), color_index=25)
        for button in self.buttons:
            button.draw(surface, palette)
            button.draw_tooltip(surface)
        if getattr(self, "credits_visible", False):
            rect = pygame.Rect(60, 140, 200, 48)
            gfx.draw_panel(surface, rect, palette)
            lines = ["Design: OpenAI", "Code: gpt-5-codex", "Thanks for playing!"]
            for i, line in enumerate(lines):
                gfx.draw_text(surface, line, (rect.x + 10, rect.y + 10 + i * 10), color_index=20)

    def on_escape(self) -> bool:
        self.app.exit()
        return True
