import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from src.api import fetch_all_arrivals, parse_arrivals
from src.config import load_config
from src.display import create_display
from src.models import DisplayData, RouteArrivals, Arrival
from src.renderer import render, render_sleep

SF_TZ = ZoneInfo("America/Los_Angeles")


def make_test_data() -> DisplayData:
    """Generate test data for verifying the renderer."""
    now = datetime.now(timezone.utc)
    return DisplayData(
        routes=[
            RouteArrivals(
                line="J", direction="Inbound", stop_name="Church & Duboce",
                walk_minutes=4,
                arrivals=[
                    Arrival(line="J", destination="Inbound", expected_time=now, minutes_away=3),
                    Arrival(line="J", destination="Inbound", expected_time=now, minutes_away=8),
                    Arrival(line="J", destination="Inbound", expected_time=now, minutes_away=14),
                ],
                frequency_minutes=5,
            ),
            RouteArrivals(
                line="N", direction="Outbound", stop_name="Church & Duboce",
                walk_minutes=4,
                arrivals=[
                    Arrival(line="N", destination="Outbound", expected_time=now, minutes_away=7),
                    Arrival(line="N", destination="Outbound", expected_time=now, minutes_away=12),
                    Arrival(line="N", destination="Outbound", expected_time=now, minutes_away=18),
                ],
                frequency_minutes=5,
            ),
            RouteArrivals(
                line="7", direction="Downtown", stop_name="Haight & Fillmore",
                walk_minutes=7,
                arrivals=[
                    Arrival(line="7", destination="Downtown", expected_time=now, minutes_away=2),
                    Arrival(line="7", destination="Downtown", expected_time=now, minutes_away=14),
                    Arrival(line="7", destination="Downtown", expected_time=now, minutes_away=25),
                ],
                frequency_minutes=12,
            ),
            RouteArrivals(
                line="22", direction="Marina", stop_name="Haight & Fillmore",
                walk_minutes=7,
                arrivals=[
                    Arrival(line="22", destination="Marina", expected_time=now, minutes_away=11),
                    Arrival(line="22", destination="Marina", expected_time=now, minutes_away=22),
                    Arrival(line="22", destination="Marina", expected_time=now, minutes_away=33),
                ],
                frequency_minutes=11,
            ),
            RouteArrivals(
                line="F", direction="Wharf", stop_name="Market & Van Ness",
                walk_minutes=10,
                arrivals=[
                    Arrival(line="F", destination="Wharf", expected_time=now, minutes_away=1),
                    Arrival(line="F", destination="Wharf", expected_time=now, minutes_away=9),
                    Arrival(line="F", destination="Wharf", expected_time=now, minutes_away=17),
                ],
                frequency_minutes=8,
            ),
            RouteArrivals(
                line="33", direction="Downtown", stop_name="Castro & 18th",
                walk_minutes=3,
                arrivals=[],
                frequency_minutes=None,
            ),
        ],
        last_updated=now,
        errors=[],
    )


def is_sleep_time(sleep_config) -> bool:
    """Check if current local time falls within the sleep window."""
    if sleep_config.sleep_time is None:
        return False
    now = datetime.now(SF_TZ).time()
    sleep_t = sleep_config.sleep_time
    wake_t = sleep_config.wake_time
    if sleep_t > wake_t:
        # Overnight: e.g. 21:00 -> 06:00
        return now >= sleep_t or now < wake_t
    else:
        # Same-day: e.g. 01:00 -> 05:00
        return sleep_t <= now < wake_t


def seconds_until_wake(sleep_config) -> float:
    """Return seconds from now until wake_time."""
    now = datetime.now(SF_TZ)
    wake = now.replace(
        hour=sleep_config.wake_time.hour,
        minute=sleep_config.wake_time.minute,
        second=0, microsecond=0,
    )
    if wake <= now:
        wake += timedelta(days=1)
    return (wake - now).total_seconds()


def fetch_and_render(config, display):
    """Fetch live data, render, and display."""
    now = datetime.now(timezone.utc)
    try:
        raw = fetch_all_arrivals(config.api_key, config.agency)
        data = parse_arrivals(raw, config, now)
    except Exception as e:
        print(f"API error: {e}")
        data = DisplayData(last_updated=now, errors=[str(e)])

    image = render(data, config.thresholds)
    display.show(image)
    return data


def main():
    parser = argparse.ArgumentParser(description="SF Muni Bus Arrival Display")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--test", action="store_true", help="Render test data (no API call)")
    args = parser.parse_args()

    config = load_config(args.config)
    display = create_display(config.display)

    if args.test:
        config.display.simulate = True
        config.display.output_path = "example.png"
        display = create_display(config.display)
        data = make_test_data()
        image = render(data, config.thresholds)
        display.show(image)
        return

    if args.once:
        fetch_and_render(config, display)
        return

    # Main loop
    interval = config.refresh_interval_minutes
    print(f"Starting SFMTA Arrivals (refresh every {interval} min, aligned to minute boundary)")
    sleeping = False
    while True:
        try:
            if is_sleep_time(config.sleep):
                if not sleeping:
                    print("Entering sleep mode")
                    image = render_sleep(config.sleep.wake_time)
                    display.show(image)
                    sleeping = True
                wait = seconds_until_wake(config.sleep)
                print(f"Sleeping for {wait / 3600:.1f} hours until wake time")
                time.sleep(wait)
                continue
            elif sleeping:
                print("Waking up")
                sleeping = False

            fetch_and_render(config, display)
        except KeyboardInterrupt:
            print("\nShutting down")
            sys.exit(0)
        except Exception as e:
            print(f"Error in main loop: {e}")

        try:
            # Sleep until the next minute boundary + 2s buffer
            now = time.time()
            seconds_into_minute = now % 60
            seconds_to_next_minute = 60 - seconds_into_minute + 2
            remaining_minutes = interval - 1
            sleep_seconds = seconds_to_next_minute + remaining_minutes * 60
            time.sleep(sleep_seconds)
        except KeyboardInterrupt:
            print("\nShutting down")
            sys.exit(0)


if __name__ == "__main__":
    main()
