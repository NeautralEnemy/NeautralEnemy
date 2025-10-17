"""Simplified tactical battle simulation helpers."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from core.state import GameState, Army
from data.units import UNITS

BOARD_WIDTH = 8
BOARD_HEIGHT = 6


@dataclass
class TacticalUnit:
    side: int
    unit_type: str
    hp: int
    morale: int
    position: Tuple[int, int]
    veterancy: int = 0

    def is_ranged(self) -> bool:
        return UNITS[self.unit_type].range > 1


@dataclass
class TacticalState:
    attacker: Army
    defender: Army
    units: List[TacticalUnit]
    current_side: int = 0
    turn: int = 1
    terrain: Dict[Tuple[int, int], str] = field(default_factory=dict)
    attacker_faction: str = ""
    defender_faction: str = ""

    def alive_units(self, side: int) -> List[TacticalUnit]:
        return [u for u in self.units if u.side == side and u.hp > 0]


def setup_battle(game_state: GameState, attacker: Army, defender: Army, rng: random.Random) -> TacticalState:
    units: List[TacticalUnit] = []
    for i, unit in enumerate(attacker.units):
        units.append(
            TacticalUnit(
                side=0,
                unit_type=unit,
                hp=max(2, int(game_state.unit_defense_value(attacker.faction, unit) / 2)),
                morale=int(6 * game_state.factions[attacker.faction].morale_modifier()) + attacker.experience,
                position=(1, 1 + i),
                veterancy=attacker.experience,
            )
        )
    for i, unit in enumerate(defender.units):
        units.append(
            TacticalUnit(
                side=1,
                unit_type=unit,
                hp=max(2, int(game_state.unit_defense_value(defender.faction, unit) / 2)),
                morale=int(6 * game_state.factions[defender.faction].morale_modifier()) + defender.experience,
                position=(BOARD_WIDTH - 2, 1 + i),
                veterancy=defender.experience,
            )
        )
    terrain: Dict[Tuple[int, int], str] = {}
    features = ["forest", "forest", "hill", "fort"]
    for kind in features:
        for _ in range(4):
            pos = (rng.randint(1, BOARD_WIDTH - 2), rng.randint(0, BOARD_HEIGHT - 1))
            if pos not in terrain:
                terrain[pos] = kind
                break
    return TacticalState(
        attacker=attacker,
        defender=defender,
        units=units,
        terrain=terrain,
        attacker_faction=attacker.faction,
        defender_faction=defender.faction,
    )


def _attack_roll(
    game_state: GameState,
    rng: random.Random,
    state: TacticalState,
    unit: TacticalUnit,
    target: TacticalUnit,
    terrain: Dict[Tuple[int, int], str],
) -> bool:
    attacker_faction = state.attacker_faction if unit.side == 0 else state.defender_faction
    defender_faction = state.attacker_faction if target.side == 0 else state.defender_faction
    base = game_state.unit_attack_value(attacker_faction, unit.unit_type) + max(0, unit.veterancy // 2)
    if unit.is_ranged():
        base += 1
    defense = game_state.unit_defense_value(defender_faction, target.unit_type)
    atk_tile = terrain.get(unit.position)
    def_tile = terrain.get(target.position)
    if atk_tile == "forest":
        base -= 1
    if atk_tile == "hill":
        base += 1
    if def_tile == "forest":
        defense += 1
    if def_tile == "hill":
        defense += 1
    if def_tile == "fort":
        defense += 2
    roll = rng.randint(1, int(base + 3))
    return roll > defense


def simulate_round(game_state: GameState, state: TacticalState, rng: random.Random) -> None:
    for side in (0, 1):
        targets = state.alive_units(1 - side)
        if not targets:
            return
        for unit in list(state.alive_units(side)):
            if not targets:
                break
            target = rng.choice(targets)
            if _attack_roll(game_state, rng, state, unit, target, state.terrain):
                target.hp -= 1
                if target.hp <= 0:
                    targets.remove(target)
            else:
                target.morale -= 1
                if target.morale <= 0:
                    target.hp = 0
                    targets.remove(target)
    state.turn += 1


def determine_winner(state: TacticalState) -> int:
    atk = any(u.hp > 0 for u in state.units if u.side == 0)
    dfn = any(u.hp > 0 for u in state.units if u.side == 1)
    if atk and not dfn:
        return 1
    if dfn and not atk:
        return 0
    return -1


def run_simulation(game_state: GameState, attacker: Army, defender: Army) -> int:
    rng = game_state.rng()
    tactical = setup_battle(game_state, attacker, defender, rng)
    winner = -1
    for _ in range(6):
        simulate_round(game_state, tactical, rng)
        winner = determine_winner(tactical)
        if winner != -1:
            break
    if winner == 1:
        defender.units = []
        attacker.experience = min(attacker.experience + 1, 5)
    elif winner == 0:
        attacker.units = []
        defender.experience = min(defender.experience + 1, 5)
    else:
        attacker.units = attacker.units[:1]
        defender.units = defender.units[:1]
    game_state.add_event("Tactical battle resolved")
    return winner
