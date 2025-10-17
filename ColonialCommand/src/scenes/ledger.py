"""Province ledger scene for campaign management."""
from __future__ import annotations

from typing import List, Tuple

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
        self.back_button: Button | None = None

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

    def _build_rows(self) -> None:
        self.rows.clear()
        if not self.app.state:
            return
        state = self.app.state
        owned_regions = list(state.regions.values())
        owned_regions.sort(key=lambda reg: (reg.owner != "Britain", -state.region_income_value(reg)))
        for region in owned_regions:
            name = REGIONS[region.key].name[:12] if region.key in REGIONS else region.key[:12]
            owner = region.owner
            income = str(state.region_income_value(region))
            stability = f"{region.stability:.2f}"
            supply = "Yes" if state.region_has_supply(region.owner, region.key) else "No"
            trait = state.governor_trait_description(region.governor_trait)
            self.rows.append((name, owner, income, stability, supply, trait))

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.back_button:
            self.back_button.handle_event(event)

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
            for value, x in zip(row, x_offsets):
                gfx.draw_text(surface, value[:16], (panel.x + x, y), color_index=20, palette_name=palette)

        battle_panel = pygame.Rect(8, 140, 304, 60)
        gfx.draw_panel(surface, battle_panel, palette)
        gfx.draw_text(surface, "Battle Journal", (battle_panel.x + 8, battle_panel.y + 6), color_index=24, palette_name=palette)
        if self.app.state:
            for idx, entry in enumerate(reversed(self.state.battle_journal[-4:])):
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

        if self.back_button:
            self.back_button.draw(surface, palette)
            self.back_button.draw_tooltip(surface)

    def on_escape(self) -> bool:
        self._return()
        return True

    def _return(self) -> None:
        self.app.switch_scene(self.return_to)


# Late import to avoid circular dependency when module is imported standalone.
from data.regions import REGIONS  # noqa: E402  pylint: disable=wrong-import-position
