"""Heuristic AI controller."""
from __future__ import annotations

from typing import List, Optional

from core.state import GameState, Army, RegionState
from data.regions import REGIONS
from data.units import UNITS
from data.buildings import BuildingDef
from . import movement, battle_auto


class AIController:
    def __init__(self, state: GameState, faction: str) -> None:
        self.state = state
        self.faction = faction

    def take_turn(self) -> None:
        self.recruit_if_needed()
        self.build_infrastructure()
        self.perform_moves()

    def build_infrastructure(self) -> None:
        fac = self.state.factions[self.faction]
        if fac.treasury < 60:
            return
        choice: Optional[tuple] = None
        best_score = -999
        for region in self.state.regions_owned_by(self.faction):
            if region.project:
                continue
            if not self.state.region_has_supply(self.faction, region.key):
                continue
            options = self.state.available_buildings(region)
            if not options:
                continue
            building = self._pick_building(region, options)
            if fac.treasury < building.cost:
                continue
            frontier = len(self._find_adjacent_enemies(region.key))
            score = region.economy + frontier * 10
            if building.key == "fort":
                score += 12 + frontier * 4
            elif building.key == "culture":
                score += int((1.0 - min(region.stability, 1.2)) * 40)
            else:
                score += 8 - region.buildings.get("market", 0) * 4
            if score > best_score:
                best_score = score
                choice = (region, building)
        if choice:
            region, building = choice
            self.state.start_construction(region, building)

    def recruit_if_needed(self) -> None:
        fac = self.state.factions[self.faction]
        if fac.treasury < 50:
            return
        owned = self.state.regions_owned_by(self.faction)
        if not owned:
            return
        richest = max(owned, key=lambda r: r.economy)
        options = self.state.available_recruits(richest)
        if not options:
            return
        unit_key = options[0]
        cost = self.state.recruit_cost(unit_key)
        if fac.treasury < cost:
            return
        richest.recruit_queue.append(unit_key)
        fac.treasury -= cost
        self.state.add_event(
            f"{self.faction} queued {UNITS[unit_key].name} in {REGIONS[richest.key].name}"
        )

    def perform_moves(self) -> None:
        for army in list(self.state.armies):
            if army.faction != self.faction or army.movement <= 0:
                continue
            enemies = self._find_adjacent_enemies(army.location)
            if enemies:
                defender_key = enemies[0]
                defender = self._get_region_garrison(defender_key)
                if defender:
                    result = battle_auto.resolve_auto(
                        self.state, army, defender, location=defender.location
                    )
                    if result.get("winner") == 1:
                        self.state.capture_region(defender_key, self.faction)
                        region = self.state.regions[defender_key]
                        region.garrison = army.units[:1]
                    else:
                        self.state.regions[defender_key].garrison = defender.units
                        if not army.units:
                            try:
                                self.state.armies.remove(army)
                            except ValueError:
                                pass
                else:
                    self.state.capture_region(defender_key, self.faction)
                    region = self.state.regions[defender_key]
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
        enemies.sort(
            key=lambda key: (
                self.state.region_has_supply(self.state.regions[key].owner, key),
                self.state.regions[key].stability,
            )
        )
        return enemies

    def _pick_building(self, region: RegionState, options: List[BuildingDef]) -> BuildingDef:
        building = options[0]
        if region.stability < 0.75:
            for opt in options:
                if opt.key == "culture":
                    building = opt
                    break
        frontier = self._find_adjacent_enemies(region.key)
        if frontier:
            for opt in options:
                if opt.key == "fort":
                    building = opt
                    break
        if building.key != "market":
            for opt in options:
                if opt.key == "market" and region.buildings.get("market", 0) == 0:
                    building = opt
                    break
        return building

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
