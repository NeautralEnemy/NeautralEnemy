"""Campaign scene for overworld map."""
from __future__ import annotations

import math
from typing import Optional

import pygame

from core import gfx
from core.state import GameState, SEASONS, Army
from core.saveio import save_autosave
from core.ui import Button
from data.factions import FACTIONS, MAJOR_FACTIONS
from data.regions import REGIONS
from data.units import UNITS
from data.tech import TECH_TREE
from systems import economy, research, movement, ai
from systems.battle_auto import resolve_auto
from .base import SceneBase

PLAYER_FACTION = "Britain"
AMBIENT_FREQUENCIES = (220, 294, 392)


class CampaignScene(SceneBase):
    def __init__(self, context) -> None:
        super().__init__(context)
        self.buttons: list[Button] = []
        self.selected_region: Optional[str] = None
        self.selected_army: Optional[Army] = None
        self.last_move: Optional[tuple[int, str]] = None
        self.moving: bool = False
        self.research_index: int = 0
        self._last_event_count: int = 0
        self._entered: bool = False
        self._highlight_time: float = 0.0
        self._hotkey_hint = "Hotkeys: H Help | U Undo | G +1000 | F Reveal"

    @property
    def state(self) -> GameState:
        assert self.app.state is not None
        return self.app.state

    def on_enter(self, **kwargs) -> None:
        self._build_buttons()
        self._sync_move_button_indicator()
        if not self.selected_region and self.state:
            visible = self.state.fog_of_war.get(PLAYER_FACTION, [])
            if visible:
                self.selected_region = visible[0]
            else:
                self.selected_region = next(iter(self.state.regions))
        if not self._entered:
            self._last_event_count = 0
            self.message_log.clear()
            self._entered = True
        self._highlight_time = 0.0

    def _build_buttons(self) -> None:
        self.buttons = [
            Button(
                pygame.Rect(8, 150, 60, 18),
                "Recruit",
                self._recruit,
                tooltip=(
                    "Recruit Line Infantry\n"
                    f"Cost: 60\nUpkeep: {UNITS['line'].upkeep}/turn"
                ),
            ),
            Button(
                pygame.Rect(72, 150, 60, 18),
                "Build",
                self._build,
                tooltip="Improve infrastructure\nCost: 80\nBuild Time: Instant",
            ),
            Button(
                pygame.Rect(136, 150, 60, 18),
                "Research",
                self._research,
                tooltip="Queue next technology\nCost: Treasury free\nBuild Time: Multi-turn",
            ),
            Button(
                pygame.Rect(200, 150, 60, 18),
                "Move",
                self._prepare_move,
                tooltip="Select a destination\nMovement Cost: 1 region hop",
            ),
            Button(
                pygame.Rect(264, 150, 48, 18),
                "End",
                self._end_turn,
                tooltip="End the turn and autosave",
            ),
        ]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            self._pick_region(pos)
            if self.selected_army and self.moving:
                self._attempt_move_to_point(pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h:
                self.app.switch_scene("help")
            elif event.key == pygame.K_g:
                self.state.factions[PLAYER_FACTION].treasury += 1000
                self.state.add_event("Cheat: +1000 gold")
            elif event.key == pygame.K_f:
                for reg in self.state.regions:
                    self.state.reveal_region(PLAYER_FACTION, reg)
                self.state.add_event("Cheat: reveal map")
            elif event.key == pygame.K_r:
                for category in TECH_TREE:
                    self.state.factions[PLAYER_FACTION].tech_progress[category] = len(TECH_TREE[category])
                self.state.add_event("Cheat: research complete")
            elif event.key in (pygame.K_z, pygame.K_u) and self.last_move:
                army_index, prev = self.last_move
                if 0 <= army_index < len(self.state.armies):
                    self.state.armies[army_index].location = prev
                    self.state.armies[army_index].movement = 1
                    self.last_move = None
                    self.state.add_event("Undo movement")
        for button in self.buttons:
            button.handle_event(event)

    def _pick_region(self, pos: tuple[int, int]) -> None:
        closest = None
        best_dist = 999
        for key, region in REGIONS.items():
            rx, ry = region.location
            dist = math.hypot(rx - pos[0], ry - pos[1])
            if dist < 10 and dist < best_dist:
                best_dist = dist
                closest = key
        if closest:
            if closest in self.state.fog_of_war.get(PLAYER_FACTION, []):
                self.selected_region = closest
                self._select_army_at_region(closest)

    def _select_army_at_region(self, region_key: str) -> None:
        self.selected_army = None
        for army in self.state.armies:
            if army.faction == PLAYER_FACTION and army.location == region_key:
                self.selected_army = army
                break
        self._set_moving(False)

    def _attempt_move_to_point(self, pos: tuple[int, int]) -> None:
        if not self.selected_army:
            return
        closest = None
        best_dist = 999
        for key, region in REGIONS.items():
            rx, ry = region.location
            dist = math.hypot(rx - pos[0], ry - pos[1])
            if dist < 10 and dist < best_dist:
                best_dist = dist
                closest = key
        if closest and closest != self.selected_army.location:
            old_location = self.selected_army.location
            if movement.move_army(self.state, self.selected_army, closest):
                self.last_move = (self.state.armies.index(self.selected_army), old_location)
                self._set_moving(False)
                self.selected_region = closest
                self._check_for_battle(self.selected_army)

    def _check_for_battle(self, army: Army) -> None:
        region = self.state.regions[army.location]
        if region.owner != army.faction:
            defender = Army(faction=region.owner, location=region.key, units=list(region.garrison))
            if defender.units:
                result = resolve_auto(self.state, army, defender)
                if result.get("winner") == 1:
                    region.owner = army.faction
                    region.garrison = army.units[:1]
                else:
                    region.garrison = defender.units
                    if not army.units:
                        try:
                            self.state.armies.remove(army)
                        except ValueError:
                            pass
            else:
                region.owner = army.faction
                self.state.add_event(f"{army.faction} occupied {REGIONS[region.key].name}")

    def _recruit(self) -> None:
        if not self.selected_region:
            return
        region = self.state.regions[self.selected_region]
        if region.owner != PLAYER_FACTION:
            self.state.add_event("Can only recruit in owned regions")
            return
        cost = 60
        fac = self.state.factions[PLAYER_FACTION]
        if fac.treasury < cost:
            self.state.add_event("Not enough funds")
            return
        region.garrison.append("line")
        fac.treasury -= cost
        self.state.add_event(f"Recruited Line Infantry in {REGIONS[region.key].name}")

    def _build(self) -> None:
        if not self.selected_region:
            return
        region = self.state.regions[self.selected_region]
        if region.owner != PLAYER_FACTION:
            self.state.add_event("Must control region to build")
            return
        fac = self.state.factions[PLAYER_FACTION]
        cost = 80
        if fac.treasury < cost:
            self.state.add_event("Insufficient treasury")
            return
        region.economy += 4
        region.stability = min(1.2, region.stability + 0.05)
        fac.treasury -= cost
        self.state.add_event(f"Upgraded infrastructure in {REGIONS[region.key].name}")

    def _research(self) -> None:
        categories = list(TECH_TREE.keys())
        fac = self.state.factions[PLAYER_FACTION]
        current = fac.research_queue
        if current:
            self.state.add_event("Research already in progress")
            return
        category = categories[self.research_index % len(categories)]
        self.research_index += 1
        if self.state.queue_research(PLAYER_FACTION, category):
            self.state.add_event(f"Researching {category}")

    def _prepare_move(self) -> None:
        if self.selected_army:
            self._set_moving(True)
            self.state.add_event("Select destination")
        else:
            self._set_moving(False)
            self.state.add_event("No army present")

    def _set_moving(self, enabled: bool) -> None:
        self.moving = bool(enabled and self.selected_army)
        if not self.moving:
            self._highlight_time = 0.0
        self._sync_move_button_indicator()

    def _sync_move_button_indicator(self) -> None:
        for button in self.buttons:
            if button.text.lower().startswith("move"):
                button.selected = self.moving
                break

    def _end_turn(self) -> None:
        self._set_moving(False)
        player_state = self.state.factions[PLAYER_FACTION]
        income_total = int(
            sum(reg.income() for reg in self.state.regions_owned_by(PLAYER_FACTION))
            * player_state.income_modifier()
        )
        upkeep_total = self.state.upkeep_cost(PLAYER_FACTION)
        treasury_before = player_state.treasury

        economy.resolve_turn_economy(self.state)
        research.handle_research(self.state)
        if self.app.skip_ai:
            self.state.add_event("AI moves skipped")
        else:
            ai.run_ai_turns(self.state, PLAYER_FACTION)
        self.state.advance_turn()
        movement.reset_movement(self.state)
        save_autosave(self.state)
        treasury_after = self.state.factions[PLAYER_FACTION].treasury
        delta = treasury_after - treasury_before
        self.state.add_event(
            f"Treasury summary: +{income_total} income -{upkeep_total} upkeep = {delta:+d}"
        )
        self.state.add_event("Turn ended")

    def update(self, dt: float) -> None:
        self.context.audio.play_loop("campaign_ambient", AMBIENT_FREQUENCIES, duration=3.0, volume=0.12)
        if self.moving:
            self._highlight_time += dt
        else:
            self._highlight_time = 0.0
        events = self.state.last_events
        if len(events) > self._last_event_count:
            for evt in events[self._last_event_count :]:
                self.message_log.add(evt)
            self._last_event_count = len(events)

    def on_exit(self) -> None:
        self.context.audio.stop_loop("campaign_ambient")
        self._set_moving(False)

    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        palette = self.app.palette_id
        self._draw_map(surface, palette)
        hud = pygame.Rect(4, 4, 312, 40)
        gfx.draw_panel(surface, hud, palette)
        header = f"{PLAYER_FACTION} | Treasury {self.state.factions[PLAYER_FACTION].treasury} | Turn {self.state.turn} {SEASONS[self.state.season_index]} {self.state.year}"
        gfx.draw_text(surface, header, (hud.x + 4, hud.y + 4), color_index=25, palette_name=palette)
        if self.selected_region:
            info_rect = pygame.Rect(4, 48, 180, 90)
            gfx.draw_panel(surface, info_rect, palette)
            region = self.state.regions[self.selected_region]
            gfx.draw_text(
                surface,
                REGIONS[region.key].name,
                (info_rect.x + 4, info_rect.y + 4),
                color_index=23,
                palette_name=palette,
            )
            faction = FACTIONS.get(region.owner)
            emblem_color = faction.color if faction else 20
            gfx.draw_faction_emblem(surface, (info_rect.x + 4, info_rect.y + 14), palette, emblem_color)
            gfx.draw_text(
                surface,
                f"Owner: {region.owner}",
                (info_rect.x + 14, info_rect.y + 14),
                palette_name=palette,
            )
            gfx.draw_text(
                surface,
                f"Pop: {region.population}",
                (info_rect.x + 4, info_rect.y + 24),
                palette_name=palette,
            )
            gfx.draw_text(
                surface,
                f"Economy: {region.economy}",
                (info_rect.x + 4, info_rect.y + 34),
                palette_name=palette,
            )
            gfx.draw_text(
                surface,
                f"Stability: {region.stability:.2f}",
                (info_rect.x + 4, info_rect.y + 44),
                palette_name=palette,
            )
            gfx.draw_text(
                surface,
                f"Garrison: {len(region.garrison)}",
                (info_rect.x + 4, info_rect.y + 54),
                palette_name=palette,
            )
        self._draw_diplomacy_panel(surface, palette)
        for button in self.buttons:
            button.draw(surface, palette)
            button.draw_tooltip(surface)
        log_rect = pygame.Rect(4, 172, 312, 24)
        self.message_log.draw(surface, log_rect, palette)
        hint_area = pygame.Rect(log_rect.x + 2, log_rect.bottom - 8, log_rect.width - 4, 8)
        surface.fill(gfx.get_palette(palette)[2], hint_area)
        gfx.draw_text(
            surface,
            self._hotkey_hint,
            (hint_area.x + 2, hint_area.y + 1),
            color_index=25,
            palette_name=palette,
        )

    def _draw_map(self, surface: pygame.Surface, palette: str) -> None:
        highlight_targets = set()
        if self.moving and self.selected_army:
            highlight_targets = {
                neighbor
                for neighbor in REGIONS[self.selected_army.location].neighbors
                if neighbor in self.state.fog_of_war.get(PLAYER_FACTION, [])
            }
        for key, region in REGIONS.items():
            x, y = region.location
            for neighbor in region.neighbors:
                nx, ny = REGIONS[neighbor].location
                pygame.draw.line(surface, gfx.get_palette(palette)[5], (x, y), (nx, ny), 1)
        for key, region in REGIONS.items():
            x, y = region.location
            discovered = key in self.state.fog_of_war.get(PLAYER_FACTION, [])
            color_index = 3 if not discovered else 12
            if discovered:
                owner = self.state.regions[key].owner
                if owner == PLAYER_FACTION:
                    color_index = 18
                elif owner in ("France", "Spain", "Netherlands"):
                    color_index = 22
            pygame.draw.circle(surface, gfx.get_palette(palette)[color_index], (x, y), 5)
            if self.selected_region == key and discovered:
                pygame.draw.circle(surface, gfx.get_palette(palette)[25], (x, y), 7, 1)
            if key in highlight_targets:
                pulse = (math.sin(self._highlight_time * 6.0) + 1.0) * 0.5
                radius = 6 + int(2 * pulse)
                highlight_color = gfx.get_palette(palette)[24 if pulse > 0.5 else 26]
                pygame.draw.circle(surface, highlight_color, (x, y), radius, 1)
            if discovered:
                gfx.draw_text(surface, region.name[:10], (x - 12, y + 8), color_index=15, palette_name=palette)
        if self.moving and self.selected_army and highlight_targets:
            origin_pos = REGIONS[self.selected_army.location].location
            pulse = (math.sin(self._highlight_time * 6.0) + 1.0) * 0.5
            highlight_color = gfx.get_palette(palette)[24 if pulse > 0.5 else 26]
            for target in highlight_targets:
                target_pos = REGIONS[target].location
                pygame.draw.line(surface, highlight_color, origin_pos, target_pos, 1)

    def _draw_diplomacy_panel(self, surface: pygame.Surface, palette: str) -> None:
        panel = pygame.Rect(196, 48, 120, 90)
        gfx.draw_panel(surface, panel, palette)
        gfx.draw_text(surface, "Diplomacy", (panel.x + 4, panel.y + 4), color_index=24, palette_name=palette)
        diplomacy = self.state.factions[PLAYER_FACTION].diplomacy
        y = panel.y + 16
        for faction in MAJOR_FACTIONS:
            if faction == PLAYER_FACTION:
                continue
            status = diplomacy.relations.get(faction, "peace").lower()
            if diplomacy.trade.get(faction):
                status = "trade"
            color_index = self._status_color_index(status)
            label = f"{faction[:9]}: {status.upper()}"
            gfx.draw_text(surface, label, (panel.x + 4, y), color_index=color_index, palette_name=palette)
            y += 10

    @staticmethod
    def _status_color_index(status: str) -> int:
        mapping = {
            "war": 28,
            "trade": 24,
            "peace": 18,
            "neutral": 15,
        }
        return mapping.get(status, 20)
