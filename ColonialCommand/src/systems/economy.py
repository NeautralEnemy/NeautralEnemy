"""Economic systems."""
from __future__ import annotations

from core.state import GameState


def resolve_turn_economy(state: GameState) -> None:
    for faction in state.factions:
        delta = state.apply_income(faction)
        if delta < 0:
            state.add_event(f"{faction} suffers deficit {delta}")
