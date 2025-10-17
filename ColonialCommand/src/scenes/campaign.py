"""Campaign scene for overworld map."""
from __future__ import annotations

import math
from typing import Optional

import pygame

from core import gfx
from core.state import GameState, SEASONS, Army, Objective, StoryEvent, EventChoice
from core.saveio import save_autosave
from core.ui import Button
from data.factions import FACTIONS, MAJOR_FACTIONS
from data.regions import REGIONS
from data.units import UNITS
from data.tech import TECH_TREE
from data.buildings import BUILDINGS, ORDERED_BUILDINGS
from systems import economy, research, movement, ai, diplomacy
from systems.battle_auto import resolve_auto
from .base import SceneBase

PLAYER_FACTION = "Britain"
AMBIENT_FREQUENCIES = (220, 294, 392)


class CampaignScene(SceneBase):
    def __init__(self, context) -> None:
        super().__init__(context)
        self.buttons: list[Button] = []
        self.utility_buttons: list[Button] = []
        self.selected_region: Optional[str] = None
        self.selected_army: Optional[Army] = None
        self.last_move: Optional[tuple[int, str]] = None
        self.moving: bool = False
        self.research_index: int = 0
        self._last_event_count: int = 0
        self._entered: bool = False
        self._highlight_time: float = 0.0
        self._hotkey_hint = "Hotkeys: H Help | U Undo | G +1000 | F Reveal | L Ledger | P Patrol | S Spy"
        self.objective_status: list[tuple[Objective, int, int]] = []
        self._active_event: Optional[StoryEvent] = None
        self._event_buttons: list[tuple[Button, EventChoice]] = []
        self._research_banner: Optional[dict] = None
        self._advisor_tip: str = ""
        self._advisor_timer: float = 0.0
        self._trade_timer: float = 0.0
        self.recruit_cycle: dict[str, int] = {}
        self.build_cycle: dict[str, int] = {}
        self.spy_mode: bool = False
        self.utility_lookup: dict[str, Button] = {}
        self._diplomacy_entries: list[tuple[pygame.Rect, str]] = []
        self._selected_diplomacy_target: Optional[str] = None
        self._diplomacy_buttons: list[Button] = []
        self._diplomacy_panel = pygame.Rect(196, 48, 120, 122)

    @property
    def state(self) -> GameState:
        assert self.app.state is not None
        return self.app.state

    def on_enter(self, **kwargs) -> None:
        self._build_buttons()
        self._build_utility_buttons()
        self._sync_move_button_indicator()
        self.spy_mode = False
        if not self.selected_region and self.state:
            visible = self.state.fog_of_war.get(PLAYER_FACTION, [])
            if visible:
                self.selected_region = visible[0]
            else:
                self.selected_region = next(iter(self.state.regions))
        self._update_recruit_tooltip()
        self._update_build_tooltip()
        if not self._entered:
            self._last_event_count = 0
            self.message_log.clear()
            self._entered = True
        self._highlight_time = 0.0
        self._trade_timer = 0.0
        self._refresh_objectives()
        self._selected_diplomacy_target = None
        self._diplomacy_buttons.clear()

    def _build_buttons(self) -> None:
        self.buttons = [
            Button(
                pygame.Rect(8, 150, 60, 18),
                "Recruit",
                self._recruit,
                tooltip="Select a region to view recruitment options",
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
        self._update_utility_states()

    def _build_utility_buttons(self) -> None:
        self.utility_buttons = []
        self.utility_lookup = {}
        specs = [
            ("Ledger", self._open_ledger, "ledger", pygame.K_l, "Review provincial income and supply"),
            ("Patrol", self._toggle_patrol, "patrol", pygame.K_p, "Assign a naval patrol to protect trade"),
            ("Spy", self._begin_spy_action, "spy", pygame.K_s, "Send a spy to an adjacent enemy"),
        ]
        width = 60
        height = 14
        for idx, (label, callback, key, hotkey, tip) in enumerate(specs):
            rect = pygame.Rect(0, 0, width, height)
            button = Button(rect=rect, text=label, on_click=callback, tooltip=tip, hotkey=hotkey)
            self.utility_buttons.append(button)
            self.utility_lookup[key] = button
        self._update_utility_states()
        self._layout_utility_buttons()

    def _update_utility_states(self) -> None:
        patrol_button = self.utility_lookup.get("patrol")
        spy_button = self.utility_lookup.get("spy")
        if patrol_button:
            enabled = bool(self.selected_army and self.selected_army.has_naval())
            patrol_button.enabled = enabled
            patrol_button.selected = bool(self.selected_army and self.selected_army.is_patrolling())
            if enabled and self.selected_army:
                status = "Stand down patrol" if self.selected_army.is_patrolling() else "Begin naval patrol"
                patrol_button.tooltip = f"{status} to guard trade routes"
            else:
                patrol_button.tooltip = "Select a fleet with a sloop or frigate"
        if spy_button:
            enabled = bool(self.selected_army and "spy" in self.selected_army.units)
            spy_button.enabled = enabled
            spy_button.selected = self.spy_mode
            if enabled:
                spy_button.tooltip = "Select an adjacent enemy region to infiltrate"
            else:
                spy_button.tooltip = "Recruit a spy unit to perform espionage"
        ledger_button = self.utility_lookup.get("ledger")
        if ledger_button:
            ledger_button.enabled = True

    def _layout_utility_buttons(self) -> None:
        hud = pygame.Rect(4, 4, 312, 40)
        info_rect = pygame.Rect(4, 48, 180, 124)
        ledger_button = self.utility_lookup.get("ledger")
        if ledger_button:
            ledger_button.rect.topleft = (
                hud.right - ledger_button.rect.width - 6,
                hud.bottom - ledger_button.rect.height - 4,
            )
        patrol_button = self.utility_lookup.get("patrol")
        spy_button = self.utility_lookup.get("spy")
        base_y = info_rect.y + info_rect.height - 24
        if patrol_button:
            patrol_button.rect.topleft = (info_rect.x + 4, base_y)
        if spy_button:
            offset_x = info_rect.x + 8 + (patrol_button.rect.width if patrol_button else 0)
            spy_button.rect.topleft = (offset_x, base_y)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self._active_event:
            for button, _ in self._event_buttons:
                button.handle_event(event)
            return
        self._layout_utility_buttons()
        for button in self._diplomacy_buttons:
            button.handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if any(button.rect.collidepoint(event.pos) for button in self._diplomacy_buttons):
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._handle_diplomacy_click(pos):
                return
            target = self._region_at_point(pos)
            if self.spy_mode and self.selected_army:
                if not target:
                    self.state.add_event("Click an adjacent region for espionage")
                    return
                if target == self.selected_army.location:
                    self.state.add_event("Select an enemy region instead")
                    return
                self._attempt_spy(target)
                return
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
            elif event.key == pygame.K_l:
                self._open_ledger()
            elif event.key == pygame.K_p:
                self._toggle_patrol()
            elif event.key == pygame.K_s:
                self._begin_spy_action()
            elif event.key in (pygame.K_z, pygame.K_u) and self.last_move:
                army_index, prev = self.last_move
                if 0 <= army_index < len(self.state.armies):
                    self.state.armies[army_index].location = prev
                    self.state.armies[army_index].movement = 1
                    self.last_move = None
                    self.state.add_event("Undo movement")
        for button in self.buttons:
            button.handle_event(event)
        for button in self.utility_buttons:
            button.handle_event(event)

    def _region_at_point(self, pos: tuple[int, int]) -> Optional[str]:
        closest: Optional[str] = None
        best_dist = 999.0
        for key, region in REGIONS.items():
            rx, ry = region.location
            dist = math.hypot(rx - pos[0], ry - pos[1])
            if dist < 10 and dist < best_dist:
                best_dist = dist
                closest = key
        return closest

    def _pick_region(self, pos: tuple[int, int]) -> None:
        closest = self._region_at_point(pos)
        if closest:
            if closest in self.state.fog_of_war.get(PLAYER_FACTION, []):
                self.selected_region = closest
                self._select_army_at_region(closest)
                self._update_recruit_tooltip()
                self._update_build_tooltip()

    def _handle_diplomacy_click(self, pos: tuple[int, int]) -> bool:
        for rect, faction in self._diplomacy_entries:
            if rect.collidepoint(pos):
                if self._selected_diplomacy_target == faction:
                    self._selected_diplomacy_target = None
                    self._diplomacy_buttons.clear()
                else:
                    self._selected_diplomacy_target = faction
                    self._refresh_diplomacy_buttons()
                return True
        return False

    def _select_army_at_region(self, region_key: str) -> None:
        self.selected_army = None
        for army in self.state.armies:
            if army.faction == PLAYER_FACTION and army.location == region_key:
                self.selected_army = army
                break
        self._set_moving(False)
        self._set_spy_mode(False, announce=False)
        self._update_utility_states()

    def _update_recruit_tooltip(self) -> None:
        if not self.buttons:
            return
        button = self.buttons[0]
        if not self.selected_region:
            button.tooltip = "Select a region to recruit"
            return
        region = self.state.regions[self.selected_region]
        if region.owner != PLAYER_FACTION:
            button.tooltip = "Capture this region to unlock recruitment"
            return
        options = self.state.available_recruits(region)
        if not options:
            button.tooltip = "No units available"
            return
        lines = [
            "Recruit (cycles each click)",
        ]
        for unit_key in options[:4]:
            unit = UNITS[unit_key]
            cost = self.state.recruit_cost(unit_key)
            lines.append(f"{unit.name}: Cost {cost} | Upkeep {unit.upkeep}")
        if len(options) > 4:
            lines.append("...")
        if not self.state.region_has_supply(PLAYER_FACTION, region.key):
            lines.append("Supply cut! Queue cannot complete until reconnected.")
        button.tooltip = "\n".join(lines)

    def _update_build_tooltip(self) -> None:
        if not self.buttons:
            return
        build_button: Optional[Button] = None
        for btn in self.buttons:
            if btn.text.lower().startswith("build"):
                build_button = btn
                break
        if not build_button:
            return
        if not self.selected_region:
            build_button.tooltip = "Select a region to develop"
            return
        region = self.state.regions[self.selected_region]
        if region.owner != PLAYER_FACTION:
            build_button.tooltip = "Occupy the region to improve it"
            return
        if region.project:
            project = region.project
            building = BUILDINGS.get(project.building)
            if building:
                build_button.tooltip = (
                    f"{building.name} under construction\nTurns remaining: {project.turns_left}"
                )
            else:
                build_button.tooltip = "Construction underway"
            return
        options = self.state.available_buildings(region)
        if not options:
            build_button.tooltip = "Region fully developed"
            return
        index = self.build_cycle.get(region.key, 0) % len(options)
        lines = ["Build (cycles each click)"]
        for offset in range(min(3, len(options))):
            opt = options[(index + offset) % len(options)]
            level = region.buildings.get(opt.key, 0) + 1
            lines.append(
                f"{opt.name} Lv{level}: Cost {opt.cost} | {opt.effect}"
            )
        if not self.state.region_has_supply(PLAYER_FACTION, region.key):
            lines.append("Supply cut! Construction paused until reconnected.")
        build_button.tooltip = "\n".join(lines)

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
                self._update_recruit_tooltip()
                self._check_for_battle(self.selected_army)

    def _check_for_battle(self, army: Army) -> None:
        region = self.state.regions[army.location]
        if region.owner != army.faction:
            if region.owner in self.state.factions:
                diplomacy.declare_war(self.state, army.faction, region.owner)
            defender = Army(faction=region.owner, location=region.key, units=list(region.garrison))
            if defender.units:
                result = resolve_auto(self.state, army, defender, location=region.key)
                if result.get("winner") == 1:
                    self.state.capture_region(region.key, army.faction, announce_for=PLAYER_FACTION)
                    updated = self.state.regions[region.key]
                    updated.garrison = army.units[:1]
                else:
                    region.garrison = defender.units
                    if not army.units:
                        try:
                            self.state.armies.remove(army)
                        except ValueError:
                            pass
            else:
                self.state.capture_region(region.key, army.faction, announce_for=PLAYER_FACTION)
                region = self.state.regions[region.key]
                self.state.add_event(f"{army.faction} occupied {REGIONS[region.key].name}")

    def _recruit(self) -> None:
        if not self.selected_region:
            return
        region = self.state.regions[self.selected_region]
        if region.owner != PLAYER_FACTION:
            self.state.add_event("Can only recruit in owned regions")
            return
        fac = self.state.factions[PLAYER_FACTION]
        options = self.state.available_recruits(region)
        if not options:
            self.state.add_event("No units available")
            return
        index = self.recruit_cycle.get(region.key, 0)
        unit_key = options[index % len(options)]
        cost = self.state.recruit_cost(unit_key)
        if fac.treasury < cost:
            self.state.add_event("Not enough funds")
            return
        region.recruit_queue.append(unit_key)
        fac.treasury -= cost
        self.recruit_cycle[region.key] = (index + 1) % len(options)
        unit_name = UNITS[unit_key].name
        self.state.add_event(
            f"Queued {unit_name} in {REGIONS[region.key].name} (Cost {cost})"
        )
        self._update_recruit_tooltip()

    def _build(self) -> None:
        if not self.selected_region:
            return
        region = self.state.regions[self.selected_region]
        if region.owner != PLAYER_FACTION:
            self.state.add_event("Must control region to build")
            return
        if region.project:
            self.state.add_event("Construction already underway")
            return
        options = self.state.available_buildings(region)
        if not options:
            self.state.add_event("Region cannot support further upgrades")
            return
        index = self.build_cycle.get(region.key, 0) % len(options)
        building = options[index]
        fac = self.state.factions[PLAYER_FACTION]
        if fac.treasury < building.cost:
            self.state.add_event("Insufficient treasury")
            return
        if not self.state.region_has_supply(PLAYER_FACTION, region.key):
            self.state.add_event("Restore supply before beginning construction")
            return
        if self.state.start_construction(region, building):
            self.build_cycle[region.key] = (index + 1) % len(options)
            self._update_build_tooltip()
        else:
            self.state.add_event("Unable to start construction")

    def _open_ledger(self) -> None:
        self._set_spy_mode(False, announce=False)
        self.app.switch_scene("ledger", return_to="campaign")

    def _toggle_patrol(self) -> None:
        if not self.selected_army:
            self.state.add_event("Select a fleet to patrol")
            return
        if not self.selected_army.has_naval():
            self.state.add_event("Patrols require naval vessels")
            return
        if self.selected_army.is_patrolling():
            self.state.set_patrol(self.selected_army, False)
        else:
            self.state.set_patrol(self.selected_army, True)
            self.selected_army.movement = 0
        self._set_spy_mode(False, announce=False)
        self._update_utility_states()

    def _begin_spy_action(self) -> None:
        if self.spy_mode:
            self._set_spy_mode(False)
            return
        if not self.selected_army or "spy" not in self.selected_army.units:
            self.state.add_event("No spy attached to the selected force")
            return
        self._set_spy_mode(True)

    def _set_spy_mode(self, enabled: bool, *, announce: bool = True) -> None:
        if self.spy_mode == enabled:
            return
        self.spy_mode = enabled
        if announce:
            if enabled:
                self.state.add_event("Select an adjacent enemy region to infiltrate")
            else:
                self.state.add_event("Spy orders cancelled")
        self._update_utility_states()

    def _attempt_spy(self, target: str) -> None:
        if not self.selected_army:
            return
        self.state.perform_espionage(self.selected_army, target)
        self._set_spy_mode(False, announce=False)
        self._update_recruit_tooltip()
        self._update_build_tooltip()

    def _refresh_diplomacy_buttons(self) -> None:
        if not self._selected_diplomacy_target:
            self._diplomacy_buttons.clear()
            return
        target = self._selected_diplomacy_target
        if target not in self.state.factions:
            self._diplomacy_buttons.clear()
            return
        relation = diplomacy.get_relation(self.state, PLAYER_FACTION, target)
        trade_active = self.state.factions[PLAYER_FACTION].diplomacy.trade.get(target, False)
        self._diplomacy_buttons.clear()

        def make_button(label: str, callback, enabled: bool, tip: str) -> None:
            rect = pygame.Rect(0, 0, 56, 14)
            button = Button(rect=rect, text=label, on_click=callback, tooltip=tip)
            button.enabled = enabled
            self._diplomacy_buttons.append(button)

        make_button(
            "War",
            self._declare_war,
            relation != "war",
            f"Declare war on {target}",
        )
        make_button(
            "Peace",
            self._offer_peace,
            relation == "war",
            f"Sue for peace with {target}",
        )
        if trade_active:
            make_button(
                "Cancel",
                self._cancel_trade,
                True,
                f"End trade pact with {target}",
            )
        else:
            make_button(
                "Trade",
                self._request_trade,
                relation != "war",
                f"Request trade agreement with {target}",
            )
        make_button(
            "Ally",
            self._propose_alliance,
            relation != "war" and relation != "allied",
            f"Seek alliance with {target}",
        )

    def _position_diplomacy_buttons(self, rect: pygame.Rect) -> None:
        if not self._diplomacy_buttons:
            return
        cols = 2
        spacing_x = 4
        spacing_y = 4
        for idx, button in enumerate(self._diplomacy_buttons):
            col = idx % cols
            row = idx // cols
            width = button.rect.width
            height = button.rect.height
            x = rect.x + 4 + col * (width + spacing_x)
            y = rect.y + 4 + row * (height + spacing_y)
            button.rect = pygame.Rect(x, y, width, height)

    def _declare_war(self) -> None:
        target = self._selected_diplomacy_target
        if not target:
            return
        diplomacy.declare_war(self.state, PLAYER_FACTION, target)
        self._refresh_diplomacy_buttons()

    def _offer_peace(self) -> None:
        target = self._selected_diplomacy_target
        if not target:
            return
        diplomacy.offer_peace(self.state, PLAYER_FACTION, target)
        self._refresh_diplomacy_buttons()

    def _request_trade(self) -> None:
        target = self._selected_diplomacy_target
        if not target:
            return
        diplomacy.request_trade(self.state, PLAYER_FACTION, target)
        self._refresh_diplomacy_buttons()

    def _cancel_trade(self) -> None:
        target = self._selected_diplomacy_target
        if not target:
            return
        self.state.factions[PLAYER_FACTION].diplomacy.trade[target] = False
        if target in self.state.factions:
            self.state.factions[target].diplomacy.trade[PLAYER_FACTION] = False
        self.state.add_event(f"Trade pact with {target} cancelled")
        self._refresh_diplomacy_buttons()

    def _propose_alliance(self) -> None:
        target = self._selected_diplomacy_target
        if not target:
            return
        diplomacy.propose_alliance(self.state, PLAYER_FACTION, target)
        self._refresh_diplomacy_buttons()

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
        else:
            self._set_spy_mode(False, announce=False)
        self._sync_move_button_indicator()
        self._update_utility_states()

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
        self.state.apply_supply_attrition()
        self.state.process_construction()
        self.state.process_recruitment()
        self.state.advance_turn(player_faction=PLAYER_FACTION)
        movement.reset_movement(self.state)
        self.state.prepare_turn_events(PLAYER_FACTION)
        save_autosave(self.state)
        treasury_after = self.state.factions[PLAYER_FACTION].treasury
        delta = treasury_after - treasury_before
        self.state.add_event(
            f"Treasury summary: +{income_total} income -{upkeep_total} upkeep = {delta:+d}"
        )
        self.state.add_event("Turn ended")
        self._update_build_tooltip()
        self._refresh_objectives()

    def update(self, dt: float) -> None:
        self.context.audio.play_loop("campaign_ambient", AMBIENT_FREQUENCIES, duration=3.0, volume=0.12)
        if self.moving:
            self._highlight_time += dt
        else:
            self._highlight_time = 0.0
        self._trade_timer += dt
        if self._trade_timer > math.tau:
            self._trade_timer -= math.tau
        events = self.state.last_events
        if len(events) > self._last_event_count:
            for evt in events[self._last_event_count :]:
                self.message_log.add(evt)
            self._last_event_count = len(events)
        self._refresh_objectives()
        if not self._active_event and self.state.has_pending_events(PLAYER_FACTION):
            event = self.state.pop_next_event(PLAYER_FACTION)
            if event:
                self._present_event(event)
        if self._research_banner:
            self._research_banner["timer"] -= dt
            if self._research_banner["timer"] <= 0:
                self._research_banner = None
        else:
            notice = self.state.pop_research_notification()
            if notice:
                faction, tech = notice
                text = f"{faction} completed {tech}"
                self._research_banner = {"text": text, "timer": 3.0}
                self.context.audio.play("research_banner", frequency=660, duration=0.35)
        self._advisor_timer += dt
        if self._advisor_timer >= 3.0:
            self._advisor_timer = 0.0
            self._refresh_advisor_tip()

    def on_exit(self) -> None:
        self.context.audio.stop_loop("campaign_ambient")
        self._set_moving(False)
        self._set_spy_mode(False, announce=False)
        self._active_event = None
        self._event_buttons.clear()

    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        palette = self.app.palette_id
        self._draw_map(surface, palette)
        hud = pygame.Rect(4, 4, 312, 40)
        gfx.draw_panel(surface, hud, palette)
        header = f"{PLAYER_FACTION} | Treasury {self.state.factions[PLAYER_FACTION].treasury} | Turn {self.state.turn} {SEASONS[self.state.season_index]} {self.state.year}"
        gfx.draw_text(surface, header, (hud.x + 4, hud.y + 4), color_index=25, palette_name=palette)
        weather_line = self.state.weather_summary()
        if weather_line:
            gfx.draw_text(
                surface,
                f"Weather: {weather_line[:38]}",
                (hud.x + 4, hud.y + 14),
                color_index=20,
                palette_name=palette,
            )
        patrols = self.state.count_patrols(PLAYER_FACTION)
        gfx.draw_text(
            surface,
            f"Patrols: {patrols}",
            (hud.x + 4, hud.y + 24),
            color_index=17,
            palette_name=palette,
        )
        if self.selected_region:
            info_rect = pygame.Rect(4, 48, 180, 124)
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
                (info_rect.x + 4, info_rect.y + 32),
                palette_name=palette,
            )
            gfx.draw_text(
                surface,
                f"Stability: {region.stability:.2f}",
                (info_rect.x + 4, info_rect.y + 40),
                palette_name=palette,
            )
            gfx.draw_text(
                surface,
                f"Garrison: {len(region.garrison)}",
                (info_rect.x + 4, info_rect.y + 48),
                palette_name=palette,
            )
            icon_y = info_rect.y + 60
            if region.garrison:
                self._draw_unit_icons(surface, region.garrison[:6], (info_rect.x + 18, icon_y), palette)
            else:
                gfx.draw_text(
                    surface,
                    "No garrison",
                    (info_rect.x + 4, icon_y - 4),
                    palette_name=palette,
                )
            supply_ok = self.state.region_has_supply(region.owner, region.key)
            supply_text = "Supplied" if supply_ok else "Cut Off"
            supply_color = 24 if supply_ok else 28
            gfx.draw_text(
                surface,
                f"Supply: {supply_text}",
                (info_rect.x + 4, info_rect.y + 70),
                color_index=supply_color,
                palette_name=palette,
            )
            income_preview = self.state.region_income_value(region)
            gfx.draw_text(
                surface,
                f"Income: {income_preview}",
                (info_rect.x + 4, info_rect.y + 78),
                palette_name=palette,
            )
            queue_preview = ", ".join(UNITS[u].name[:8] for u in region.recruit_queue[:3]) or "None"
            gfx.draw_text(
                surface,
                f"Queue: {queue_preview}",
                (info_rect.x + 4, info_rect.y + 86),
                palette_name=palette,
            )
            if region.recruit_queue:
                self._draw_unit_icons(
                    surface,
                    region.recruit_queue[:6],
                    (info_rect.x + 18, info_rect.y + 98),
                    palette,
                )
            governor_desc = self.state.governor_trait_description(region.governor_trait)
            gov_text = f"Governor: {governor_desc[:18]} ({region.governor_turns}t)"
            gfx.draw_text(
                surface,
                gov_text,
                (info_rect.x + 4, info_rect.y + 106),
                palette_name=palette,
            )
            building_bits = []
            for key in ORDERED_BUILDINGS:
                level = region.buildings.get(key, 0)
                if level:
                    building_bits.append(f"{BUILDINGS[key].name[:6]} Lv{level}")
            building_text = ", ".join(building_bits) if building_bits else "None"
            gfx.draw_text(
                surface,
                f"Builds: {building_text}",
                (info_rect.x + 4, info_rect.y + 114),
                palette_name=palette,
            )
            if region.project:
                building = BUILDINGS.get(region.project.building)
                label = building.name if building else region.project.building
                gfx.draw_text(
                    surface,
                    f"Project: {label} ({region.project.turns_left}t)",
                    (info_rect.x + 4, info_rect.y + 122),
                    palette_name=palette,
                )
        self._draw_diplomacy_panel(surface, palette)
        for button in self._diplomacy_buttons:
            button.draw(surface, palette)
            button.draw_tooltip(surface)
        self._layout_utility_buttons()
        for button in self.buttons:
            button.draw(surface, palette)
            button.draw_tooltip(surface)
        for button in self.utility_buttons:
            button.draw(surface, palette)
            button.draw_tooltip(surface)
        log_rect = pygame.Rect(4, 176, 312, 20)
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
        if self._research_banner:
            self._draw_research_banner(surface, palette)
        if self._active_event:
            self._draw_event_overlay(surface, palette)

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
        self._draw_trade_routes(surface, palette)
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
            if (
                discovered
                and self.state.regions[key].owner == PLAYER_FACTION
                and self.state.regions[key].unsupplied_turns > 0
            ):
                colors = gfx.get_palette(palette)
                pygame.draw.line(surface, colors[28], (x - 4, y - 4), (x + 4, y + 4), 1)
                pygame.draw.line(surface, colors[28], (x - 4, y + 4), (x + 4, y - 4), 1)
            if key in highlight_targets:
                pulse = (math.sin(self._highlight_time * 6.0) + 1.0) * 0.5
                radius = 6 + int(2 * pulse)
                highlight_color = gfx.get_palette(palette)[24 if pulse > 0.5 else 26]
                pygame.draw.circle(surface, highlight_color, (x, y), radius, 1)
            if discovered:
                gfx.draw_text(surface, region.name[:10], (x - 12, y + 8), color_index=15, palette_name=palette)
        for army in self.state.armies:
            if army.faction == PLAYER_FACTION and army.is_patrolling():
                px, py = REGIONS[army.location].location
                pygame.draw.circle(surface, gfx.get_palette(palette)[27], (px, py), 9, 1)
        if self.moving and self.selected_army and highlight_targets:
            origin_pos = REGIONS[self.selected_army.location].location
            pulse = (math.sin(self._highlight_time * 6.0) + 1.0) * 0.5
            highlight_color = gfx.get_palette(palette)[24 if pulse > 0.5 else 26]
            for target in highlight_targets:
                target_pos = REGIONS[target].location
                pygame.draw.line(surface, highlight_color, origin_pos, target_pos, 1)

    def _draw_trade_routes(self, surface: pygame.Surface, palette: str) -> None:
        fac = self.state.factions[PLAYER_FACTION]
        origin_key = self.state.faction_capital(PLAYER_FACTION)
        if not origin_key or origin_key not in REGIONS:
            return
        origin = REGIONS[origin_key].location
        partners = [partner for partner, active in fac.diplomacy.trade.items() if active]
        colors = gfx.get_palette(palette)
        for idx, partner in enumerate(partners):
            dest_key = self.state.faction_capital(partner)
            if not dest_key or dest_key not in REGIONS:
                continue
            dest = REGIONS[dest_key].location
            pygame.draw.line(surface, colors[21], origin, dest, 1)
            t = (self._trade_timer * 0.3 + idx * 0.2) % 1.0
            px = int(origin[0] + (dest[0] - origin[0]) * t)
            py = int(origin[1] + (dest[1] - origin[1]) * t)
            pygame.draw.circle(surface, colors[25], (px, py), 1)

    def _draw_unit_icons(
        self, surface: pygame.Surface, units: list[str], origin: tuple[int, int], palette: str
    ) -> None:
        if not units:
            return
        icon_map = {
            "line": "infantry",
            "militia": "infantry",
            "cavalry": "cavalry",
            "artillery": "artillery",
            "sloop": "ship",
            "frigate": "ship",
            "spy": "default",
        }
        x_start, y_center = origin
        spacing = 12
        for idx, unit in enumerate(units[:6]):
            icon_type = icon_map.get(unit, "default")
            center = (x_start + idx * spacing, y_center)
            gfx.draw_icon(surface, center, icon_type, palette)

    def _draw_research_banner(self, surface: pygame.Surface, palette: str) -> None:
        rect = pygame.Rect(40, 4, 240, 16)
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, rect.topleft)
        gfx.draw_text(surface, self._research_banner["text"][:30], (rect.x + 6, rect.y + 4), color_index=27, palette_name=palette)

    def _draw_event_overlay(self, surface: pygame.Surface, palette: str) -> None:
        rect = pygame.Rect(40, 40, 240, 120)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        gfx.draw_panel(surface, rect, palette)
        gfx.draw_text(surface, self._active_event.title, (rect.x + 8, rect.y + 6), color_index=25, palette_name=palette)
        desc = self._active_event.description
        for i in range(3):
            segment = desc[i * 34 : (i + 1) * 34]
            if not segment:
                break
            gfx.draw_text(
                surface,
                segment,
                (rect.x + 8, rect.y + 18 + i * 10),
                color_index=20,
                palette_name=palette,
            )
        for button, _ in self._event_buttons:
            button.draw(surface, palette)
            button.draw_tooltip(surface)

    def _present_event(self, event: StoryEvent) -> None:
        self._active_event = event
        self._event_buttons = []
        base_rect = pygame.Rect(50, 88, 220, 18)
        for i, choice in enumerate(event.choices):
            rect = pygame.Rect(base_rect.x, base_rect.y + i * 22, base_rect.width, base_rect.height)
            button = Button(
                rect=rect,
                text=choice.label,
                on_click=lambda c=choice: self._select_event_choice(c),
                tooltip=choice.result,
            )
            self._event_buttons.append((button, choice))

    def _select_event_choice(self, choice: EventChoice) -> None:
        self.state.resolve_event_choice(PLAYER_FACTION, choice)
        self.message_log.add(f"Event resolved: {choice.result}")
        self._active_event = None
        self._event_buttons.clear()

    def _refresh_objectives(self) -> None:
        self.objective_status = self.state.evaluate_objectives(PLAYER_FACTION)

    def _refresh_advisor_tip(self) -> None:
        fac = self.state.factions[PLAYER_FACTION]
        new_tip = ""
        cut_off = [
            reg
            for reg in self.state.regions_owned_by(PLAYER_FACTION)
            if reg.unsupplied_turns > 0
        ]
        if cut_off:
            new_tip = f"Reconnect supply to {REGIONS[cut_off[0].key].name}."
        elif fac.treasury < 60:
            new_tip = "Treasury low. Secure income."
        elif not fac.research_queue:
            new_tip = "Queue research to stay ahead."
        else:
            troubled = [reg for reg in self.state.regions_owned_by(PLAYER_FACTION) if reg.stability < 0.7]
            if troubled:
                new_tip = f"Boost stability in {REGIONS[troubled[0].key].name}."
            elif all(not reg.recruit_queue for reg in self.state.regions_owned_by(PLAYER_FACTION)):
                new_tip = "Consider training new units."
        if new_tip != self._advisor_tip:
            self._advisor_tip = new_tip
            if new_tip:
                self.message_log.add(f"Advisor: {new_tip}")

    def _draw_diplomacy_panel(self, surface: pygame.Surface, palette: str) -> None:
        panel = self._diplomacy_panel
        gfx.draw_panel(surface, panel, palette)
        palette_colors = gfx.get_palette(palette)
        gfx.draw_text(surface, "Objectives", (panel.x + 4, panel.y + 4), color_index=24, palette_name=palette)
        obj_y = panel.y + 14
        for objective, current, target in self.objective_status[:2]:
            progress = min(current, target)
            marker = "✓" if objective.completed else "•"
            text = f"{marker} {objective.description[:16]} ({progress}/{target})"
            gfx.draw_text(surface, text, (panel.x + 4, obj_y), color_index=20, palette_name=palette)
            obj_y += 10
        tip_text = self._advisor_tip or "All quiet across the empire."
        gfx.draw_text(
            surface,
            f"Advisor: {tip_text[:20]}",
            (panel.x + 4, obj_y),
            color_index=18,
            palette_name=palette,
        )
        diplo_start = obj_y + 12
        gfx.draw_text(surface, "Diplomacy", (panel.x + 4, diplo_start), color_index=24, palette_name=palette)
        diplo_state = self.state.factions[PLAYER_FACTION].diplomacy
        self._diplomacy_entries = []
        y = diplo_start + 10
        action_top = panel.bottom - 40
        for faction in MAJOR_FACTIONS:
            if faction == PLAYER_FACTION:
                continue
            row_rect = pygame.Rect(panel.x + 2, y - 2, panel.width - 4, 10)
            relation = diplomacy.get_relation(self.state, PLAYER_FACTION, faction)
            trade_active = diplo_state.trade.get(faction, False)
            status = relation
            if trade_active and relation != "war":
                status = "allied" if relation == "allied" else "trade"
            if self._selected_diplomacy_target == faction:
                surface.fill(palette_colors[4], row_rect)
                pygame.draw.rect(surface, palette_colors[8], row_rect, 1)
            color_index = self._status_color_index(status)
            label = f"{faction[:9]}: {status.upper()}"
            if trade_active and relation != "war":
                label += " +TRD"
            gfx.draw_text(
                surface,
                label[:18],
                (panel.x + 4, y),
                color_index=color_index,
                palette_name=palette,
            )
            self._diplomacy_entries.append((row_rect, faction))
            y += 10
        action_rect = pygame.Rect(panel.x + 4, action_top, panel.width - 8, 36)
        pygame.draw.rect(surface, palette_colors[3], action_rect)
        pygame.draw.rect(surface, palette_colors[8], action_rect, 1)
        if self._selected_diplomacy_target:
            self._refresh_diplomacy_buttons()
            target = self._selected_diplomacy_target
            relation = diplomacy.get_relation(self.state, PLAYER_FACTION, target)
            gfx.draw_text(
                surface,
                f"Actions: {target[:10]}",
                (action_rect.x + 2, action_rect.y + 2),
                color_index=23,
                palette_name=palette,
            )
            gfx.draw_text(
                surface,
                f"Status: {relation.title()}",
                (action_rect.x + 2, action_rect.y + 10),
                color_index=18,
                palette_name=palette,
            )
            self._position_diplomacy_buttons(action_rect)
        else:
            self._diplomacy_buttons.clear()

    @staticmethod
    def _status_color_index(status: str) -> int:
        mapping = {
            "war": 28,
            "trade": 24,
            "allied": 27,
            "neutral": 18,
        }
        return mapping.get(status, 20)
