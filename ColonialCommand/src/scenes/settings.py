"""Settings scene."""
from __future__ import annotations

import pygame

from core import gfx
from core.ui import Button, Toggle, Slider
from .base import SceneBase

PALETTES = ["sunset", "jade", "dusk"]


class SettingsScene(SceneBase):
    def __init__(self, context) -> None:
        super().__init__(context)
        self.buttons: list[Button] = []
        self.toggles: list[Toggle] = []
        self.sliders: list[Slider] = []
        self.palette_index = 0

    def on_enter(self, **kwargs) -> None:
        palette = self.app.palette_id
        if palette in PALETTES:
            self.palette_index = PALETTES.index(palette)
        else:
            self.palette_index = 0
        self.buttons = [
            Button(pygame.Rect(40, 150, 120, 18), "Back", self._back, tooltip="Return to previous menu"),
            Button(pygame.Rect(180, 150, 120, 18), "Cycle Palette", self._cycle_palette, tooltip="Switch color set"),
        ]
        self.toggles = [
            Toggle(pygame.Rect(40, 60, 120, 18), "Audio", not self.context.audio.muted, self._toggle_audio),
            Toggle(pygame.Rect(40, 90, 120, 18), "Scanlines", self.app.scanlines, self._toggle_scanlines),
        ]
        self.sliders = [
            Slider(pygame.Rect(200, 80, 100, 18), "Scale", self.app.window_scale, 2, 4, self._change_scale)
        ]

    def handle_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            button.handle_event(event)
        for toggle in self.toggles:
            toggle.handle_event(event)
        for slider in self.sliders:
            slider.handle_event(event)

    def _toggle_audio(self, state: bool) -> None:
        self.app.set_audio(state)

    def _toggle_scanlines(self, state: bool) -> None:
        self.app.set_scanlines(state)

    def _change_scale(self, value: int) -> None:
        self.app.set_window_scale(value)

    def _cycle_palette(self) -> None:
        self.palette_index = (self.palette_index + 1) % len(PALETTES)
        self.app.set_palette(PALETTES[self.palette_index])

    def _back(self) -> None:
        self.app.switch_scene("menu")

    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        palette = self.app.palette_id
        gfx.draw_panel(surface, pygame.Rect(20, 20, 280, 40), palette)
        gfx.draw_text(surface, "Settings", (40, 30), color_index=25)
        for toggle in self.toggles:
            toggle.draw(surface, palette)
        for slider in self.sliders:
            slider.draw(surface, palette)
        for button in self.buttons:
            button.draw(surface, palette)
            button.draw_tooltip(surface)

    def on_escape(self) -> bool:
        self._back()
        return True
