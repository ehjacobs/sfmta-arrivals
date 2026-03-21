from src.config import ThresholdConfig

# RGB color constants (Inky 7-color palette)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (200, 0, 0)
GREEN = (0, 150, 0)
YELLOW = (200, 180, 0)
BLUE = (0, 0, 200)
ORANGE = (200, 100, 0)

# Sentinel for unreachable arrivals (drawn as black with strikethrough)
UNREACHABLE = None

# Row separator color
ROW_SEPARATOR = BLUE


def urgency_color(minutes_away: int, walk_minutes: int, thresholds: ThresholdConfig):
    """Return color based on buffer time (minutes_away - walk_minutes).

    Returns UNREACHABLE (None) for buses that can't be caught,
    GREEN for go-now, YELLOW for moderate wait, RED for long wait.
    """
    buffer = minutes_away - walk_minutes
    if buffer <= thresholds.rush_max:
        return UNREACHABLE
    elif buffer <= thresholds.ideal_max:
        return GREEN
    elif buffer <= thresholds.medium_max:
        return ORANGE
    else:
        return RED
