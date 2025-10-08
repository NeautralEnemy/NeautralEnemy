"""Simple tech trees."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class TechNode:
    key: str
    name: str
    tier: int
    category: str
    cost: int
    bonus: Dict[str, float]


TECH_TREE: Dict[str, List[TechNode]] = {
    "economy": [
        TechNode("marketplaces", "Marketplaces", tier=1, category="economy", cost=80, bonus={"income": 0.1}),
        TechNode("mercantilism", "Mercantilism", tier=2, category="economy", cost=120, bonus={"trade": 0.1}),
        TechNode("industrialization", "Industrialization", tier=3, category="economy", cost=180, bonus={"income": 0.2}),
    ],
    "military": [
        TechNode("drill", "Drill Manuals", tier=1, category="military", cost=80, bonus={"morale": 0.1}),
        TechNode("bayonet", "Socket Bayonet", tier=2, category="military", cost=120, bonus={"attack": 1}),
        TechNode("grand_battery", "Grand Battery", tier=3, category="military", cost=180, bonus={"artillery": 1}),
    ],
    "naval": [
        TechNode("drydocks", "Dry Docks", tier=1, category="naval", cost=80, bonus={"naval": 0.1}),
        TechNode("navigation", "Navigation", tier=2, category="naval", cost=120, bonus={"naval": 0.15}),
        TechNode("convoys", "Convoy System", tier=3, category="naval", cost=160, bonus={"trade": 0.1}),
    ],
}
