"""Faction definitions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class Faction:
    name: str
    color: int
    bonus: str
    modifiers: Dict[str, float]
    capital: str


FACTIONS: Dict[str, Faction] = {
    "Britain": Faction("Britain", color=12, bonus="+Trade", modifiers={"trade": 0.15}, capital="london"),
    "France": Faction("France", color=28, bonus="+Morale", modifiers={"morale": 0.1}, capital="paris"),
    "Spain": Faction("Spain", color=22, bonus="+Income", modifiers={"income": 0.1}, capital="madrid"),
    "Netherlands": Faction("Netherlands", color=18, bonus="+Naval", modifiers={"naval": 0.2}, capital="amsterdam"),
}

MAJOR_FACTIONS = list(FACTIONS.keys())
