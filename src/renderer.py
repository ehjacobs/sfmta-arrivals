from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from src.colors import (
    BLACK, WHITE, RED, BLUE, UNREACHABLE, ROW_SEPARATOR, urgency_color,
)
from src.config import ThresholdConfig
from src.models import DisplayData, RouteArrivals

WIDTH = 800
HEIGHT = 480
HEADER_HEIGHT = 40
MAX_ROWS = 6
MAX_ARRIVALS = 3

# Grid column layout (x positions)
BADGE_WIDTH = 80
CONTENT_X = BADGE_WIDTH + 10
# 3 arrival columns evenly spaced in the available area
ARRIVALS_X0 = CONTENT_X       # first arrival aligns with content
ARRIVALS_WIDTH = 620           # total width for 3 arrival columns
COL_WIDTH = ARRIVALS_WIDTH // MAX_ARRIVALS  # ~207px per column
FREQ_X = WIDTH - 90           # frequency column on far right

FONTS_DIR = Path(__file__).parent.parent / "fonts"
SF_TZ = ZoneInfo("America/Los_Angeles")


def _load_fonts():
    return {
        "header": ImageFont.truetype(str(FONTS_DIR / "DejaVuSans-Bold.ttf"), 20),
        "header_small": ImageFont.truetype(str(FONTS_DIR / "DejaVuSans.ttf"), 16),
        "route_badge": ImageFont.truetype(str(FONTS_DIR / "DejaVuSans-Bold.ttf"), 30),
        "stop_info": ImageFont.truetype(str(FONTS_DIR / "DejaVuSans-Bold.ttf"), 16),
        "arrival_time": ImageFont.truetype(str(FONTS_DIR / "DejaVuSans-Bold.ttf"), 24),
        "arrival_clock": ImageFont.truetype(str(FONTS_DIR / "DejaVuSans-Bold.ttf"), 16),
        "frequency": ImageFont.truetype(str(FONTS_DIR / "DejaVuSans.ttf"), 18),
        "frequency_label": ImageFont.truetype(str(FONTS_DIR / "DejaVuSans.ttf"), 13),
    }


