"""UI widgets for Colonial Command."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

import pygame

from . import gfx


@dataclass
class MessageLog:
    max_lines: int
    fade_duration: float = 0.6
    entries: List["LogEntry"] = field(default_factory=list)

    def add(self, text: str) -> None:
        self.entries.append(LogEntry(text=text))
        if len(self.entries) > self.max_lines:
            self.entries = self.entries[-self.max_lines :]

    def clear(self) -> None:
        self.entries.clear()

    def update(self, dt: float) -> None:
        if not self.entries:
            return
        for entry in self.entries:
            entry.age = min(entry.age + dt, self.fade_duration)

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, palette: str = "sunset") -> None:
        gfx.draw_panel(surface, rect, palette)
        palette_colors = gfx.get_palette(palette)
        base_color = palette_colors[20]
        highlight_color = palette_colors[25]
        line_height = 8
        usable_height = max(0, rect.height - 8)
        visible = min(len(self.entries), self.max_lines, max(1, usable_height // line_height))
        recent_entries = self.entries[-visible:]
        for i, entry in enumerate(recent_entries):
            t = entry.age / self.fade_duration if self.fade_duration > 0 else 1.0
            t = max(0.0, min(1.0, t))
            color = tuple(
                int(highlight_color[channel] * (1.0 - t) + base_color[channel] * t)
                for channel in range(3)
            )
            gfx.draw_text(
                surface,
                entry.text[:52],
                (rect.x + 4, rect.y + 4 + i * line_height),
                color=color,
            )


@dataclass
class LogEntry:
    text: str
    age: float = 0.0


@dataclass
class Button:
    rect: pygame.Rect
    text: str
    on_click: Callable[[], None]
    tooltip: Optional[str] = None
    hotkey: Optional[int] = None
    enabled: bool = True
    hovered: bool = False
    selected: bool = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.enabled:
            return
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()
        elif event.type == pygame.KEYDOWN and self.hotkey and event.key == self.hotkey:
            self.on_click()

    def draw(self, surface: pygame.Surface, palette: str) -> None:
        color = palette
        gfx.draw_panel(surface, self.rect, color)
        offset = (1, 1) if self.hovered else (0, 0)
        gfx.draw_text(surface, self.text.upper(), (self.rect.x + 4 + offset[0], self.rect.y + 4 + offset[1]))
        if self.selected:
            highlight = gfx.get_palette(palette)[26]
            pygame.draw.rect(surface, highlight, self.rect, 1)
        if not self.enabled:
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            surface.blit(overlay, self.rect.topleft)

    def draw_tooltip(self, surface: pygame.Surface) -> None:
        if self.hovered and self.tooltip:
            gfx.draw_tooltip(surface, self.tooltip, (self.rect.centerx, self.rect.top))


@dataclass
class Toggle:
    rect: pygame.Rect
    label: str
    state: bool
    on_toggle: Callable[[bool], None]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.state = not self.state
            self.on_toggle(self.state)

    def draw(self, surface: pygame.Surface, palette: str) -> None:
        gfx.draw_panel(surface, self.rect, palette)
        gfx.draw_text(surface, f"{self.label}: {'ON' if self.state else 'OFF'}", (self.rect.x + 4, self.rect.y + 4))


@dataclass
class Slider:
    rect: pygame.Rect
    label: str
    value: int
    min_value: int
    max_value: int
    on_change: Callable[[int], None]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            ratio = (event.pos[0] - self.rect.x) / max(1, self.rect.width)
            self.value = int(self.min_value + ratio * (self.max_value - self.min_value))
            self.value = max(self.min_value, min(self.max_value, self.value))
            self.on_change(self.value)

    def draw(self, surface: pygame.Surface, palette: str) -> None:
        gfx.draw_panel(surface, self.rect, palette)
        inner = self.rect.inflate(-6, -10)
        pygame.draw.rect(surface, gfx.get_palette(palette)[10], inner)
        knob_x = inner.x + int((self.value - self.min_value) / max(1, self.max_value - self.min_value) * inner.width)
        pygame.draw.rect(surface, gfx.get_palette(palette)[15], pygame.Rect(knob_x - 2, inner.y, 4, inner.height))
        gfx.draw_text(surface, f"{self.label}: {self.value}", (self.rect.x + 4, self.rect.y - 8))


def layout_vertical(rect: pygame.Rect, item_height: int, padding: int, count: int) -> List[pygame.Rect]:
    rects = []
    y = rect.y
    for _ in range(count):
        rects.append(pygame.Rect(rect.x, y, rect.width, item_height))
        y += item_height + padding
    return rects
