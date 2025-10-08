"""Region graph covering multiple theaters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RegionDef:
    key: str
    name: str
    location: tuple[int, int]
    neighbors: List[str]
    resource: str
    base_income: int


REGIONS: Dict[str, RegionDef] = {
    "london": RegionDef("london", "Great Britain", (70, 60), ["paris", "dublin"], "textiles", 40),
    "paris": RegionDef("paris", "Île-de-France", (100, 70), ["london", "madrid", "amsterdam", "vienna"], "wine", 38),
    "madrid": RegionDef("madrid", "Castile", (90, 110), ["paris", "lisbon", "algiers"], "silver", 36),
    "lisbon": RegionDef("lisbon", "Portugal", (70, 120), ["madrid", "azores"], "spices", 30),
    "amsterdam": RegionDef("amsterdam", "Netherlands", (110, 60), ["paris", "copenhagen", "vienna"], "trade", 34),
    "copenhagen": RegionDef("copenhagen", "Denmark", (130, 50), ["amsterdam", "stockholm"], "timber", 28),
    "stockholm": RegionDef("stockholm", "Sweden", (150, 40), ["copenhagen", "stpetersburg"], "iron", 26),
    "stpetersburg": RegionDef("stpetersburg", "Russia", (180, 40), ["stockholm", "vienna"], "fur", 24),
    "vienna": RegionDef("vienna", "Austria", (140, 80), ["paris", "amsterdam", "stpetersburg", "istanbul"], "manufactories", 32),
    "istanbul": RegionDef("istanbul", "Ottomans", (180, 90), ["vienna", "cairo"], "coffee", 34),
    "cairo": RegionDef("cairo", "Egypt", (200, 120), ["istanbul", "tripoli"], "grain", 26),
    "tripoli": RegionDef("tripoli", "Tripoli", (180, 130), ["cairo", "algiers"], "corsairs", 22),
    "algiers": RegionDef("algiers", "Algiers", (150, 130), ["tripoli", "madrid"], "dates", 20),
    "dublin": RegionDef("dublin", "Ireland", (60, 70), ["london", "newyork"], "linen", 24),
    "newyork": RegionDef("newyork", "New York", (40, 80), ["dublin", "virginia", "caribbean"], "fur", 28),
    "virginia": RegionDef("virginia", "Virginia", (30, 100), ["newyork", "caribbean"], "tobacco", 32),
    "caribbean": RegionDef("caribbean", "Caribbean", (50, 120), ["virginia", "newyork", "havana", "azores", "cape"], "sugar", 36),
    "havana": RegionDef("havana", "Cuba", (60, 140), ["caribbean", "yucatan"], "rum", 30),
    "yucatan": RegionDef("yucatan", "Yucatán", (40, 150), ["havana", "newgranada"], "dyes", 22),
    "newgranada": RegionDef("newgranada", "New Granada", (30, 170), ["yucatan"], "gold", 26),
    "azores": RegionDef("azores", "Azores", (90, 150), ["caribbean", "lisbon"], "naval", 18),
    "bombay": RegionDef("bombay", "Bombay", (260, 140), ["calcutta", "cape"], "spices", 40),
    "calcutta": RegionDef("calcutta", "Calcutta", (280, 130), ["bombay"], "tea", 36),
    "cape": RegionDef("cape", "Cape Colony", (220, 160), ["bombay", "caribbean"], "harbor", 30),
}
