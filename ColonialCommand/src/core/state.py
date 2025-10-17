"""Game state and serialization."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from data.factions import FACTIONS, MAJOR_FACTIONS
from data.regions import (
    REGIONS,
    RegionDef,
    RESOURCE_INCOME_BONUS,
    RESOURCE_RECRUIT_UNITS,
    is_sea_lane,
)
from data.units import UNITS, UnitType
from data.tech import TECH_TREE, TechNode

SAVES_DIR = Path("saves")

SEASONS = ["Spring", "Summer", "Autumn", "Winter"]


@dataclass
class Army:
    faction: str
    location: str
    units: List[str]
    movement: int = 1
    experience: int = 0

    def power(self) -> int:
        base = sum(UNITS[u].attack + UNITS[u].defense for u in self.units)
        return base + self.experience * 2

    def has_naval(self) -> bool:
        return any(unit in ("sloop", "frigate") for unit in self.units)

    def max_speed(self) -> int:
        if not self.units:
            return 1
        return max(UNITS[u].speed for u in self.units)


@dataclass
class RegionState:
    key: str
    owner: str
    population: int
    economy: int
    stability: float
    garrison: List[str]
    discovered: bool = False
    recruit_queue: List[str] = field(default_factory=list)

    def income(self) -> int:
        resource = REGIONS[self.key].resource
        multiplier = 1.0 + RESOURCE_INCOME_BONUS.get(resource, 0.0)
        return int(self.economy * multiplier * max(0.4, self.stability))


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
    bonus_modifiers: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        faction = FACTIONS.get(self.name)
        if faction:
            for key, value in faction.modifiers.items():
                self.bonus_modifiers.setdefault(key, 0.0)
                if self.bonus_modifiers[key] == 0.0:
                    self.bonus_modifiers[key] = value

    def get_modifier(self, key: str) -> float:
        return self.bonus_modifiers.get(key, 0.0)

    def apply_bonus(self, bonus: Dict[str, float]) -> None:
        for key, value in bonus.items():
            self.bonus_modifiers[key] = self.bonus_modifiers.get(key, 0.0) + value

    def income_modifier(self) -> float:
        return 1.0 + self.get_modifier("income")

    def morale_modifier(self) -> float:
        return 1.0 + self.get_modifier("morale")

    def trade_modifier(self) -> float:
        return 1.0 + self.get_modifier("trade")

    def naval_modifier(self) -> float:
        return 1.0 + self.get_modifier("naval")

    def attack_bonus(self, unit_key: str) -> float:
        bonus = self.get_modifier("attack")
        if unit_key == "artillery":
            bonus += self.get_modifier("artillery")
        return bonus


@dataclass
class Objective:
    id: str
    description: str
    type: str
    target: int
    completed: bool = False


@dataclass
class EventChoice:
    label: str
    effect: str
    result: str


@dataclass
class StoryEvent:
    id: str
    faction: str
    title: str
    description: str
    choices: List[EventChoice]


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
    objectives: Dict[str, List[Objective]] = field(default_factory=dict)
    pending_events: List[StoryEvent] = field(default_factory=list)
    research_notifications: List[Tuple[str, str]] = field(default_factory=list)

    @classmethod
    def new_game(cls, seed: Optional[int] = None) -> "GameState":
        rng = random.Random(seed or random.randint(0, 999999))
        seed_value = rng.randint(0, 999999)
        rng.seed(seed_value)
        factions = {name: FactionState(name=name, treasury=200) for name in MAJOR_FACTIONS}
        for name, fac in factions.items():
            for other in factions:
                if other == name:
                    continue
                fac.diplomacy.relations.setdefault(other, "neutral")
                fac.diplomacy.trade.setdefault(other, False)
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
        objectives = {
            "Britain": [
                Objective("expand", "Control 4 regions", "regions", 4),
                Objective("wealth", "Reach a treasury of 400", "treasury", 400),
                Objective("innovation", "Complete 1 technology", "tech", 1),
            ]
        }
        return cls(
            factions=factions,
            regions=regions,
            armies=armies,
            turn=1,
            season_index=0,
            year=1700,
            rng_seed=seed_value,
            fog_of_war=fog,
            last_events=["Campaign begins"],
            objectives=objectives,
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
                bonus_modifiers=dict(fac.get("bonus_modifiers", {})),
            )
            for name, fac in data["factions"].items()
        }
        for name, fac in factions.items():
            for other in factions:
                if other == name:
                    continue
                fac.diplomacy.relations.setdefault(other, "neutral")
                fac.diplomacy.trade.setdefault(other, False)
        regions = {
            key: RegionState(
                key=key,
                owner=reg["owner"],
                population=reg["population"],
                economy=reg["economy"],
                stability=reg.get("stability", 1.0),
                garrison=list(reg.get("garrison", [])),
                discovered=reg.get("discovered", False),
                recruit_queue=list(reg.get("recruit_queue", [])),
            )
            for key, reg in data["regions"].items()
        }
        armies = [
            Army(
                faction=army["faction"],
                location=army["location"],
                units=list(army.get("units", [])),
                movement=army.get("movement", 1),
                experience=army.get("experience", 0),
            )
            for army in data.get("armies", [])
        ]
        objectives = {
            fac: [
                Objective(
                    id=obj.get("id", f"obj{i}"),
                    description=obj.get("description", "Objective"),
                    type=obj.get("type", "regions"),
                    target=obj.get("target", 1),
                    completed=obj.get("completed", False),
                )
                for i, obj in enumerate(objs)
            ]
            for fac, objs in data.get("objectives", {}).items()
        }
        pending_events = [
            StoryEvent(
                id=evt.get("id", "event"),
                faction=evt.get("faction", "Britain"),
                title=evt.get("title", "Event"),
                description=evt.get("description", ""),
                choices=[
                    EventChoice(
                        label=choice.get("label", "OK"),
                        effect=choice.get("effect", ""),
                        result=choice.get("result", ""),
                    )
                    for choice in evt.get("choices", [])
                ],
            )
            for evt in data.get("pending_events", [])
        ]
        research_notifications = [tuple(item) for item in data.get("research_notifications", [])]
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
            objectives=objectives,
            pending_events=pending_events,
            research_notifications=research_notifications,
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

    def apply_tech_bonus(self, faction: str, node: TechNode) -> None:
        fac = self.factions[faction]
        fac.apply_bonus(node.bonus)

    def unit_attack_value(self, faction: str, unit_key: str) -> float:
        base = UNITS[unit_key].attack
        return base + self.factions[faction].attack_bonus(unit_key)

    def unit_defense_value(self, faction: str, unit_key: str) -> float:
        base = UNITS[unit_key].defense
        morale_bonus = self.factions[faction].morale_modifier()
        return base * morale_bonus

    def available_recruits(self, region: RegionState) -> List[str]:
        options = ["militia", "line"]
        resource = REGIONS[region.key].resource
        for unit in RESOURCE_RECRUIT_UNITS.get(resource, []):
            if unit not in options:
                options.append(unit)
        owner = region.owner
        fac = self.factions.get(owner)
        if fac:
            military_tier = fac.tech_progress.get("military", 0)
            naval_tier = fac.tech_progress.get("naval", 0)
            if military_tier >= 1 and "cavalry" not in options:
                options.append("cavalry")
            if military_tier >= 2 and "artillery" not in options:
                options.append("artillery")
            if naval_tier >= 1 and "sloop" not in options:
                options.append("sloop")
            if naval_tier >= 2 and "frigate" not in options:
                options.append("frigate")
        return options

    def recruit_cost(self, unit_key: str) -> int:
        unit = UNITS[unit_key]
        base = 30 + unit.upkeep * 3
        if unit_key in ("artillery", "frigate"):
            base += 25
        if unit_key == "sloop":
            base += 15
        if unit_key == "cavalry":
            base += 20
        return base

    def army_has_naval_support(self, army: Army, destination: Optional[str] = None) -> bool:
        if army.has_naval():
            return True
        origin_resource = REGIONS[army.location].resource
        if origin_resource in ("naval", "harbor", "trade", "corsairs"):
            return self.factions[army.faction].naval_modifier() > 1.0
        if destination:
            dest_resource = REGIONS[destination].resource
            if dest_resource in ("naval", "harbor", "trade", "corsairs"):
                return self.factions[army.faction].naval_modifier() > 1.0
        return False

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
            self.research_notifications.append((faction, node.name))
            self.apply_tech_bonus(faction, node)
            return node.key
        return None

    # Objective helpers -------------------------------------------------

    def ensure_objectives(self, faction: str) -> List[Objective]:
        if faction not in self.objectives:
            self.objectives[faction] = [
                Objective("expand", "Control 4 regions", "regions", 4),
                Objective("wealth", "Reach a treasury of 400", "treasury", 400),
                Objective("innovation", "Complete 1 technology", "tech", 1),
            ]
        return self.objectives[faction]

    def evaluate_objectives(self, faction: str) -> List[Tuple[Objective, int, int]]:
        objectives = self.ensure_objectives(faction)
        results: List[Tuple[Objective, int, int]] = []
        for obj in objectives:
            current = 0
            if obj.type == "regions":
                current = len(self.regions_owned_by(faction))
            elif obj.type == "treasury":
                current = self.factions[faction].treasury
            elif obj.type == "tech":
                current = sum(self.factions[faction].tech_progress.values())
            if current >= obj.target and not obj.completed:
                obj.completed = True
                self.add_event(f"Objective complete: {obj.description}")
            results.append((obj, current, obj.target))
        return results

    # Recruitment -------------------------------------------------------

    def process_recruitment(self) -> None:
        for region in self.regions.values():
            if region.recruit_queue:
                unit_key = region.recruit_queue.pop(0)
                region.garrison.append(unit_key)
                unit_name = UNITS[unit_key].name
                region_name = REGIONS[region.key].name
                self.add_event(f"{region.owner} raised {unit_name} in {region_name}")

    # Narrative events --------------------------------------------------

    def has_pending_events(self, faction: str) -> bool:
        return any(evt for evt in self.pending_events if evt.faction == faction)

    def pop_next_event(self, faction: str) -> Optional[StoryEvent]:
        for idx, evt in enumerate(self.pending_events):
            if evt.faction == faction:
                return self.pending_events.pop(idx)
        return None

    def prepare_turn_events(self, faction: str) -> None:
        rng = self.rng()
        chance = 0.35
        if rng.random() > chance:
            return
        templates = [
            (
                "harbor_fire",
                "Harbor Fire!",
                "A blaze engulfs warehouses near the docks. Merchants plead for support.",
                [
                    ("Send relief", "treasury:-80", "Funds sent to rebuild the harbor"),
                    ("Let insurance handle it", "stability:-5", "Merchants grumble about neglect"),
                ],
            ),
            (
                "colonial_windfall",
                "Colonial Windfall",
                "A rich shipment from the colonies arrives ahead of schedule.",
                [
                    ("Sell at auction", "treasury:+120", "Treasury swells with silver"),
                    ("Invest in colonies", "stability:+5", "Colonial governors praise your support"),
                ],
            ),
            (
                "innovation_push",
                "Inventor's Proposal",
                "A tinkerer claims to speed musket drills if funded.",
                [
                    ("Back the idea", "research:+30", "Research surges ahead"),
                    ("Decline politely", "treasury:+40", "Funds saved for other ventures"),
                ],
            ),
        ]
        template = rng.choice(templates)
        choices = [EventChoice(label=lbl, effect=eff, result=res) for lbl, eff, res in template[3]]
        event = StoryEvent(
            id=template[0],
            faction=faction,
            title=template[1],
            description=template[2],
            choices=choices,
        )
        self.pending_events.append(event)

    def faction_capital(self, faction: str) -> Optional[str]:
        faction_def = FACTIONS.get(faction)
        if not faction_def:
            return None
        return faction_def.capital

    def pop_research_notification(self) -> Optional[Tuple[str, str]]:
        if self.research_notifications:
            return self.research_notifications.pop(0)
        return None

    def resolve_event_choice(self, faction: str, choice: EventChoice) -> None:
        kind, _, value = choice.effect.partition(":")
        if kind == "treasury":
            delta = int(float(value or 0))
            self.factions[faction].treasury += delta
        elif kind == "stability":
            delta = float(value or 0) / 100.0
            region_key = self.faction_capital(faction)
            region = self.regions.get(region_key) if region_key else None
            if region:
                region.stability = max(0.2, min(1.4, region.stability + delta))
        elif kind == "research":
            boost = int(float(value or 0) or 20)
            fac = self.factions[faction]
            if not fac.research_queue:
                for category, nodes in TECH_TREE.items():
                    if fac.tech_progress.get(category, 0) < len(nodes):
                        fac.research_queue = category
                        fac.research_points = 0
                        break
            if fac.research_queue:
                fac.research_points += boost
        self.add_event(choice.result)

