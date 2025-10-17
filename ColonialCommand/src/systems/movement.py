"""Movement system."""
from __future__ import annotations

from typing import Optional

from core.state import GameState, Army
from data.regions import REGIONS, is_sea_lane


def move_army(state: GameState, army: Army, destination: str) -> bool:
    if destination not in REGIONS:
        return False
    if army.movement <= 0:
        state.add_event("Army is exhausted")
        return False
    region = state.get_region(army.location)
    if destination not in REGIONS[region.key].neighbors:
        return False
    if army.is_patrolling():
        state.set_patrol(army, False)
    cost = 1
    if is_sea_lane(region.key, destination):
        if not state.army_has_naval_support(army, destination):
            state.add_event("Naval support required for sea travel")
            return False
        naval_modifier = state.factions[army.faction].naval_modifier()
        cost = max(1, int(round(2 / max(0.5, naval_modifier))))
    if army.movement < cost:
        state.add_event("Not enough movement")
        return False
    army.location = destination
    army.movement = max(0, army.movement - cost)
    state.reveal_region(army.faction, destination)
    state.add_event(f"{army.faction} army moved to {REGIONS[destination].name}")
    return True


def reset_movement(state: GameState) -> None:
    for army in state.armies:
        if army.is_patrolling():
            army.movement = 0
            continue
        base_speed = army.max_speed()
        if army.has_naval():
            base_speed = max(base_speed, 3)
            base_speed = base_speed * state.factions[army.faction].naval_modifier()
        weather = state.weather_movement_modifier()
        movement_allowance = int(round(base_speed * weather))
        movement_allowance = max(1, min(5, movement_allowance))
        if not state.region_has_supply(army.faction, army.location):
            movement_allowance = max(1, int(round(movement_allowance * 0.5)))
        army.movement = movement_allowance
