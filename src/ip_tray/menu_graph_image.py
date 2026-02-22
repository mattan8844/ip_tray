from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw


def _downsample(values: Sequence[float], width: int) -> list[float]:
    if width <= 0:
        return []
    if not values:
        return [0.0] * width
    if len(values) <= width:
        padded = [0.0] * (width - len(values))
        return padded + [float(v) for v in values]

    src_len = len(values)
    out: list[float] = []
    for i in range(width):
        start = int(i * src_len / width)
        end = int((i + 1) * src_len / width)
        if end <= start:
            end = start + 1
        chunk = values[start:end]
        out.append(sum(float(v) for v in chunk) / len(chunk))
    return out


def _line_points(values: Sequence[float], width: int, height: int, max_v: float) -> list[tuple[float, float]]:
    if width <= 1:
        return []
    max_v = max(max_v, 1e-6)
    pts: list[tuple[float, float]] = []
    for i, v in enumerate(values):
        x = i
        y = (height - 1) - ((max(0.0, float(v)) / max_v) * (height - 1))
        pts.append((x, y))
    return pts


def _fill_under_curve(
    draw: ImageDraw.ImageDraw,
    points: Sequence[tuple[float, float]],
    width: int,
    height: int,
    color: tuple[int, int, int, int],
) -> None:
    if len(points) < 2:
        return
    polygon = [(0, height - 1)] + list(points) + [(width - 1, height - 1)]
    draw.polygon(polygon, fill=color)


def render_single_history_graph(
    samples: Sequence[float],
    path: Path,
    line_color: tuple[int, int, int, int],
    fill_color: tuple[int, int, int, int],
    width: int = 180,
    height: int = 32,
) -> Path:
    """Render one colored history chart with system-panel-like style."""
    scale = 2
    sw, sh = width * scale, height * scale
    image = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((0, 0, sw - 1, sh - 1), radius=8, fill=(245, 247, 250, 160))

    for y in (int(sh * 0.33), int(sh * 0.66)):
        draw.line((0, y, sw - 1, y), fill=(180, 188, 198, 110), width=1)

    data = _downsample(samples, sw)
    max_v = max(max(data) if data else 0.0, 1.0)
    pts = _line_points(data, sw, sh, max_v)

    _fill_under_curve(draw, pts, sw, sh, fill_color)
    if len(pts) >= 2:
        draw.line(pts, fill=line_color, width=3)

    draw.rounded_rectangle((0, 0, sw - 1, sh - 1), radius=8, outline=(126, 136, 148, 150), width=1)
    image = image.resize((width, height), Image.Resampling.LANCZOS)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return path