def render(data: DisplayData, thresholds: ThresholdConfig) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)
    fonts = _load_fonts()

    # Header
    draw.rectangle([(0, 0), (WIDTH, HEADER_HEIGHT)], fill=BLUE)
    draw.text((10, 8), "SF Muni Arrivals", fill=WHITE, font=fonts["header"])

    if data.last_updated:
        local_time = data.last_updated.astimezone(SF_TZ)
        time_str = f"Updated {local_time.strftime('%-I:%M %p')}"
        bbox = draw.textbbox((0, 0), time_str, font=fonts["header_small"])
        tw = bbox[2] - bbox[0]
        draw.text((WIDTH - tw - 10, 11), time_str, fill=WHITE, font=fonts["header_small"])

    # Error banner
    banner_y = HEADER_HEIGHT
    if data.errors:
        error_text = " | ".join(data.errors)
        draw.rectangle([(0, banner_y), (WIDTH, banner_y + 24)], fill=RED)
        draw.text((10, banner_y + 2), error_text, fill=WHITE, font=fonts["header_small"])
        banner_y += 24

    # Rows
    row_count = min(len(data.routes), MAX_ROWS)
    if row_count == 0:
        msg = "No routes configured" if not data.errors else "Waiting for data..."
        draw.text((WIDTH // 2 - 100, HEIGHT // 2), msg, fill=BLACK, font=fonts["stop_info"])
        return img

    available_height = HEIGHT - banner_y
    row_height = available_height // max(row_count, 1)

    for i, route in enumerate(data.routes[:MAX_ROWS]):
        y = banner_y + i * row_height

        # Separator line between rows
        if i > 0:
            draw.line([(0, y), (WIDTH, y)], fill=ROW_SEPARATOR, width=1)

        _draw_route_row(draw, fonts, route, thresholds, y, row_height)

    return img


def _draw_walking_figure(draw: ImageDraw.ImageDraw, x: int, y: int, height: int):
    """Draw a simple walking stick figure at (x, y) with given height."""
    color = (100, 100, 100)
    w = 2  # line width
    # Proportions relative to height
    head_r = height // 6
    head_cx = x + height // 3
    head_cy = y + head_r

    # Head
    draw.ellipse(
        [(head_cx - head_r, head_cy - head_r), (head_cx + head_r, head_cy + head_r)],
        fill=color,
    )

    # Body — slight forward lean
    body_top = head_cy + head_r + 1
    body_bottom = y + int(height * 0.6)
    body_bottom_x = head_cx + 1
    draw.line([(head_cx, body_top), (body_bottom_x, body_bottom)], fill=color, width=w)

    # Legs — mid-stride
    leg_bottom = y + height
    draw.line([(body_bottom_x, body_bottom), (body_bottom_x + height // 4, leg_bottom)], fill=color, width=w)
    draw.line([(body_bottom_x, body_bottom), (body_bottom_x - height // 5, leg_bottom)], fill=color, width=w)

    # Arms — swinging
    arm_y = body_top + (body_bottom - body_top) // 3
    draw.line([(body_bottom_x, arm_y), (body_bottom_x + height // 3, arm_y + height // 5)], fill=color, width=w)
    draw.line([(body_bottom_x, arm_y), (body_bottom_x - height // 4, arm_y + height // 4)], fill=color, width=w)


def _draw_route_row(
    draw: ImageDraw.ImageDraw,
    fonts: dict,
    route: RouteArrivals,
    thresholds: ThresholdConfig,
    y: int,
    row_height: int,
):
    # Route badge: rounded rectangle with margin
    badge_margin = 6
    badge_x0 = badge_margin
    badge_y0 = y + badge_margin
    badge_x1 = BADGE_WIDTH - badge_margin
    badge_y1 = y + row_height - badge_margin
    draw.rounded_rectangle(
        [(badge_x0, badge_y0), (badge_x1, badge_y1)],
        radius=8,
        fill=BLUE,
    )
    badge_text = route.line
    badge_bbox = draw.textbbox((0, 0), badge_text, font=fonts["route_badge"])
    badge_tw = badge_bbox[2] - badge_bbox[0]
    badge_th = badge_bbox[3] - badge_bbox[1]
    badge_text_x = badge_x0 + (badge_x1 - badge_x0 - badge_tw) // 2 - badge_bbox[0]
    badge_text_y = badge_y0 + (badge_y1 - badge_y0 - badge_th) // 2 - badge_bbox[1]
    draw.text((badge_text_x, badge_text_y), badge_text, fill=WHITE, font=fonts["route_badge"])

    # Top / bottom split
    top_line_y = y + 10
    bottom_line_y = y + row_height // 2 + 4

    # Top line: stop name + walk time with walking figure + direction
    walk_text = f"{route.stop_name} ({route.walk_minutes} min"
    draw.text((CONTENT_X, top_line_y), walk_text, fill=BLACK, font=fonts["stop_info"])
    walk_bbox = draw.textbbox((CONTENT_X, top_line_y), walk_text, font=fonts["stop_info"])
    walker_x = walk_bbox[2] + 3
    _draw_walking_figure(draw, walker_x, top_line_y + 2, 14)
    after_walker_x = walker_x + 12
    draw.text((after_walker_x, top_line_y), f") \u00b7 {route.direction}", fill=BLACK, font=fonts["stop_info"])

    # Bottom line: arrival times in fixed grid columns
    if not route.arrivals:
        draw.text((ARRIVALS_X0, bottom_line_y), "--", fill=BLACK, font=fonts["arrival_time"])
    else:
        for col_idx in range(MAX_ARRIVALS):
            col_x = ARRIVALS_X0 + col_idx * COL_WIDTH
            if col_idx < len(route.arrivals):
                arr = route.arrivals[col_idx]
                color = urgency_color(arr.minutes_away, route.walk_minutes, thresholds)
                mins_text = f"{arr.minutes_away} min"
                local_arr = arr.expected_time.astimezone(SF_TZ)
                clock_text = local_arr.strftime("%-I:%M %p")
                if color is UNREACHABLE:
                    draw.text((col_x, bottom_line_y), mins_text, fill=BLACK, font=fonts["arrival_time"])
                    bbox = draw.textbbox((col_x, bottom_line_y), mins_text, font=fonts["arrival_time"])
                    strike_y = (bbox[1] + bbox[3]) // 2
                    draw.line([(bbox[0], strike_y), (bbox[2], strike_y)], fill=BLACK, width=3)
                    draw.text((bbox[2] + 4, bottom_line_y + 6), clock_text, fill=BLUE, font=fonts["arrival_clock"])
                else:
                    draw.text((col_x, bottom_line_y), mins_text, fill=color, font=fonts["arrival_time"])
                    bbox = draw.textbbox((col_x, bottom_line_y), mins_text, font=fonts["arrival_time"])
                    draw.text((bbox[2] + 4, bottom_line_y + 6), clock_text, fill=BLUE, font=fonts["arrival_clock"])

    # Frequency on the far right: "Every" on top, "~X min" below
    if route.frequency_minutes is not None:
        label_text = "Every"
        label_bbox = draw.textbbox((0, 0), label_text, font=fonts["frequency_label"])
        label_w = label_bbox[2] - label_bbox[0]

        freq_text = f"~{route.frequency_minutes} min"
        freq_bbox = draw.textbbox((0, 0), freq_text, font=fonts["frequency"])
        freq_w = freq_bbox[2] - freq_bbox[0]

        # Right-align both
        right_edge = WIDTH - 10
        draw.text((right_edge - label_w, top_line_y + 2), label_text, fill=BLACK, font=fonts["frequency_label"])
        draw.text((right_edge - freq_w, bottom_line_y + 2), freq_text, fill=BLACK, font=fonts["frequency"])
