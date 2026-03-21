# SFMTA Arrivals

Real-time SF Muni arrival display. Runs as a PNG generator on any machine, or on a Raspberry Pi with a Pimoroni Inky Impression 7.3" e-ink display.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml  # then edit with your API key
make test    # render test data to output.png (no API key needed)
make dev     # fetch live data and render to output.png
```

## Architecture

- `src/config.py` — YAML config loading, dataclasses, validation (max 6 routes)
- `src/models.py` — Arrival, RouteArrivals, DisplayData dataclasses
- `src/api.py` — 511.org StopMonitoring API client; single call per refresh, filters locally; rate limiter (55/hr cap)
- `src/colors.py` — RGB constants, `urgency_color()` returns color or UNREACHABLE sentinel
- `src/renderer.py` — PIL-based 800x480 image rendering; DejaVu fonts from `fonts/`
- `src/display.py` — SimulatorDisplay (PNG) for dev, InkyDisplay for Pi hardware
- `src/main.py` — Entry point with `--config`, `--once`, `--test` flags
- `src/lookup.py` — CLI utility to discover route destinations and stop info from the API

## Key Conventions

- Display is 800x480, 7-color e-ink palette
- Color coding: strikethrough black = unreachable, green = go now, yellow = comfortable wait, red = long wait
- Frequency is averaged across all available arrival gaps (not just first two)
- Times shown in America/Los_Angeles timezone
- API response may have BOM prefix — stripped before JSON parsing
- `StopMonitoringDelivery` may be a dict or list — code handles both
- Route matching uses `LineRef` (e.g., "14R", "J"), not `PublishedLineName` (e.g., "MISSION")
- Direction matching uses substring match on `DestinationName` (e.g., "Steuart" matches "Steuart St & Mission St")
- Use `python -m src.lookup --route <route>` to discover valid destination strings
- `config.yaml` contains API secrets — never commit (it's in .gitignore)

## Deploy to Pi

```bash
make deploy  # rsync + restart systemd service
```
