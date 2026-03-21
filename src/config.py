from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class RouteConfig:
    line: str
    direction: str        # substring match against API's DestinationName
    display_name: str = ""  # shown on display; defaults to direction if empty


@dataclass
class StopConfig:
    stop_code: str
    name: str
    walk_minutes: int
    routes: list[RouteConfig]


@dataclass
class ThresholdConfig:
    rush_max: int = 0
    ideal_max: int = 5
    medium_max: int = 10


@dataclass
class DisplayConfig:
    simulate: bool = False
    output_path: str = "output.png"
    saturation: float = 0.5
    rotation: int = 0


@dataclass
class AppConfig:
    api_key: str
    agency: str
    refresh_interval_minutes: int
    stops: list[StopConfig]
    thresholds: ThresholdConfig
    display: DisplayConfig


def load_config(path: str) -> AppConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)

    if not raw.get("api_key"):
        raise ValueError("api_key is required in config")

    stops = []
    total_routes = 0
    for s in raw.get("stops", []):
        routes = [RouteConfig(**r) for r in s.get("routes", [])]
        total_routes += len(routes)
        stops.append(StopConfig(
            stop_code=str(s["stop_code"]),
            name=s["name"],
            walk_minutes=s.get("walk_minutes", 0),
            routes=routes,
        ))

    if total_routes > 6:
        raise ValueError(f"Total routes ({total_routes}) exceeds maximum of 6")
    if total_routes == 0:
        raise ValueError("At least one route must be configured")

    thresh_raw = raw.get("thresholds", {})
    thresholds = ThresholdConfig(
        rush_max=thresh_raw.get("rush_max", 0),
        ideal_max=thresh_raw.get("ideal_max", 5),
        medium_max=thresh_raw.get("medium_max", 10),
    )
    if not (thresholds.rush_max <= thresholds.ideal_max <= thresholds.medium_max):
        raise ValueError("Thresholds must be in ascending order: rush_max <= ideal_max <= medium_max")

    disp_raw = raw.get("display", {})
    display = DisplayConfig(
        simulate=disp_raw.get("simulate", False),
        output_path=disp_raw.get("output_path", "output.png"),
        saturation=disp_raw.get("saturation", 0.5),
        rotation=disp_raw.get("rotation", 0),
    )

    return AppConfig(
        api_key=raw["api_key"],
        agency=raw.get("agency", "SF"),
        refresh_interval_minutes=raw.get("refresh_interval_minutes",
                                        raw.get("refresh_interval_seconds", 120) // 60 or 2),
        stops=stops,
        thresholds=thresholds,
        display=display,
    )
