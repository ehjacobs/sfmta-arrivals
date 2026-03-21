import time
from datetime import datetime, timezone

import requests

from src.config import AppConfig
from src.models import Arrival, DisplayData, RouteArrivals


class RateLimiter:
    def __init__(self, max_calls: int = 60, window_seconds: int = 3600):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.call_times: list[float] = []

    def can_call(self) -> bool:
        self._prune()
        return len(self.call_times) < self.max_calls - 5  # 5-call safety margin

    def record_call(self):
        self.call_times.append(time.time())

    def _prune(self):
        cutoff = time.time() - self.window_seconds
        self.call_times = [t for t in self.call_times if t > cutoff]


_rate_limiter = RateLimiter()


def fetch_all_arrivals(api_key: str, agency: str) -> dict:
    """Fetch all stop monitoring data for the agency in a single API call."""
    if not _rate_limiter.can_call():
        raise RuntimeError("Rate limit approaching — skipping API call")

    url = "http://api.511.org/transit/StopMonitoring"
    params = {
        "api_key": api_key,
        "agency": agency,
        "format": "json",
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    _rate_limiter.record_call()

    # 511.org sometimes returns a BOM at the start of the response
    text = resp.text.lstrip("\ufeff")
    import json
    return json.loads(text)


def parse_arrivals(raw_json: dict, config: AppConfig, now: datetime | None = None) -> DisplayData:
    """Parse SIRI JSON into DisplayData, filtering to configured stops/routes."""
    if now is None:
        now = datetime.now(timezone.utc)

    errors = []
    route_arrivals_list = []

    # Build lookup of configured stops and routes
    stop_routes: dict[str, list] = {}
    stop_info: dict[str, tuple] = {}
    for stop in config.stops:
        stop_routes[stop.stop_code] = stop.routes
        stop_info[stop.stop_code] = (stop.name, stop.walk_minutes)

    # Collect all arrivals grouped by (stop_code, line, direction_config)
    grouped: dict[tuple, list[Arrival]] = {}

    try:
        visits = (
            raw_json["ServiceDelivery"]["StopMonitoringDelivery"][0]["MonitoredStopVisit"]
        )
    except (KeyError, IndexError, TypeError) as e:
        errors.append(f"Invalid API response: {e}")
        return DisplayData(errors=errors, last_updated=now)

    for visit in visits:
        try:
            journey = visit["MonitoredVehicleJourney"]
            stop_ref = journey["MonitoredCall"]["StopPointRef"]
            line = journey["PublishedLineName"]
            destination = journey.get("DestinationName", "")

            if stop_ref not in stop_routes:
                continue

            for route_cfg in stop_routes[stop_ref]:
                if route_cfg.line != line:
                    continue
                if route_cfg.direction.lower() not in destination.lower():
                    continue

                expected_str = journey["MonitoredCall"].get("ExpectedArrivalTime")
                if not expected_str:
                    expected_str = journey["MonitoredCall"].get("AimedArrivalTime")
                if not expected_str:
                    continue

                expected = datetime.fromisoformat(expected_str)
                if expected.tzinfo is None:
                    expected = expected.replace(tzinfo=timezone.utc)

                minutes_away = max(0, int((expected - now).total_seconds() / 60))

                key = (stop_ref, route_cfg.line, route_cfg.direction)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(Arrival(
                    line=line,
                    destination=destination,
                    expected_time=expected,
                    minutes_away=minutes_away,
                ))
        except (KeyError, TypeError, ValueError):
            continue

    # Build RouteArrivals in config order
    for stop in config.stops:
        stop_name, walk_minutes = stop_info[stop.stop_code]
        for route_cfg in stop.routes:
            key = (stop.stop_code, route_cfg.line, route_cfg.direction)
            arrivals = grouped.get(key, [])
            arrivals.sort(key=lambda a: a.minutes_away)

            top4 = arrivals[:4]
            frequency = None
            if len(arrivals) >= 2:
                # Average gap across all consecutive arrivals for a smoother estimate
                gaps = [
                    arrivals[i + 1].minutes_away - arrivals[i].minutes_away
                    for i in range(len(arrivals) - 1)
                ]
                positive_gaps = [g for g in gaps if g > 0]
                if positive_gaps:
                    frequency = round(sum(positive_gaps) / len(positive_gaps))

            route_arrivals_list.append(RouteArrivals(
                line=route_cfg.line,
                direction=route_cfg.direction,
                stop_name=stop_name,
                walk_minutes=walk_minutes,
                arrivals=top4,
                frequency_minutes=frequency,
            ))

    return DisplayData(
        routes=route_arrivals_list,
        last_updated=now,
        errors=errors,
    )
