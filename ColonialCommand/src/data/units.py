"""Unit definitions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class UnitType:
    key: str
    name: str
    attack: int
    defense: int
    range: int
    speed: int
    morale: int
    upkeep: int


UNITS: Dict[str, UnitType] = {
    "line": UnitType("line", "Line Infantry", attack=6, defense=5, range=4, speed=2, morale=6, upkeep=10),
    "militia": UnitType("militia", "Militia", attack=4, defense=3, range=3, speed=2, morale=4, upkeep=6),
    "cavalry": UnitType("cavalry", "Cavalry", attack=7, defense=4, range=1, speed=4, morale=6, upkeep=12),
    "artillery": UnitType("artillery", "Artillery", attack=8, defense=3, range=6, speed=1, morale=5, upkeep=14),
    "sloop": UnitType("sloop", "Sloop", attack=5, defense=4, range=5, speed=3, morale=5, upkeep=8),
    "frigate": UnitType("frigate", "Frigate", attack=7, defense=5, range=6, speed=3, morale=6, upkeep=12),
}
