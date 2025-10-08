"""Heuristic AI controller."""
from __future__ import annotations

from typing import List

from core.state import GameState, Army
from data.regions import REGIONS
from data.units import UNITS
from . import movement, battle_auto


class AIController:
    def __init__(self, state: GameState, faction: str) -> None:
        self.state = state
        self.faction = faction

    def take_turn(self) -> None:
        self.recruit_if_needed()
        self.perform_moves()

    def recruit_if_needed(self) -> None:
        fac = self.state.factions[self.faction]
        if fac.treasury < 50:
            return
        owned = self.state.regions_owned_by(self.faction)
        if not owned:
            return
        richest = max(owned, key=lambda r: r.economy)
        richest.garrison.append("militia")
        fac.treasury -= UNITS["militia"].upkeep * 2
        self.state.add_event(f"{self.faction} raised militia in {REGIONS[richest.key].name}")

    def perform_moves(self) -> None:
        for army in list(self.state.armies):
            if army.faction != self.faction or army.movement <= 0:
                continue
            enemies = self._find_adjacent_enemies(army.location)
            if enemies:
                defender_key = enemies[0]
                defender = self._get_region_garrison(defender_key)
                if defender:
                    result = battle_auto.resolve_auto(self.state, army, defender)
                    if result.get("winner") == 1:
                        region = self.state.regions[defender_key]
                        region.owner = self.faction
                        region.garrison = army.units[:1]
                    else:
                        self.state.regions[defender_key].garrison = defender.units
                        if not army.units:
                            try:
                                self.state.armies.remove(army)
                            except ValueError:
                                pass
                else:
                    region = self.state.regions[defender_key]
                    region.owner = self.faction
                    region.garrison = []
                    self.state.add_event(f"{self.faction} captured {REGIONS[defender_key].name}")
            else:
                neighbors = [n for n in REGIONS[army.location].neighbors]
                if neighbors:
                    movement.move_army(self.state, army, neighbors[0])

    def _find_adjacent_enemies(self, region_key: str) -> List[str]:
        enemies = []
        owner = self.state.regions[region_key].owner
        for neighbor in REGIONS[region_key].neighbors:
            if self.state.regions[neighbor].owner != self.faction:
                enemies.append(neighbor)
        return enemies

    def _get_region_garrison(self, region_key: str) -> Army | None:
        region = self.state.regions[region_key]
        if region.garrison:
            return Army(faction=region.owner, location=region_key, units=list(region.garrison))
        return None


def run_ai_turns(state: GameState, player_faction: str) -> None:
    for faction in state.factions:
        if faction == player_faction:
            continue
        controller = AIController(state, faction)
        controller.take_turn()
