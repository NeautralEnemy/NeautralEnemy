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


def declare_war(state: GameState, faction: str, other: str) -> bool:
    """Force the relation into a war state, returning True when it changed."""

    if other not in state.factions or faction == other:
        return False
    if get_relation(state, faction, other) == "war":
        return False
    set_relation(state, faction, other, "war")
    return True


def offer_peace(state: GameState, faction: str, other: str) -> bool:
    """Attempt to end a war and return to neutrality."""

    if other not in state.factions or faction == other:
        return False
    relation = get_relation(state, faction, other)
    if relation != "war":
        state.add_event(f"{faction} and {other} are not at war")
        return False
    rng = state.rng()
    ours = len(state.regions_owned_by(faction))
    theirs = len(state.regions_owned_by(other))
    base = 0.45
    if ours < theirs:
        base += 0.2
    elif ours > theirs:
        base -= 0.1
    other_regions = state.regions_owned_by(other)
    if other_regions:
        average = sum(reg.stability for reg in other_regions) / len(other_regions)
        base += min(0.15, max(-0.15, average - 0.6))
    if rng.random() <= max(0.1, min(0.9, base)):
        set_relation(state, faction, other, "neutral")
        state.factions[faction].diplomacy.trade.setdefault(other, False)
        state.factions[other].diplomacy.trade.setdefault(faction, False)
        state.add_event(f"{other} accepts peace with {faction}")
        return True
    state.add_event(f"{other} rejects peace with {faction}")
    return False


def propose_alliance(state: GameState, faction: str, other: str) -> bool:
    """Attempt to elevate relations to an alliance."""

    if other not in state.factions or faction == other:
        return False
    relation = get_relation(state, faction, other)
    if relation == "war":
        state.add_event(f"{faction} must secure peace before an alliance with {other}")
        return False
    if relation == "allied":
        state.add_event(f"{faction} and {other} already stand allied")
        return False
    rng = state.rng()
    base = 0.35
    if state.factions[faction].diplomacy.trade.get(other):
        base += 0.25
    if state.factions[other].diplomacy.trade.get(faction):
        base += 0.1
    treasury_ratio = state.factions[faction].treasury / max(1, state.factions[other].treasury)
    if treasury_ratio > 1.2:
        base += 0.05
    elif treasury_ratio < 0.8:
        base -= 0.05
    if rng.random() <= max(0.05, min(0.85, base)):
        set_relation(state, faction, other, "allied")
        state.factions[faction].diplomacy.trade[other] = True
        state.factions[other].diplomacy.trade[faction] = True
        state.add_event(f"{other} joins {faction} in alliance")
        return True
    state.add_event(f"{other} declines an alliance with {faction}")
    return False


def request_trade(state: GameState, faction: str, other: str) -> bool:
    rng = state.rng()
    relation = get_relation(state, faction, other)
    if relation == "war":
        state.add_event(f"{faction} must make peace with {other} first")
        return False
    base = 0.4 if relation == "neutral" else 0.55
    if relation == "allied":
        base = 0.75
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
