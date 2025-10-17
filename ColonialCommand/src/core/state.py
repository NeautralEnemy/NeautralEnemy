"""Game state and serialization."""
from __future__ import annotations

import json
import random
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from data.buildings import BUILDINGS, ORDERED_BUILDINGS, BuildingDef
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

WEATHER_PROFILES = {
    "Spring": {"movement": 1.0, "attack": 1.0, "defense": 1.0},
    "Summer": {"movement": 1.15, "attack": 1.05, "defense": 0.95},
    "Autumn": {"movement": 0.95, "attack": 1.0, "defense": 1.05},
    "Winter": {"movement": 0.75, "attack": 0.9, "defense": 1.15},
}

WEATHER_DESCRIPTIONS = {
    "Spring": "Roads thaw; conditions are balanced.",
    "Summer": "Dry roads quicken marches but defenses suffer heat fatigue.",
    "Autumn": "Rains slow supply columns while defenders dig in.",
    "Winter": "Bitter cold saps assaults yet bolsters defensive stands.",
}

SEASONAL_EVENTS: Dict[str, List[dict]] = {
    "Spring": [
        {
            "id": "spring_bloom",
            "name": "Spring Bloom",
            "description": "Bountiful harvest forecasts lift provincial income.",
            "income": 0.12,
            "stability": 0.02,
        },
        {
            "id": "spring_floods",
            "name": "Thaw Flooding",
            "description": "Meltwater floods hamper roads and supply trains.",
            "supply": -0.2,
            "movement": -0.1,
        },
    ],
    "Summer": [
        {
            "id": "summer_drought",
            "name": "Dry Drought",
            "description": "Parched fields dent income and rile the populace.",
            "income": -0.1,
            "stability": -0.03,
        },
        {
            "id": "summer_winds",
            "name": "Steady Trade Winds",
            "description": "Reliable winds speed convoys and naval patrols.",
            "naval": 0.15,
        },
    ],
    "Autumn": [
        {
            "id": "autumn_harvest",
            "name": "Rich Harvest",
            "description": "Granaries swell, easing supply concerns and morale.",
            "supply": 0.25,
            "stability": 0.04,
        },
        {
            "id": "autumn_storms",
            "name": "Atlantic Storms",
            "description": "Tempests endanger trade convoys and naval patrols.",
            "naval": -0.2,
            "attack": -0.05,
        },
    ],
    "Winter": [
        {
            "id": "winter_freeze",
            "name": "Deep Freeze",
            "description": "Frozen roads strangle supply and batter armies.",
            "supply": -0.25,
            "attack": -0.1,
        },
        {
            "id": "winter_markets",
            "name": "Winter Markets",
            "description": "Festivals and markets buoy trade income despite the chill.",
            "income": 0.08,
        },
    ],
}

GOVERNOR_TRAITS = {
    "merchant": {
        "description": "Merchant guilds swell tax coffers.",
        "income": 0.18,
    },
    "steward": {
        "description": "A steady steward soothes unrest.",
        "stability": 0.04,
    },
    "drillmaster": {
        "description": "Drillmasters hasten recruitment queues.",
        "extra_recruit": 1,
    },
    "spymaster": {
        "description": "Spymasters sharpen covert operations.",
        "spy_bonus": 0.2,
    },
}


@dataclass
class Army:
    faction: str
    location: str
    units: List[str]
    movement: int = 1
    experience: int = 0
    patrol_target: Optional[str] = None
    patrol_turns: int = 0

    def power(self) -> int:
        base = sum(UNITS[u].attack + UNITS[u].defense for u in self.units)
        return base + self.experience * 2

    def has_naval(self) -> bool:
        return any(unit in ("sloop", "frigate") for unit in self.units)

    def max_speed(self) -> int:
        if not self.units:
            return 1
        return max(UNITS[u].speed for u in self.units)

    def is_patrolling(self) -> bool:
        return self.patrol_target is not None


