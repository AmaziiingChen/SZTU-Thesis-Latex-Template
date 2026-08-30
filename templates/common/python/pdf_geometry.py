"""Reusable PDF geometry and raster assertions for form-template QA."""

from __future__ import annotations

from PIL import Image


def bbox(chars: list[dict]) -> tuple[float, float, float, float]:
    return (
        min(float(char["x0"]) for char in chars),
        min(float(char["top"]) for char in chars),
        max(float(char["x1"]) for char in chars),
        max(float(char["bottom"]) for char in chars),
    )


def cell_chars(
    chars: list[dict],
    bounds: tuple[float, float, float, float],
    *,
    font: str,
    size: float,
) -> list[dict]:
    x0, top, x1, bottom = bounds
    return [
        char
        for char in chars
        if x0 <= (float(char["x0"]) + float(char["x1"])) / 2 <= x1
        and top <= (float(char["top"]) + float(char["bottom"])) / 2 <= bottom
        and font in char["fontname"]
        and round(float(char["size"]), 2) == size
    ]


def assert_centered(chars: list[dict], bounds: tuple[float, float, float, float]) -> None:
    assert chars
    x0, top, x1, bottom = bounds
    bx0, btop, bx1, bbottom = bbox(chars)
    horizontal_error = abs((bx0 + bx1) / 2 - (x0 + x1) / 2)
    vertical_error = abs((btop + bbottom) / 2 - (top + bottom) / 2)
    assert horizontal_error <= 1.7, (bounds, bbox(chars), horizontal_error)
    assert vertical_error <= 1.7, (bounds, bbox(chars), vertical_error)


def assert_vertically_centered(
    chars: list[dict], bounds: tuple[float, float, float, float]
) -> None:
    assert chars
    _, top, _, bottom = bounds
    _, btop, _, bbottom = bbox(chars)
    vertical_error = abs((btop + bbottom) / 2 - (top + bottom) / 2)
    assert vertical_error <= 1.7, (bounds, bbox(chars), vertical_error)


def clustered(values: list[float], *, tolerance: float = 1.0) -> list[float]:
    result: list[float] = []
    for value in sorted(values):
        if not result or value - result[-1] > tolerance:
            result.append(value)
    return result


def assert_rule_has_raster_ink(
    image: Image.Image,
    *,
    page_width: float,
    page_height: float,
    x0: float,
    x1: float,
    top: float,
) -> None:
    grayscale = image.convert("L")
    scale_x = grayscale.width / page_width
    scale_y = grayscale.height / page_height
    px0 = max(0, round(x0 * scale_x))
    px1 = min(grayscale.width, round(x1 * scale_x))
    py = round(top * scale_y)
    ratios = []
    for row in range(max(0, py - 3), min(grayscale.height, py + 4)):
        dark = sum(grayscale.getpixel((column, row)) < 160 for column in range(px0, px1))
        ratios.append(dark / max(1, px1 - px0))
    assert ratios and max(ratios) >= 0.75
