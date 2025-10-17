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

    def alive_units(self, side: int) -> List[TacticalUnit]:
        return [u for u in self.units if u.side == side and u.hp > 0]


def setup_battle(attacker: Army, defender: Army, rng: random.Random) -> TacticalState:
    units: List[TacticalUnit] = []
    for i, unit in enumerate(attacker.units):
        units.append(
            TacticalUnit(
                side=0,
                unit_type=unit,
                hp=3,
                morale=6 + attacker.experience,
                position=(1, 1 + i),
                veterancy=attacker.experience,
            )
        )
    for i, unit in enumerate(defender.units):
        units.append(
            TacticalUnit(
                side=1,
                unit_type=unit,
                hp=3,
                morale=6 + defender.experience,
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
    return TacticalState(attacker=attacker, defender=defender, units=units, terrain=terrain)


def _attack_roll(rng: random.Random, unit: TacticalUnit, target: TacticalUnit, terrain: Dict[Tuple[int, int], str]) -> bool:
    stats = UNITS[unit.unit_type]
    base = stats.attack + max(0, unit.veterancy // 2)
    if unit.is_ranged():
        base += 1
    defense = UNITS[target.unit_type].defense
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
    roll = rng.randint(1, base + 3)
    return roll > defense


def simulate_round(state: TacticalState, rng: random.Random) -> None:
    for side in (0, 1):
        targets = state.alive_units(1 - side)
        if not targets:
            return
        for unit in list(state.alive_units(side)):
            if not targets:
                break
            target = rng.choice(targets)
            if _attack_roll(rng, unit, target, state.terrain):
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
    tactical = setup_battle(attacker, defender, rng)
    winner = -1
    for _ in range(6):
        simulate_round(tactical, rng)
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
