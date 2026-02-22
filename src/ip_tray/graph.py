from typing import Sequence

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _downsample(values: Sequence[float], target_width: int) -> list[float]:
    if target_width <= 0:
        return []
    if not values:
        return []
    if len(values) <= target_width:
        return [float(v) for v in values]

    src_len = len(values)
    reduced: list[float] = []
    for i in range(target_width):
        start = int(i * src_len / target_width)
        end = int((i + 1) * src_len / target_width)
        if end <= start:
            end = start + 1
        chunk = values[start:end]
        reduced.append(sum(float(v) for v in chunk) / len(chunk))
    return reduced


def render_speed_sparkline(samples: Sequence[float], width: int = 60) -> str:
    """Render fixed-width sparkline for speed history.

    Samples are bytes/s. The returned string length is always `width`.
    """
    if width <= 0:
        return ""

    reduced = _downsample(samples, width)
    if len(reduced) < width:
        reduced = ([0.0] * (width - len(reduced))) + reduced

    max_value = max(reduced) if reduced else 0.0
    if max_value <= 0:
        return SPARK_CHARS[0] * width

    top_index = len(SPARK_CHARS) - 1
    out = []
    for value in reduced:
        ratio = max(0.0, min(1.0, float(value) / max_value))
        idx = int(round(ratio * top_index))
        out.append(SPARK_CHARS[idx])
    return "".join(out)
