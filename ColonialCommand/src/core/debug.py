"""Simple debug console overlay."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pygame

from . import gfx


@dataclass
class DebugConsole:
    visible: bool = False
    lines: List[str] = field(default_factory=list)

    def toggle(self) -> None:
        self.visible = not self.visible

    def add(self, text: str) -> None:
        self.lines.append(text)
        if len(self.lines) > 8:
            self.lines = self.lines[-8:]

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        rect = pygame.Rect(4, 4, 160, 80)
        gfx.draw_panel(surface, rect, "dusk")
        for i, line in enumerate(self.lines[-8:]):
            gfx.draw_text(surface, line[:24], (rect.x + 4, rect.y + 4 + i * 8), color_index=25)
