"""Lookup utility: find stop codes, routes, and destination names from the 511.org API."""

import argparse
import json
import sys
from collections import defaultdict

import requests


def fetch_stops(api_key: str, agency: str) -> dict:
    url = "http://api.511.org/transit/StopMonitoring"
    params = {"api_key": api_key, "agency": agency, "format": "json"}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    text = resp.text.lstrip("\ufeff")
    return json.loads(text)


def lookup_route(raw: dict, route: str):
    """Show all destinations and stops for a given route."""
    smd = raw["ServiceDelivery"]["StopMonitoringDelivery"]
    if isinstance(smd, list):
        smd = smd[0]
    visits = smd["MonitoredStopVisit"]

    # Group by destination -> set of stops
    by_dest: dict[str, set] = defaultdict(set)
    for visit in visits:
        j = visit["MonitoredVehicleJourney"]
        line = j.get("LineRef", "")
        if line.lower() != route.lower():
            continue
        dest = j.get("DestinationName", "Unknown")
        stop_ref = j["MonitoredCall"]["StopPointRef"]
        monitoring_ref = visit.get("MonitoringRef", stop_ref)
        by_dest[dest].add(monitoring_ref)

    if not by_dest:
        print(f"No active vehicles found for route '{route}'.")
        print("Note: only currently running routes appear in the data.")
        return

    print(f"\nRoute {route} — active destinations:\n")
    for dest, stops in sorted(by_dest.items()):
        print(f"  \"{dest}\"")
        print(f"    Serving {len(stops)} stops: {', '.join(sorted(stops)[:8])}", end="")
        if len(stops) > 8:
            print(f" ... and {len(stops) - 8} more", end="")
        print()
    print(f"\nUse these destination strings (or substrings) as the 'direction' in config.yaml.")


def lookup_stop(raw: dict, stop_code: str):
    """Show all routes and destinations serving a given stop."""
    smd = raw["ServiceDelivery"]["StopMonitoringDelivery"]
    if isinstance(smd, list):
        smd = smd[0]
    visits = smd["MonitoredStopVisit"]

    by_line: dict[str, set] = defaultdict(set)
    for visit in visits:
        j = visit["MonitoredVehicleJourney"]
        stop_ref = j["MonitoredCall"]["StopPointRef"]
        if stop_ref != stop_code:
            continue
        line = j.get("LineRef", "?")
        dest = j.get("DestinationName", "Unknown")
        by_line[line].add(dest)

    if not by_line:
        print(f"No active vehicles found for stop '{stop_code}'.")
        return

    print(f"\nStop {stop_code} — active routes:\n")
    for line, dests in sorted(by_line.items()):
        for dest in sorted(dests):
            print(f"  Line {line:>4s}  →  \"{dest}\"")
    print(f"\nUse the line and a destination substring as 'line' and 'direction' in config.yaml.")


def main():
    parser = argparse.ArgumentParser(
        description="Look up route destinations and stop info from 511.org API",
        epilog="Examples:\n"
               "  python -m src.lookup --route 14R\n"
               "  python -m src.lookup --stop 15557\n"
               "  python -m src.lookup --routes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", default="config.yaml", help="Config file (for API key)")
    parser.add_argument("--route", help="Show destinations for a route (e.g., 14R, J, 49)")
    parser.add_argument("--stop", help="Show routes serving a stop code (e.g., 15557)")
    parser.add_argument("--routes", action="store_true", help="List all active routes")
    args = parser.parse_args()

    from src.config import load_config
    config = load_config(args.config)

    print("Fetching data from 511.org...")
    raw = fetch_stops(config.api_key, config.agency)

    if args.route:
        lookup_route(raw, args.route)
    elif args.stop:
        lookup_stop(raw, args.stop)
    elif args.routes:
        smd = raw["ServiceDelivery"]["StopMonitoringDelivery"]
        if isinstance(smd, list):
            smd = smd[0]
        visits = smd["MonitoredStopVisit"]
        routes = sorted(set(
            v["MonitoredVehicleJourney"].get("LineRef", "")
            for v in visits
        ))
        print(f"\nActive routes: {', '.join(routes)}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
