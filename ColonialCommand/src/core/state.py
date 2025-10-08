"""Game state and serialization."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

from data.factions import FACTIONS, MAJOR_FACTIONS
from data.regions import REGIONS, RegionDef
from data.units import UNITS, UnitType
from data.tech import TECH_TREE

SAVES_DIR = Path("saves")

SEASONS = ["Spring", "Summer", "Autumn", "Winter"]


@dataclass
class Army:
    faction: str
    location: str
    units: List[str]
    movement: int = 1

    def power(self) -> int:
        return sum(UNITS[u].attack + UNITS[u].defense for u in self.units)


@dataclass
class RegionState:
    key: str
    owner: str
    population: int
    economy: int
    stability: float
    garrison: List[str]
    discovered: bool = False

    def income(self) -> int:
        return int(self.economy * max(0.4, self.stability))


@dataclass
class Diplomacy:
    relations: Dict[str, str] = field(default_factory=dict)
    trade: Dict[str, bool] = field(default_factory=dict)


@dataclass
class FactionState:
    name: str
    treasury: int
    tech_progress: Dict[str, int] = field(default_factory=lambda: {"economy": 0, "military": 0, "naval": 0})
    research_queue: Optional[str] = None
    research_points: int = 0
    diplomacy: Diplomacy = field(default_factory=Diplomacy)

    def income_modifier(self) -> float:
        faction = FACTIONS[self.name]
        return 1.0 + faction.modifiers.get("income", 0.0)

    def morale_modifier(self) -> float:
        faction = FACTIONS[self.name]
        return 1.0 + faction.modifiers.get("morale", 0.0)


@dataclass
class GameState:
    factions: Dict[str, FactionState]
    regions: Dict[str, RegionState]
    armies: List[Army]
    turn: int
    season_index: int
    year: int
    rng_seed: int
    fog_of_war: Dict[str, List[str]] = field(default_factory=dict)
    last_events: List[str] = field(default_factory=list)

    @classmethod
    def new_game(cls, seed: Optional[int] = None) -> "GameState":
        rng = random.Random(seed or random.randint(0, 999999))
        seed_value = rng.randint(0, 999999)
        rng.seed(seed_value)
        factions = {name: FactionState(name=name, treasury=200) for name in MAJOR_FACTIONS}
        regions: Dict[str, RegionState] = {}
        assignments = list(MAJOR_FACTIONS)
        extended = assignments + ["Britain", "France", "Spain", "Netherlands"]
        i = 0
        for key, reg in REGIONS.items():
            owner = extended[i % len(extended)]
            population = rng.randint(2, 6) * 100
            economy = reg.base_income
            stability = rng.uniform(0.6, 1.0)
            garrison = ["militia"]
            regions[key] = RegionState(key=key, owner=owner, population=population, economy=economy, stability=stability, garrison=garrison, discovered=(owner == "Britain"))
            i += 1
        armies = [Army(faction="Britain", location="london", units=["line", "line", "cavalry"])]
        fog = {fac: ["london"] for fac in factions}
        for fac in factions:
            fog.setdefault(fac, [])
        for region in regions.values():
            fog.setdefault(region.owner, [])
            if region.key not in fog[region.owner]:
                fog[region.owner].append(region.key)
        return cls(
            factions=factions,
            regions=regions,
            armies=armies,
            turn=1,
            season_index=0,
            year=1700,
            rng_seed=seed_value,
            fog_of_war=fog,
            last_events=["Campaign begins"]
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        factions = {
            name: FactionState(
                name=name,
                treasury=fac["treasury"],
                tech_progress=fac.get("tech_progress", {"economy": 0, "military": 0, "naval": 0}),
                research_queue=fac.get("research_queue"),
                research_points=fac.get("research_points", 0),
                diplomacy=Diplomacy(
                    relations=fac.get("diplomacy", {}).get("relations", {}),
                    trade=fac.get("diplomacy", {}).get("trade", {}),
                ),
            )
            for name, fac in data["factions"].items()
        }
        regions = {
            key: RegionState(
                key=key,
                owner=reg["owner"],
                population=reg["population"],
                economy=reg["economy"],
                stability=reg.get("stability", 1.0),
                garrison=list(reg.get("garrison", [])),
                discovered=reg.get("discovered", False),
            )
            for key, reg in data["regions"].items()
        }
        armies = [Army(**army) for army in data.get("armies", [])]
        return cls(
            factions=factions,
            regions=regions,
            armies=armies,
            turn=data.get("turn", 1),
            season_index=data.get("season_index", 0),
            year=data.get("year", 1700),
            rng_seed=data.get("rng_seed", 0),
            fog_of_war=data.get("fog_of_war", {}),
            last_events=data.get("last_events", []),
        )

    @classmethod
    def load(cls, slot: str) -> Optional["GameState"]:
        path = SAVES_DIR / f"{slot}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return cls.from_dict(data)

    def save(self, slot: str) -> None:
        path = SAVES_DIR / f"{slot}.json"
        path.write_text(self.to_json())

    def advance_turn(self) -> None:
        self.turn += 1
        self.season_index = (self.season_index + 1) % len(SEASONS)
        if self.season_index == 0:
            self.year += 1

    def rng(self) -> random.Random:
        return random.Random(self.rng_seed + self.turn)

    def reveal_region(self, faction: str, region: str) -> None:
        self.fog_of_war.setdefault(faction, [])
        if region not in self.fog_of_war[faction]:
            self.fog_of_war[faction].append(region)

    def regions_owned_by(self, faction: str) -> List[RegionState]:
        return [reg for reg in self.regions.values() if reg.owner == faction]

    def get_region(self, key: str) -> RegionState:
        return self.regions[key]

    def add_event(self, text: str) -> None:
        self.last_events.append(text)
        if len(self.last_events) > 12:
            self.last_events = self.last_events[-12:]

    def upkeep_cost(self, faction: str) -> int:
        total = 0
        for reg in self.regions.values():
            if reg.owner == faction:
                total += sum(UNITS[u].upkeep for u in reg.garrison)
        for army in self.armies:
            if army.faction == faction:
                total += sum(UNITS[u].upkeep for u in army.units)
        return total

    def apply_income(self, faction: str) -> int:
        fac_state = self.factions[faction]
        income = int(sum(reg.income() for reg in self.regions_owned_by(faction)) * fac_state.income_modifier())
        try:
            from systems.diplomacy import trade_income_bonus

            income += trade_income_bonus(self, faction)
        except Exception:
            pass
        upkeep = self.upkeep_cost(faction)
        fac_state.treasury += income - upkeep
        self.add_event(f"{faction} income {income} - upkeep {upkeep} = {income - upkeep}")
        return income - upkeep

    def queue_research(self, faction: str, category: str) -> bool:
        fac = self.factions[faction]
        if fac.research_queue == category:
            return True
        if category not in TECH_TREE:
            return False
        if fac.tech_progress.get(category, 0) >= len(TECH_TREE[category]):
            return False
        fac.research_queue = category
        fac.research_points = 0
        self.add_event(f"{faction} began researching {category} tech")
        return True

    def progress_research(self, faction: str, amount: int) -> Optional[str]:
        fac = self.factions[faction]
        if not fac.research_queue:
            return None
        fac.research_points += amount
        tier = fac.tech_progress[fac.research_queue]
        node = TECH_TREE[fac.research_queue][tier]
        if fac.research_points >= node.cost:
            fac.tech_progress[fac.research_queue] += 1
            fac.research_queue = None
            fac.research_points = 0
            self.add_event(f"{faction} researched {node.name}")
            return node.key
        return None
