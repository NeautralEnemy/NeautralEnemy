"""Diplomacy helpers."""
from __future__ import annotations

import random

from core.state import GameState


RELATION_LEVELS = ["war", "neutral", "allied"]


def get_relation(state: GameState, faction: str, other: str) -> str:
    return state.factions[faction].diplomacy.relations.get(other, "neutral")


def set_relation(state: GameState, faction: str, other: str, relation: str) -> None:
    state.factions[faction].diplomacy.relations[other] = relation
    state.factions[other].diplomacy.relations[faction] = relation
    state.add_event(f"{faction} and {other} are now {relation}")


def request_trade(state: GameState, faction: str, other: str) -> bool:
    rng = state.rng()
    chance = 0.5
    if state.factions[faction].treasury > 200:
        chance += 0.1
    if rng.random() < chance:
        state.factions[faction].diplomacy.trade[other] = True
        state.factions[other].diplomacy.trade[faction] = True
        state.add_event(f"{faction} agreed on trade with {other}")
        return True
    state.add_event(f"{other} refused trade with {faction}")
    return False


def trade_income_bonus(state: GameState, faction: str) -> int:
    fac = state.factions[faction]
    return sum(10 for partner, active in fac.diplomacy.trade.items() if active)
