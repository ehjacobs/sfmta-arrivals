from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Arrival:
    line: str
    destination: str
    expected_time: datetime
    minutes_away: int


@dataclass
class RouteArrivals:
    line: str
    direction: str
    stop_name: str
    walk_minutes: int
    arrivals: list[Arrival] = field(default_factory=list)  # max 4
    frequency_minutes: int | None = None


@dataclass
class DisplayData:
    routes: list[RouteArrivals] = field(default_factory=list)
    last_updated: datetime | None = None
    errors: list[str] = field(default_factory=list)