@dataclass
class ConstructionProject:
    building: str
    turns_left: int


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
    buildings: Dict[str, int] = field(default_factory=dict)
    project: Optional[ConstructionProject] = None
    unsupplied_turns: int = 0
    governor_trait: str = ""
    governor_turns: int = 0
    governor_level: int = 1
    governor_loyalty: float = 1.0

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
    capital_upgrade: int = 0
    personality: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        faction = FACTIONS.get(self.name)
        if faction:
            for key, value in faction.modifiers.items():
                self.bonus_modifiers.setdefault(key, 0.0)
                if self.bonus_modifiers[key] == 0.0:
                    self.bonus_modifiers[key] = value
        if not self.personality:
            rng = random.Random(hash(self.name) & 0xFFFF)
            self.personality = {
                "aggression": 0.4 + rng.random() * 0.5,
                "diplomacy": 0.3 + rng.random() * 0.5,
                "naval": 0.2 + rng.random() * 0.6,
                "memory": 0.5 + rng.random() * 0.4,
            }

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
    battle_journal: List[Dict[str, str]] = field(default_factory=list)
    seasonal_event: Optional[dict] = None
    diplomacy_missions: Dict[str, Dict[str, dict]] = field(default_factory=dict)
    ai_memory: Dict[str, Dict[str, float]] = field(default_factory=dict)
    trade_threats: Dict[str, Dict[str, str]] = field(default_factory=dict)

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
            trait = rng.choice(list(GOVERNOR_TRAITS.keys()))
            duration = rng.randint(3, 6)
            regions[key] = RegionState(
                key=key,
                owner=owner,
                population=population,
                economy=economy,
                stability=stability,
                garrison=garrison,
                discovered=(owner == "Britain"),
                governor_trait=trait,
                governor_turns=duration,
                governor_level=1,
                governor_loyalty=1.0,
            )
            faction_def = FACTIONS.get(owner)
            if faction_def and faction_def.capital == key:
                regions[key].buildings["market"] = 1
                regions[key].economy += 2
                regions[key].buildings.setdefault("capital", 0)
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
        state = cls(
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
            battle_journal=[],
        )
        state.roll_seasonal_event(announce=False)
        state._initialise_diplomacy_memory()
        state.evaluate_maritime_threats()
        return state

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
                capital_upgrade=fac.get("capital_upgrade", 0),
            )
            for name, fac in data["factions"].items()
        }
        for name, fac in factions.items():
            for other in factions:
                if other == name:
                    continue
                fac.diplomacy.relations.setdefault(other, "neutral")
                fac.diplomacy.trade.setdefault(other, False)
        regions: Dict[str, RegionState] = {}
        for key, reg in data["regions"].items():
            project_data = reg.get("project")
            project = None
            if project_data:
                project = ConstructionProject(
                    building=project_data.get("building", "market"),
                    turns_left=project_data.get("turns_left", 0),
                )
            regions[key] = RegionState(
                key=key,
                owner=reg["owner"],
                population=reg["population"],
                economy=reg["economy"],
                stability=reg.get("stability", 1.0),
                garrison=list(reg.get("garrison", [])),
                discovered=reg.get("discovered", False),
                recruit_queue=list(reg.get("recruit_queue", [])),
                buildings=dict(reg.get("buildings", {})),
                project=project,
                unsupplied_turns=reg.get("unsupplied_turns", 0),
                governor_trait=reg.get("governor_trait", "merchant"),
                governor_turns=reg.get("governor_turns", 3),
                governor_level=reg.get("governor_level", 1),
                governor_loyalty=reg.get("governor_loyalty", 1.0),
            )
        armies = [
            Army(
                faction=army["faction"],
                location=army["location"],
                units=list(army.get("units", [])),
                movement=army.get("movement", 1),
                experience=army.get("experience", 0),
                patrol_target=army.get("patrol_target"),
                patrol_turns=army.get("patrol_turns", 0),
            )
            for army in data.get("armies", [])
        ]
        for faction_name, faction_state in factions.items():
            faction_def = FACTIONS.get(faction_name)
            if not faction_def:
                continue
            capital_key = faction_def.capital
            region = regions.get(capital_key)
            if not region:
                continue
            level = region.buildings.get("capital", faction_state.capital_upgrade)
            region.buildings.setdefault("capital", level)
            faction_state.capital_upgrade = max(faction_state.capital_upgrade, level)
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
        state = cls(
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
            battle_journal=list(data.get("battle_journal", [])),
            seasonal_event=data.get("seasonal_event"),
            diplomacy_missions=dict(data.get("diplomacy_missions", {})),
            ai_memory=dict(data.get("ai_memory", {})),
            trade_threats=dict(data.get("trade_threats", {})),
        )
        state._initialise_diplomacy_memory()
        state.evaluate_maritime_threats()
        return state

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

    def advance_turn(self, player_faction: Optional[str] = None) -> None:
        previous_season = self.current_season()
        self.turn += 1
        self.season_index = (self.season_index + 1) % len(SEASONS)
        if self.season_index == 0:
            self.year += 1
        if previous_season != self.current_season():
            summary = self.weather_summary()
            if summary:
                self.add_event(f"Season shifts to {self.current_season()}: {summary}")
            self.roll_seasonal_event(player=player_faction)
        self.rotate_governors(announce_for=player_faction)
        self.tick_patrols()
        self._tick_governor_loyalty(player_faction)
        self.evaluate_maritime_threats()

    def rng(self) -> random.Random:
        return random.Random(self.rng_seed + self.turn)

    def current_season(self) -> str:
        return SEASONS[self.season_index % len(SEASONS)]

    def weather_profile(self) -> Dict[str, float]:
        return WEATHER_PROFILES.get(self.current_season(), WEATHER_PROFILES["Spring"])

    def weather_movement_modifier(self) -> float:
        base = self.weather_profile().get("movement", 1.0)
        return max(0.4, base * (1.0 + self.seasonal_event_modifier("movement", 0.0)))

    def weather_attack_modifier(self) -> float:
        base = self.weather_profile().get("attack", 1.0)
        return max(0.5, base * (1.0 + self.seasonal_event_modifier("attack", 0.0)))

    def weather_defense_modifier(self) -> float:
        base = self.weather_profile().get("defense", 1.0)
        return max(0.5, base * (1.0 + self.seasonal_event_modifier("defense", 0.0)))

    def weather_summary(self) -> str:
        return WEATHER_DESCRIPTIONS.get(self.current_season(), "")

    def seasonal_event_text(self) -> str:
        if not self.seasonal_event:
            return ""
        return f"{self.seasonal_event.get('name', 'Seasonal Event')}: {self.seasonal_event.get('description', '')}"

    def seasonal_event_modifier(self, key: str, default: float = 0.0) -> float:
        if not self.seasonal_event:
            return default
        return float(self.seasonal_event.get(key, default))

    def roll_seasonal_event(self, announce: bool = True, player: Optional[str] = None) -> None:
        season = self.current_season()
        pool = SEASONAL_EVENTS.get(season, [])
        if not pool:
            self.seasonal_event = None
            return
        rng = self.rng()
        self.seasonal_event = dict(rng.choice(pool))
        if announce:
            summary = self.seasonal_event_text()
            if summary:
                self.add_event(summary)
        if player and announce and self.seasonal_event:
            hint = self.seasonal_event.get("description")
            if hint:
                self.add_event(f"Impact: {hint}")

    def _initialise_diplomacy_memory(self) -> None:
        for faction in self.factions:
            memory = self.ai_memory.setdefault(faction, {})
            missions = self.diplomacy_missions.setdefault(faction, {})
            for other in self.factions:
                if other == faction:
                    continue
                memory.setdefault(other, 0.0)
                if not missions.get(other):
                    missions[other] = self._generate_diplomatic_mission(faction, other)

    def _generate_diplomatic_mission(self, faction: str, other: str) -> dict:
        rng = self.rng()
        mission_type = rng.choice(["gift", "mission", "escort"])
        if mission_type == "gift":
            amount = 60 + rng.randint(0, 80)
            return {
                "type": "gift",
                "value": amount,
                "description": f"Offer {other} a {amount} gold gift to soften relations.",
                "progress": 0,
                "completed": False,
            }
        if mission_type == "escort":
            return {
                "type": "escort",
                "value": 2,
                "description": "Maintain two active naval patrols to reassure trade partners.",
                "progress": 0,
                "completed": False,
            }
        target = rng.choice(list(self.regions.keys())) if self.regions else "region"
        return {
            "type": "mission",
            "value": target,
            "description": f"Capture {REGIONS.get(target, RegionDef(target, target, (0, 0), [], '', 0)).name} to impress {other}.",
            "progress": 0,
            "completed": False,
        }

    def register_diplomacy_memory(self, actor: str, other: str, delta: float) -> None:
        memory = self.ai_memory.setdefault(actor, {})
        memory[other] = memory.get(other, 0.0) + delta
        clamp = max(-2.0, min(2.0, memory[other]))
        memory[other] = clamp

    def offer_sweetener(self, faction: str, other: str, amount: int) -> bool:
        if amount <= 0:
            return False
        fac = self.factions.get(faction)
        rival = self.factions.get(other)
        if not fac or not rival:
            return False
        if fac.treasury < amount:
            return False
        fac.treasury -= amount
        rival.treasury += amount // 2
        self.register_diplomacy_memory(other, faction, min(0.5, amount / 200))
        mission = self.diplomacy_missions.get(faction, {}).get(other)
        if mission and mission.get("type") == "gift" and not mission.get("completed"):
            mission["progress"] += amount
            if mission["progress"] >= mission.get("value", 0):
                mission["completed"] = True
                self.register_diplomacy_memory(faction, other, 0.25)
        self.add_event(f"{faction} presents {other} a gift of {amount} gold")
        return True

    def evaluate_maritime_threats(self) -> None:
        previous = {fac: dict(threats) for fac, threats in self.trade_threats.items()}
        self.trade_threats = {fac: {} for fac in self.factions}
        for faction, fac_state in self.factions.items():
            origin = self.faction_capital(faction)
            if not origin:
                continue
            origin_neighbors = REGIONS[origin].neighbors if origin in REGIONS else []
            naval_enemies = [army for army in self.armies if army.has_naval() and army.faction != faction]
            threat_level = 0
            threat_reason = ""
            for army in naval_enemies:
                if army.location == origin:
                    threat_level = 2
                    threat_reason = f"{army.faction} fleet blockades the capital"
                    break
                if army.location in origin_neighbors and is_sea_lane(army.location, origin):
                    threat_level = max(threat_level, 1)
                    threat_reason = f"{army.faction} raiders prowl the sea-lanes"
            partners = [partner for partner, active in fac_state.diplomacy.trade.items() if active]
            for partner in partners:
                previous_level = previous.get(faction, {}).get(partner, {}).get("level", 0)
                if threat_level:
                    self.trade_threats[faction][partner] = {
                        "level": threat_level,
                        "reason": threat_reason,
                    }
                    if previous_level < threat_level:
                        self.add_event(
                            f"{faction} trade with {partner} threatened: {threat_reason}"
                        )
                else:
                    self.trade_threats[faction][partner] = {
                        "level": 0,
                        "reason": "Sea lanes clear",
                    }
                    if previous_level > 0:
                        self.add_event(f"{faction} trade routes to {partner} secured")

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

    def assign_governor_trait(
        self,
        region: RegionState,
        trait: Optional[str] = None,
        *,
        announce_for: Optional[str] = None,
        duration: Optional[int] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        pool = list(GOVERNOR_TRAITS.keys()) or ["merchant"]
        rng = rng or self.rng()
        if not trait or trait not in GOVERNOR_TRAITS:
            trait = rng.choice(pool)
        if duration is None:
            duration = rng.randint(4, 6)
        region.governor_trait = trait
        region.governor_turns = duration
        if region.governor_level <= 0:
            region.governor_level = 1
        if announce_for and region.owner == announce_for:
            desc = GOVERNOR_TRAITS.get(trait, {}).get("description", trait.title())
            self.add_event(f"Governor in {REGIONS[region.key].name}: {desc}")

    def rotate_governors(self, announce_for: Optional[str] = None) -> None:
        rng = self.rng()
        for region in self.regions.values():
            if region.owner not in self.factions:
                continue
            region.governor_turns = max(0, region.governor_turns - 1)
            if region.governor_turns <= 0:
                self.assign_governor_trait(region, announce_for=announce_for, rng=rng)

    def _tick_governor_loyalty(self, announce_for: Optional[str]) -> None:
        rng = self.rng()
        for region in self.regions.values():
            if region.owner not in self.factions:
                continue
            supply = self.region_has_supply(region.owner, region.key)
            delta = 0.01
            if not supply:
                delta = -0.08
            elif region.stability < 0.6:
                delta = -0.03
            elif region.stability > 1.1:
                delta = 0.02
            event_mod = self.seasonal_event_modifier("stability", 0.0)
            delta += event_mod * 0.5
            region.governor_loyalty = max(0.0, min(1.5, region.governor_loyalty + delta))
            if region.governor_loyalty <= 0.2 and rng.random() < 0.25:
                region.stability = max(0.2, region.stability - 0.1)
                if announce_for and region.owner == announce_for:
                    self.add_event(
                        f"Governor unrest in {REGIONS[region.key].name} undermines control!"
                    )
                region.governor_loyalty = 0.4
            if region.governor_loyalty > 1.2 and region.governor_level < 5:
                region.governor_level += 1
                region.governor_loyalty = 0.9
                if announce_for and region.owner == announce_for:
                    self.add_event(
                        f"Governor of {REGIONS[region.key].name} gains renown (level {region.governor_level})"
                    )

    def governor_trait_bonus(self, region: Optional[RegionState], key: str, default: float = 0.0) -> float:
        if region is None:
            return default
        data = GOVERNOR_TRAITS.get(region.governor_trait)
        if not data:
            return default
        return float(data.get(key, default))

    def governor_trait_description(self, trait: str) -> str:
        return GOVERNOR_TRAITS.get(trait, {}).get("description", trait.title())

    def active_patrols(self, faction: str) -> List[Army]:
        return [army for army in self.armies if army.faction == faction and army.is_patrolling()]

    def count_patrols(self, faction: str) -> int:
        return len(self.active_patrols(faction))

    def naval_patrol_income_bonus(self, faction: str) -> int:
        fac_state = self.factions.get(faction)
        if not fac_state:
            return 0
        patrols = self.active_patrols(faction)
        if not patrols:
            return 0
        trade_routes = sum(1 for active in fac_state.diplomacy.trade.values() if active)
        naval_mod = 1.0 + self.seasonal_event_modifier("naval", 0.0)
        base = int(6 * len(patrols) * max(0.4, naval_mod))
        return base + trade_routes * 2

    def set_patrol(self, army: Army, enabled: bool) -> None:
        if enabled:
            if army.is_patrolling():
                return
            army.patrol_target = army.location
            army.patrol_turns = 0
            self.add_event(f"{army.faction} patrol established near {REGIONS[army.location].name}")
        else:
            if not army.is_patrolling():
                return
            if army.is_patrolling():
                self.add_event(f"{army.faction} patrol stood down near {REGIONS[army.location].name}")
            army.patrol_target = None
            army.patrol_turns = 0
        self.evaluate_maritime_threats()

    def tick_patrols(self) -> None:
        for army in self.armies:
            if army.is_patrolling():
                army.patrol_turns += 1

    def capture_region(self, region_key: str, new_owner: str, announce_for: Optional[str] = None) -> None:
        region = self.regions[region_key]
        if region.owner == new_owner:
            return
        previous_owner = region.owner
        region.owner = new_owner
        region.garrison = list(region.garrison)
        region.unsupplied_turns = 0
        region.governor_turns = 0
        self.assign_governor_trait(region, announce_for=announce_for)
        self.reveal_region(new_owner, region_key)
        faction_def = FACTIONS.get(new_owner)
        if faction_def and faction_def.capital == region_key:
            level = region.buildings.get("capital", 0)
            self.factions[new_owner].capital_upgrade = level
        prev_def = FACTIONS.get(previous_owner)
        if prev_def and prev_def.capital == region_key and previous_owner in self.factions:
            self.factions[previous_owner].capital_upgrade = 0
        if previous_owner != new_owner:
            self.add_event(f"{new_owner} seized {REGIONS[region_key].name}")
        mission = self.diplomacy_missions.get(new_owner, {})
        for rival, data in mission.items():
            if data.get("type") == "mission" and data.get("value") == region_key:
                data["completed"] = True
                data["progress"] = 1

    def perform_espionage(self, army: Army, target_region: str) -> str:
        if "spy" not in army.units:
            return "No spy unit available"
        if target_region not in REGIONS:
            return "Unknown target"
        origin = REGIONS[army.location]
        if target_region not in origin.neighbors:
            return "Target must be adjacent"
        target_state = self.regions[target_region]
        if target_state.owner == army.faction:
            return "Cannot spy on friendly region"
        rng = self.rng()
        base_chance = 0.55
        origin_state = self.regions.get(army.location)
        bonus = self.governor_trait_bonus(origin_state, "spy_bonus", 0.0) if origin_state else 0.0
        chance = min(0.95, base_chance + bonus)
        army.movement = 0
        success = rng.random() <= chance
        operation = "scout"
        options = ["scout", "sabotage", "unrest"]
        if not target_state.buildings:
            options.remove("sabotage") if "sabotage" in options else None
        if target_state.stability > 1.1:
            options.remove("unrest") if "unrest" in options else None
        if options:
            operation = rng.choice(options)
        if success:
            self.reveal_region(army.faction, target_region)
            if operation == "scout":
                target_state.stability = max(0.2, target_state.stability - 0.04)
                self.add_event(
                    f"Spy charts {REGIONS[target_region].name}; defenses catalogued."
                )
                loot = int(target_state.economy * 0.1)
                self.factions[army.faction].treasury += loot
                self.add_event(f"Spy lifts {loot} gold in courier satchels")
            elif operation == "sabotage":
                building_key = next(iter(target_state.buildings))
                target_state.buildings[building_key] = max(0, target_state.buildings[building_key] - 1)
                self.add_event(
                    f"Saboteurs cripple {REGIONS[target_region].name}'s {building_key}"
                )
                target_state.stability = max(0.2, target_state.stability - 0.08)
            elif operation == "unrest":
                target_state.stability = max(0.2, target_state.stability - 0.15)
                self.add_event(
                    f"Spy foments dissent in {REGIONS[target_region].name}; stability plunges"
                )
            if target_state.garrison and operation != "scout":
                lost = target_state.garrison.pop(0)
                self.add_event(
                    f"Garrison loses {UNITS[lost].name} amid the chaos"
                )
            mission = self.diplomacy_missions.get(army.faction, {}).get(target_state.owner)
            if mission and mission.get("type") == "mission" and mission.get("value") == target_region:
                mission["completed"] = True
                mission["progress"] = 1
                self.register_diplomacy_memory(army.faction, target_state.owner, -0.2)
            return "Espionage succeeded"
        detected = rng.random() < 0.6
        if detected:
            try:
                army.units.remove("spy")
                self.add_event("Spy captured and executed")
            except ValueError:
                pass
            self.register_diplomacy_memory(target_state.owner, army.faction, -0.3)
        else:
            self.add_event("Spy escapes but brings no intel")
            self.register_diplomacy_memory(target_state.owner, army.faction, -0.1)
        return "Espionage failed"

    def record_battle(
        self,
        *,
        location: str,
        attacker: str,
        defender: str,
        winner: str,
        battle_type: str,
        attacker_losses: int,
        defender_losses: int,
    ) -> None:
        entry = {
            "turn": str(self.turn),
            "season": self.current_season(),
            "year": str(self.year),
            "location": REGIONS.get(location, RegionDef(location, location, (0, 0), [], "", 0)).name,
            "attacker": attacker,
            "defender": defender,
            "winner": winner,
            "type": battle_type,
            "atk_losses": str(attacker_losses),
            "def_losses": str(defender_losses),
        }
        self.battle_journal.append(entry)
        if len(self.battle_journal) > 12:
            self.battle_journal = self.battle_journal[-12:]

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
        income_value = sum(self.region_income_value(reg) for reg in self.regions_owned_by(faction))
        income = int(income_value * fac_state.income_modifier())
        try:
            from systems.diplomacy import trade_income_bonus

            income += trade_income_bonus(self, faction)
        except Exception:
            pass
        patrol_bonus = self.naval_patrol_income_bonus(faction)
        if patrol_bonus:
            income += patrol_bonus
        mission = self.diplomacy_missions.get(faction, {})
        for rival, data in mission.items():
            if data.get("type") == "escort" and not data.get("completed"):
                if self.count_patrols(faction) >= data.get("value", 0):
                    data["completed"] = True
                    data["progress"] = data.get("value", 0)
                    self.register_diplomacy_memory(faction, rival, 0.2)
        upkeep = self.upkeep_cost(faction)
        fac_state.treasury += income - upkeep
        if patrol_bonus:
            self.add_event(f"{faction} patrols secured +{patrol_bonus} trade income")
        net = income - upkeep
        self.add_event(f"{faction} income {income} - upkeep {upkeep} = {net}")
        return net

    def region_income_value(self, region: RegionState) -> int:
        base = region.income()
        base += region.buildings.get("market", 0) * 6
        if region.project and region.project.building == "market":
            base += 2
        trait_bonus = self.governor_trait_bonus(region, "income", 0.0)
        if trait_bonus:
            base = int(base * (1.0 + trait_bonus))
        base = int(base * (1.0 + self.seasonal_event_modifier("income", 0.0)))
        capital_key = self.faction_capital(region.owner)
        faction_state = self.factions.get(region.owner)
        if capital_key and capital_key == region.key and faction_state:
            upgrade = faction_state.capital_upgrade
            if upgrade:
                base = int(base * (1.05 + 0.05 * upgrade))
        if not self.region_has_supply(region.owner, region.key):
            penalty = 0.5 + self.seasonal_event_modifier("supply", 0.0)
            base = int(base * max(0.2, penalty))
        return base

    def region_has_supply(self, faction: str, region_key: str) -> bool:
        if faction not in self.factions:
            return True
        capital = self.faction_capital(faction)
        if not capital:
            return True
        if region_key == capital:
            return True
        owned_regions = self.regions_owned_by(faction)
        owned = {reg.key for reg in owned_regions}
        naval_resources = {"naval", "harbor", "trade", "corsairs"}
        naval_regions = {reg.key for reg in owned_regions if REGIONS[reg.key].resource in naval_resources}
        has_naval_supply = bool(
            naval_regions and any(army.faction == faction and army.has_naval() for army in self.armies)
        )
        if region_key not in owned:
            for neighbor in REGIONS[region_key].neighbors:
                if neighbor not in owned:
                    continue
                if is_sea_lane(region_key, neighbor) and not has_naval_supply:
                    continue
                if self.region_has_supply(faction, neighbor):
                    return True
            if has_naval_supply and REGIONS[region_key].resource in naval_resources:
                return True
            return False
        if capital not in owned:
            return False
        queue: deque[str] = deque([capital])
        visited = {capital}
        while queue:
            current = queue.popleft()
            if current == region_key:
                return True
            for neighbor in REGIONS[current].neighbors:
                if neighbor in owned and neighbor not in visited and not is_sea_lane(current, neighbor):
                    visited.add(neighbor)
                    queue.append(neighbor)
        if region_key in visited:
            return True
        if has_naval_supply and (
            region_key in naval_regions or REGIONS[region_key].resource in naval_resources
        ):
            return True
        return False

    def available_buildings(self, region: RegionState) -> List[BuildingDef]:
        options: List[BuildingDef] = []
        for key in ORDERED_BUILDINGS:
            building = BUILDINGS[key]
            if building.key == "capital":
                faction_def = FACTIONS.get(region.owner)
                if not faction_def or faction_def.capital != region.key:
                    continue
                faction_state = self.factions.get(region.owner)
                current_level = 0
                if faction_state:
                    current_level = max(
                        faction_state.capital_upgrade,
                        region.buildings.get(building.key, 0),
                    )
                if faction_state and current_level >= building.max_level:
                    continue
                if current_level < building.max_level:
                    options.append(building)
                continue
            if region.buildings.get(key, 0) < building.max_level:
                options.append(building)
        return options

    def start_construction(self, region: RegionState, building: BuildingDef) -> bool:
        if region.project:
            return False
        current_level = region.buildings.get(building.key, 0)
        if building.key == "capital":
            faction_state = self.factions.get(region.owner)
            if not faction_state:
                return False
            current_level = max(current_level, faction_state.capital_upgrade)
            if current_level >= building.max_level:
                return False
        else:
            if current_level >= building.max_level:
                return False
        if not self.region_has_supply(region.owner, region.key):
            return False
        faction = self.factions.get(region.owner)
        if not faction:
            return False
        if faction.treasury < building.cost:
            return False
        faction.treasury -= building.cost
        region.project = ConstructionProject(building=building.key, turns_left=building.build_time)
        self.add_event(
            f"{region.owner} began {building.name} in {REGIONS[region.key].name}"
        )
        return True

    def process_construction(self) -> None:
        for region in self.regions.values():
            if not region.project:
                continue
            if not self.region_has_supply(region.owner, region.key):
                if region.unsupplied_turns == 1:
                    self.add_event(
                        f"Construction stalled in {REGIONS[region.key].name} (cut off)"
                    )
                continue
            region.project.turns_left -= 1
            if region.project.turns_left <= 0:
                building = BUILDINGS.get(region.project.building)
                if building:
                    region.buildings[building.key] = region.buildings.get(building.key, 0) + 1
                    self.apply_building_effect(region, building)
                    self.add_event(
                        f"{region.owner} completed {building.name} in {REGIONS[region.key].name}"
                    )
                region.project = None

    def apply_building_effect(self, region: RegionState, building: BuildingDef) -> None:
        if building.key == "market":
            region.economy += 2
        elif building.key == "fort":
            region.stability = min(1.3, region.stability + 0.03)
        elif building.key == "culture":
            region.stability = min(1.4, region.stability + 0.08)
        elif building.key == "capital":
            faction = self.factions.get(region.owner)
            if faction:
                level = region.buildings.get("capital", 0)
                faction.capital_upgrade = max(faction.capital_upgrade, level)
                region.stability = min(1.4, region.stability + 0.05 * max(1, level))

    def region_defense_bonus(self, region_key: str) -> int:
        region = self.regions.get(region_key)
        if not region:
            return 0
        return region.buildings.get("fort", 0) * 4

    def apply_supply_attrition(self) -> None:
        for region in self.regions.values():
            if region.owner not in self.factions:
                continue
            supplied = self.region_has_supply(region.owner, region.key)
            if supplied:
                if region.unsupplied_turns > 0:
                    self.add_event(f"Supply restored to {REGIONS[region.key].name}")
                region.unsupplied_turns = 0
                culture_level = region.buildings.get("culture", 0)
                if culture_level and region.stability < 1.35:
                    region.stability = min(1.35, region.stability + 0.02 * culture_level)
                trait_boost = self.governor_trait_bonus(region, "stability", 0.0)
                if trait_boost:
                    region.stability = min(1.4, region.stability + trait_boost)
                continue
            region.unsupplied_turns += 1
            penalty = 0.05 + 0.02 * max(0, region.unsupplied_turns - 1)
            penalty = max(0.02, penalty - 0.01 * region.buildings.get("fort", 0))
            cap_upgrade = 0
            faction_state = self.factions.get(region.owner)
            if faction_state:
                cap_upgrade = faction_state.capital_upgrade
            if cap_upgrade:
                penalty = max(0.015, penalty - 0.01 * cap_upgrade)
            trait_relief = self.governor_trait_bonus(region, "stability", 0.0)
            if trait_relief:
                penalty = max(0.01, penalty - trait_relief / 2)
            penalty += -self.seasonal_event_modifier("supply", 0.0)
            region.stability = max(0.2, region.stability - penalty)
            if region.unsupplied_turns % 2 == 0 and region.garrison:
                lost = region.garrison.pop(0)
                self.add_event(
                    f"Garrison in {REGIONS[region.key].name} lost {UNITS[lost].name} to attrition"
                )
        for army in list(self.armies):
            if army.faction not in self.factions:
                continue
            if self.region_has_supply(army.faction, army.location):
                continue
            if army.units:
                lost = army.units.pop()
                self.add_event(
                    f"{army.faction} army in {REGIONS[army.location].name} lost {UNITS[lost].name} to attrition"
                )
                if not army.units:
                    try:
                        self.armies.remove(army)
                    except ValueError:
                        pass
                    continue
            army.experience = max(0, army.experience - 1)

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
            if (
                region.buildings.get("culture", 0)
                or self.governor_trait_bonus(region, "spy_bonus", 0.0)
                or (
                    self.faction_capital(owner) == region.key
                    and fac.capital_upgrade >= 1
                )
            ) and "spy" not in options:
                options.append("spy")
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
        if unit_key == "spy":
            base = max(20, base - 12)
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
            if not region.recruit_queue:
                continue
            if not self.region_has_supply(region.owner, region.key):
                if region.unsupplied_turns == 1:
                    self.add_event(
                        f"Recruitment stalled in {REGIONS[region.key].name} (cut off)"
                    )
                continue
            slots = 1
            extra = int(self.governor_trait_bonus(region, "extra_recruit", 0))
            if extra > 0:
                slots += extra
            faction_state = self.factions.get(region.owner)
            if (
                faction_state
                and self.faction_capital(region.owner) == region.key
                and faction_state.capital_upgrade >= 2
            ):
                slots += 1
            for _ in range(slots):
                if not region.recruit_queue:
                    break
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

