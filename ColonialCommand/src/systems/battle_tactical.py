"""Simplified tactical battle simulation."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple

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

    def is_ranged(self) -> bool:
        return UNITS[self.unit_type].range > 1


@dataclass
class TacticalState:
    attacker: Army
    defender: Army
    units: List[TacticalUnit]
    current_side: int = 0
    turn: int = 1

    def alive_units(self, side: int) -> List[TacticalUnit]:
        return [u for u in self.units if u.side == side and u.hp > 0]


def setup_battle(attacker: Army, defender: Army) -> TacticalState:
    units: List[TacticalUnit] = []
    for i, unit in enumerate(attacker.units):
        units.append(TacticalUnit(side=0, unit_type=unit, hp=3, morale=6, position=(1, 1 + i)))
    for i, unit in enumerate(defender.units):
        units.append(TacticalUnit(side=1, unit_type=unit, hp=3, morale=6, position=(BOARD_WIDTH - 2, 1 + i)))
    return TacticalState(attacker=attacker, defender=defender, units=units)


def _attack_roll(rng: random.Random, unit: TacticalUnit, target: TacticalUnit) -> bool:
    stats = UNITS[unit.unit_type]
    base = stats.attack
    if unit.is_ranged():
        base += 1
    defense = UNITS[target.unit_type].defense
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
            if _attack_roll(rng, unit, target):
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
    tactical = setup_battle(attacker, defender)
    for _ in range(6):
        simulate_round(tactical, rng)
        winner = determine_winner(tactical)
        if winner != -1:
            break
    if winner == 1:
        defender.units = []
    elif winner == 0:
        attacker.units = []
    else:
        attacker.units = attacker.units[:1]
        defender.units = defender.units[:1]
    game_state.add_event("Tactical battle resolved")
    return winner
