"""Research system."""
from __future__ import annotations

from core.state import GameState


def handle_research(state: GameState) -> None:
    for faction in state.factions:
        fac = state.factions[faction]
        if fac.research_queue:
            gained = 20
            completed = state.progress_research(faction, gained)
            if completed:
                state.add_event(f"{faction} unlocked {completed}")
