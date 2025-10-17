"""Auto resolve battles."""
from __future__ import annotations

from typing import Dict, Optional

from core.state import GameState, Army


class BattleResult(Dict[str, int]):
    pass


def resolve_auto(
    state: GameState,
    attacker: Army,
    defender: Army,
    location: Optional[str] = None,
) -> BattleResult:
    location = location or defender.location
    attacker_start = len(attacker.units)
    defender_start = len(defender.units)
    atk_power = sum(state.unit_attack_value(attacker.faction, u) for u in attacker.units) + attacker.experience * 2
    def_power = sum(state.unit_defense_value(defender.faction, u) for u in defender.units) + defender.experience * 2
    atk_score = atk_power * state.weather_attack_modifier()
    def_score = def_power * state.weather_defense_modifier()
    if location:
        def_score += state.region_defense_bonus(location)
        if not state.region_has_supply(defender.faction, location):
            def_score = int(def_score * 0.9)
    rng = state.rng()
    atk_roll = atk_score * (0.8 + rng.random() * 0.4)
    def_roll = def_score * (0.8 + rng.random() * 0.4)
    if atk_roll > def_roll:
        losses = min(len(attacker.units), max(1, int(len(attacker.units) * 0.2)))
        attacker.units = attacker.units[:-losses] if losses < len(attacker.units) else []
        defender.units = []
        state.add_event(f"{attacker.faction} wins with auto-resolve")
        attacker.experience = min(attacker.experience + 1, 5)
        attacker_losses = max(0, attacker_start - len(attacker.units))
        defender_losses = defender_start
        state.record_battle(
            location=location,
            attacker=attacker.faction,
            defender=defender.faction,
            winner=attacker.faction,
            battle_type="auto",
            attacker_losses=attacker_losses,
            defender_losses=defender_losses,
        )
        return BattleResult(winner=1)
    else:
        losses = min(len(defender.units), max(1, int(len(defender.units) * 0.2)))
        defender.units = defender.units[:-losses] if losses < len(defender.units) else []
        attacker.units = []
        state.add_event(f"{defender.faction} defends successfully")
        defender.experience = min(defender.experience + 1, 5)
        defender_losses = max(0, defender_start - len(defender.units))
        attacker_losses = attacker_start
        state.record_battle(
            location=location,
            attacker=attacker.faction,
            defender=defender.faction,
            winner=defender.faction,
            battle_type="auto",
            attacker_losses=attacker_losses,
            defender_losses=defender_losses,
        )
        return BattleResult(winner=0)
