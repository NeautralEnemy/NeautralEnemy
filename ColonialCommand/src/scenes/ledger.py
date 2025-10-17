"""Province ledger scene for campaign management."""
from __future__ import annotations

from typing import List, Tuple, Optional

import pygame

from core import gfx
from core.state import GameState
from core.ui import Button
from .base import SceneBase


class LedgerScene(SceneBase):
    def __init__(self, context) -> None:
        super().__init__(context)
        self.return_to: str = "campaign"
        self.rows: List[Tuple[str, str, str, str, str, str]] = []
        self.row_flags: List[dict] = []
        self.back_button: Button | None = None
        self.sort_buttons: List[Button] = []
        self.filter_buttons: List[Button] = []
        self.sort_key: str = "income"
        self.filter_mode: str = "all"
        self.selected_row: Optional[int] = None
        self.battle_hover: Optional[dict] = None

    @property
    def state(self) -> GameState:
        assert self.app.state is not None
        return self.app.state

    def on_enter(self, **kwargs) -> None:
        self.return_to = kwargs.get("return_to", "campaign")
        self._build_rows()
        self.back_button = Button(
            pygame.Rect(248, 170, 64, 18),
            "Back",
            self._return,
            tooltip="Return to campaign",
        )
        self._build_controls()

    def _build_rows(self) -> None:
        self.rows.clear()
        self.row_flags.clear()
        if not self.app.state:
            return
        state = self.app.state
        owned_regions = list(state.regions.values())
        if self.filter_mode == "trouble":
            owned_regions = [
                reg
                for reg in owned_regions
                if state.region_has_supply(reg.owner, reg.key) is False
                or reg.stability < 0.7
            ]
        elif self.filter_mode == "supply":
            owned_regions = [
                reg
                for reg in owned_regions
                if state.region_has_supply(reg.owner, reg.key)
            ]
        if self.sort_key == "name":
            owned_regions.sort(key=lambda reg: REGIONS[reg.key].name)
        elif self.sort_key == "stability":
            owned_regions.sort(key=lambda reg: reg.stability)
        else:
            owned_regions.sort(key=lambda reg: state.region_income_value(reg), reverse=True)
        for region in owned_regions:
            name = REGIONS[region.key].name[:12] if region.key in REGIONS else region.key[:12]
            owner = region.owner
            income = str(state.region_income_value(region))
            stability = f"{region.stability:.2f}"
            supply = "Yes" if state.region_has_supply(region.owner, region.key) else "No"
            trait = state.governor_trait_description(region.governor_trait)
            self.rows.append((name, owner, income, stability, supply, trait))
            self.row_flags.append(
                {
                    "trouble": supply == "No" or region.stability < 0.7,
                    "unsupplied": supply == "No",
                }
            )

    def _build_controls(self) -> None:
        panel = pygame.Rect(8, 8, 304, 128)
        self.sort_buttons = []
        sort_specs = [("Name", "name"), ("Income", "income"), ("Stab", "stability")]
        for idx, (label, key) in enumerate(sort_specs):
            rect = pygame.Rect(panel.right - 50, panel.y + 6 + idx * 16, 44, 12)
            button = Button(rect, label, lambda k=key: self._set_sort(k), tooltip=f"Sort by {label.lower()}")
            button.selected = self.sort_key == key
            self.sort_buttons.append(button)
        self.filter_buttons = []
        filter_specs = [("All", "all"), ("Trouble", "trouble"), ("Supply", "supply")]
        for idx, (label, mode) in enumerate(filter_specs):
            rect = pygame.Rect(12 + idx * 64, 170, 60, 14)
            button = Button(rect, label, lambda m=mode: self._set_filter(m), tooltip=f"Show {label.lower()} regions")
            button.selected = self.filter_mode == mode
            self.filter_buttons.append(button)

    def _set_sort(self, key: str) -> None:
        if self.sort_key == key:
            return
        self.sort_key = key
        self._build_rows()
        for button in self.sort_buttons:
            button.selected = button.text.lower().startswith(key[:3].lower())

    def _set_filter(self, mode: str) -> None:
        if self.filter_mode == mode:
            return
        self.filter_mode = mode
        self._build_rows()
        for button in self.filter_buttons:
            button.selected = button.text.lower().startswith(mode[:3])

    def _handle_row_click(self, pos: Tuple[int, int]) -> None:
        panel = pygame.Rect(8, 8, 304, 128)
        if not panel.collidepoint(pos):
            self.selected_row = None
            return
        relative_y = pos[1] - (panel.y + 18)
        if relative_y < 0:
            self.selected_row = None
            return
        index = relative_y // 10
        if 0 <= index < len(self.rows):
            self.selected_row = index
        else:
            self.selected_row = None

    def _handle_battle_hover(self, pos: Tuple[int, int]) -> None:
        if not self.app.state:
            return
        battle_panel = pygame.Rect(8, 140, 304, 60)
        if not battle_panel.collidepoint(pos):
            self.battle_hover = None
            return
        recent = list(reversed(self.state.battle_journal[-4:]))
        relative_y = pos[1] - (battle_panel.y + 18)
        if relative_y < 0:
            self.battle_hover = None
            return
        index = relative_y // 10
        if 0 <= index < len(recent):
            self.battle_hover = recent[index]
        else:
            self.battle_hover = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.back_button:
            self.back_button.handle_event(event)
        for button in self.sort_buttons:
            button.handle_event(event)
        for button in self.filter_buttons:
            button.handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_row_click(event.pos)
            self._handle_battle_hover(event.pos)
        if event.type == pygame.MOUSEMOTION:
            self._handle_battle_hover(event.pos)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        palette = self.app.palette_id
        panel = pygame.Rect(8, 8, 304, 128)
        gfx.draw_panel(surface, panel, palette)
        headers = ["Region", "Owner", "Income", "Stab", "Supply", "Governor"]
        x_offsets = [10, 70, 130, 172, 210, 248]
        for header, x in zip(headers, x_offsets):
            gfx.draw_text(surface, header, (panel.x + x, panel.y + 6), color_index=25, palette_name=palette)
        for idx, row in enumerate(self.rows[:10]):
            y = panel.y + 18 + idx * 10
            flag = self.row_flags[idx] if idx < len(self.row_flags) else {}
            if flag.get("trouble"):
                highlight = pygame.Rect(panel.x + 6, y - 1, panel.width - 12, 9)
                surface.fill(gfx.get_palette(palette)[4], highlight)
            if self.selected_row == idx:
                pygame.draw.rect(surface, gfx.get_palette(palette)[8], pygame.Rect(panel.x + 6, y - 1, panel.width - 12, 9), 1)
            for value, x in zip(row, x_offsets):
                color = 20
                if flag.get("unsupplied") and x == x_offsets[4]:
                    color = 28
                gfx.draw_text(surface, value[:16], (panel.x + x, y), color_index=color, palette_name=palette)

        battle_panel = pygame.Rect(8, 140, 304, 60)
        gfx.draw_panel(surface, battle_panel, palette)
        gfx.draw_text(surface, "Battle Journal", (battle_panel.x + 8, battle_panel.y + 6), color_index=24, palette_name=palette)
        if self.app.state:
            recent = list(reversed(self.state.battle_journal[-4:]))
            for idx, entry in enumerate(recent):
                text = (
                    f"{entry['season']} {entry['year']} {entry['location']}: "
                    f"{entry['attacker']} vs {entry['defender']} -> {entry['winner']}"
                )
                gfx.draw_text(
                    surface,
                    text[:46],
                    (battle_panel.x + 8, battle_panel.y + 18 + idx * 10),
                    color_index=18,
                    palette_name=palette,
                )
            if self.battle_hover:
                hover_text = (
                    f"Losses A:{self.battle_hover['atk_losses']} D:{self.battle_hover['def_losses']}"
                )
                gfx.draw_text(
                    surface,
                    hover_text,
                    (battle_panel.x + 8, battle_panel.bottom - 12),
                    color_index=25,
                    palette_name=palette,
                )

        if self.back_button:
            self.back_button.draw(surface, palette)
            self.back_button.draw_tooltip(surface)
        for button in self.sort_buttons + self.filter_buttons:
            button.draw(surface, palette)
            button.draw_tooltip(surface)

    def on_escape(self) -> bool:
        self._return()
        return True

    def _return(self) -> None:
        self.app.switch_scene(self.return_to)


# Late import to avoid circular dependency when module is imported standalone.
from data.regions import REGIONS  # noqa: E402  pylint: disable=wrong-import-position
