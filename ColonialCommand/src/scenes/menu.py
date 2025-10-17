"""Main menu scene."""
from __future__ import annotations

from datetime import datetime

import pygame

from core import gfx
from core.saveio import ensure_directories
from core.state import SAVES_DIR
from .base import SceneBase
from core.ui import Button, layout_vertical


class MenuScene(SceneBase):
    def __init__(self, context) -> None:
        super().__init__(context)
        self.buttons: list[Button] = []
        self.load_panel_visible: bool = False
        self.load_panel_rect = pygame.Rect(50, 60, 220, 120)
        self.slot_buttons: list[tuple[Button, str]] = []
        self.slot_details: dict[str, str] = {}
        self.selected_slot: str = "autosave"
        self.autosave_label: str = "Empty"
        ensure_directories()

    def on_enter(self, **kwargs) -> None:
        self.selected_slot = self.app.config.get("last_save_slot", "autosave") or "autosave"
        self.load_panel_visible = False
        rects = layout_vertical(pygame.Rect(110, 70, 100, 18), 18, 6, 5)
        actions = [
            ("New Game", self._new_game, "Start a new campaign"),
            ("Load", self._toggle_load_panel, "Browse save slots"),
            ("Settings", self._open_settings, "Adjust visual and audio options"),
            ("Credits", self._show_credits, "Meet the crew"),
            ("Exit", self._exit, "Leave Colonial Command"),
        ]
        self.buttons = []
        for rect, (label, callback, tip) in zip(rects, actions):
            self.buttons.append(Button(rect=rect, text=label, on_click=callback, tooltip=tip))
        self.credits_visible = False
        self._refresh_load_panel()

    def _new_game(self) -> None:
        self.app.start_new_game()

    def _toggle_load_panel(self) -> None:
        self.load_panel_visible = not self.load_panel_visible
        if self.load_panel_visible:
            self._refresh_load_panel()

    def _load_slot(self, slot: str) -> None:
        self.selected_slot = slot
        detail = self.slot_details.get(slot, "Empty")
        if detail == "Empty":
            self.message_log.add("Save slot empty")
            self._refresh_load_panel()
            return
        if self.app.load_game(slot):
            self.app.config["last_save_slot"] = slot
            self.load_panel_visible = False
        else:
            self.message_log.add("Failed to load save")
        self._refresh_load_panel()

    def _slot_detail(self, slot: str) -> str:
        path = SAVES_DIR / f"{slot}.json"
        if not path.exists():
            return "Empty"
        try:
            timestamp = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            return "Unavailable"
        return timestamp.strftime("%Y-%m-%d %H:%M")

    def _refresh_load_panel(self) -> None:
        slots = [
            ("autosave", "Autosave"),
            ("slot1", "Slot 1"),
            ("slot2", "Slot 2"),
            ("slot3", "Slot 3"),
        ]
        self.slot_buttons = []
        self.slot_details = {}
        button_area = pygame.Rect(self.load_panel_rect.x + 12, self.load_panel_rect.y + 44, 120, 16)
        rects = layout_vertical(button_area, 16, 4, len(slots))
        for rect, (slot_key, label) in zip(rects, slots):
            detail = self._slot_detail(slot_key)
            button = Button(
                rect=rect,
                text=label,
                on_click=lambda s=slot_key: self._load_slot(s),
                tooltip=f"{label}: {detail}" if detail != "Empty" else "Slot empty",
            )
            button.selected = slot_key == self.selected_slot
            self.slot_buttons.append((button, slot_key))
            self.slot_details[slot_key] = detail
        self.autosave_label = self.slot_details.get("autosave", "Empty")

    def _open_settings(self) -> None:
        self.app.switch_scene("settings")

    def _show_credits(self) -> None:
        self.credits_visible = not getattr(self, "credits_visible", False)

    def _exit(self) -> None:
        self.app.exit()

    def handle_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            button.handle_event(event)
        if self.load_panel_visible:
            for button, _ in self.slot_buttons:
                button.handle_event(event)

    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        palette = self.app.palette_id
        title_rect = pygame.Rect(40, 20, 240, 40)
        gfx.draw_panel(surface, title_rect, palette)
        gfx.draw_text(surface, "Colonial Command", (60, 30), color_index=25, palette_name=palette)
        for button in self.buttons:
            button.draw(surface, palette)
            button.draw_tooltip(surface)
        if getattr(self, "credits_visible", False):
            rect = pygame.Rect(60, 140, 200, 48)
            gfx.draw_panel(surface, rect, palette)
            lines = ["Design: OpenAI", "Code: gpt-5-codex", "Thanks for playing!"]
            for i, line in enumerate(lines):
                gfx.draw_text(surface, line, (rect.x + 10, rect.y + 10 + i * 10), color_index=20, palette_name=palette)
        if self.load_panel_visible:
            self._draw_load_panel(surface, palette)

    def on_escape(self) -> bool:
        if self.load_panel_visible:
            self.load_panel_visible = False
            return True
        self.app.exit()
        return True

    def _draw_load_panel(self, surface: pygame.Surface, palette: str) -> None:
        panel = self.load_panel_rect
        gfx.draw_panel(surface, panel, palette)
        gfx.draw_text(surface, "Load Game", (panel.x + 8, panel.y + 8), color_index=25, palette_name=palette)
        gfx.draw_text(
            surface,
            f"Autosave: {self.autosave_label}",
            (panel.x + 8, panel.y + 20),
            color_index=20,
            palette_name=palette,
        )
        gfx.draw_text(
            surface,
            "Select a slot to load",
            (panel.x + 8, panel.y + 30),
            color_index=18,
            palette_name=palette,
        )
        for button, slot_key in self.slot_buttons:
            button.draw(surface, palette)
            button.draw_tooltip(surface)
            detail = self.slot_details.get(slot_key, "Empty")
            color_index = 20 if detail not in {"Empty", "Unavailable"} else 15
            gfx.draw_text(
                surface,
                detail,
                (button.rect.right + 6, button.rect.y + 4),
                color_index=color_index,
                palette_name=palette,
            )
