"""Auto resolve battles."""
from __future__ import annotations

from typing import Dict

from core.state import GameState, Army
from data.units import UNITS


class BattleResult(Dict[str, int]):
    pass


def resolve_auto(state: GameState, attacker: Army, defender: Army) -> BattleResult:
    atk_power = sum(UNITS[u].attack for u in attacker.units)
    def_power = sum(UNITS[u].defense for u in defender.units)
    morale_bonus = state.factions[attacker.faction].morale_modifier()
    atk_score = atk_power * morale_bonus
    def_score = def_power
    rng = state.rng()
    atk_roll = atk_score * (0.8 + rng.random() * 0.4)
    def_roll = def_score * (0.8 + rng.random() * 0.4)
    if atk_roll > def_roll:
        losses = min(len(attacker.units), max(1, int(len(attacker.units) * 0.2)))
        attacker.units = attacker.units[:-losses] if losses < len(attacker.units) else []
        defender.units = []
        state.add_event(f"{attacker.faction} wins with auto-resolve")
        return BattleResult(winner=1)
    else:
        losses = min(len(defender.units), max(1, int(len(defender.units) * 0.2)))
        defender.units = defender.units[:-losses] if losses < len(defender.units) else []
        attacker.units = []
        state.add_event(f"{defender.faction} defends successfully")
        return BattleResult(winner=0)
