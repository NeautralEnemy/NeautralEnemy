"""Movement system."""
from __future__ import annotations

from typing import Optional

from core.state import GameState, Army
from data.regions import REGIONS


def move_army(state: GameState, army: Army, destination: str) -> bool:
    if destination not in REGIONS:
        return False
    region = state.get_region(army.location)
    if destination not in REGIONS[region.key].neighbors:
        return False
    army.location = destination
    army.movement = max(0, army.movement - 1)
    state.reveal_region(army.faction, destination)
    state.add_event(f"{army.faction} army moved to {REGIONS[destination].name}")
    return True


def reset_movement(state: GameState) -> None:
    for army in state.armies:
        army.movement = 1
