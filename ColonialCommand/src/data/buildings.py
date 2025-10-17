"""Building definitions for regional development."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class BuildingDef:
    """Static data describing an upgrade option for a region."""

    key: str
    name: str
    description: str
    effect: str
    cost: int
    build_time: int
    max_level: int


BUILDINGS: Dict[str, BuildingDef] = {
    "market": BuildingDef(
        key="market",
        name="Market",
        description="Invest in local merchants and warehouses.",
        effect="Income +6 per level; boosts economy slightly",
        cost=80,
        build_time=2,
        max_level=3,
    ),
    "fort": BuildingDef(
        key="fort",
        name="Fort",
        description="Raise permanent defenses and trained guards.",
        effect="Defenders gain fortification bonus; slows attrition",
        cost=90,
        build_time=3,
        max_level=2,
    ),
    "culture": BuildingDef(
        key="culture",
        name="Culture",
        description="Support theatres, churches, and civic projects.",
        effect="Stability recovery while supplied; morale boost",
        cost=70,
        build_time=2,
        max_level=2,
    ),
    "capital": BuildingDef(
        key="capital",
        name="Capital Works",
        description="Expand the seat of government with parade grounds and arsenals.",
        effect="Improves supply network, recruitment throughput, and capital defenses",
        cost=110,
        build_time=3,
        max_level=3,
    ),
}


ORDERED_BUILDINGS: List[str] = ["market", "fort", "culture", "capital"]
"""Stable iteration order for UI cycling and AI heuristics."""

