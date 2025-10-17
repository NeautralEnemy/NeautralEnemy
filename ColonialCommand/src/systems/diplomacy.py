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
    if relation == "war":
        state.factions[faction].diplomacy.trade.pop(other, None)
        state.factions[other].diplomacy.trade.pop(faction, None)
    state.add_event(f"{faction} and {other} are now {relation}")


def request_trade(state: GameState, faction: str, other: str) -> bool:
    rng = state.rng()
    relation = get_relation(state, faction, other)
    if relation == "war":
        state.add_event(f"{faction} must make peace with {other} first")
        return False
    base = 0.4 if relation == "neutral" else 0.6
    chance = base * state.factions[faction].trade_modifier() * state.factions[other].trade_modifier()
    if rng.random() < min(0.95, chance):
        state.factions[faction].diplomacy.trade[other] = True
        state.factions[other].diplomacy.trade[faction] = True
        state.add_event(f"{faction} agreed on trade with {other}")
        return True
    state.add_event(f"{other} refused trade with {faction}")
    return False


def trade_income_bonus(state: GameState, faction: str) -> int:
    fac = state.factions[faction]
    bonus = 0
    for partner, active in fac.diplomacy.trade.items():
        if not active:
            continue
        relation = get_relation(state, faction, partner)
        if relation == "war":
            continue
        base = 12 if relation == "allied" else 10
        bonus += int(base * fac.trade_modifier())
    return bonus
