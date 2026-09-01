"""Shared outline numbering rules for process documents and the thesis."""

from __future__ import annotations

from collections.abc import Iterable


NUMBERING_STYLES = {
    "chinese_hierarchy": 4,
    "chapter_hierarchy": 5,
    "chapter_section_hierarchy": 6,
    "part_chapter_section_hierarchy": 6,
    "decimal_hierarchy": 6,
}


def require_numbering_style(value: object, path: str = "numbering_style") -> str:
    if not isinstance(value, str) or value not in NUMBERING_STYLES:
        supported = ", ".join(NUMBERING_STYLES)
        raise ValueError(f"{path} must be one of: {supported}")
    return value


def chinese_number(value: int) -> str:
    """Render a positive integer using formal outline Chinese numerals."""

    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 9999:
        raise ValueError("outline counters must be integers from 1 to 9999")
    digits = "零一二三四五六七八九"
    units = ("", "十", "百", "千")
    source = str(value)
    parts: list[str] = []
    pending_zero = False
    for index, character in enumerate(source):
        digit = int(character)
        unit_index = len(source) - index - 1
        if digit == 0:
            pending_zero = bool(parts)
            continue
        if pending_zero:
            parts.append("零")
            pending_zero = False
        if not (digit == 1 and unit_index == 1 and not parts):
            parts.append(digits[digit])
        parts.append(units[unit_index])
    return "".join(parts)


def style_max_depth(style: str) -> int:
    return NUMBERING_STYLES[require_numbering_style(style)]


def _format_counter(style: str, level: int, counters: list[int]) -> str:
    current = counters[level - 1]
    chinese = chinese_number(current)
    if style == "decimal_hierarchy":
        decimal = ".".join(str(counter) for counter in counters[:level])
        return f"{decimal}." if level == 1 else decimal
    patterns = {
        "chinese_hierarchy": (
            lambda: f"{chinese}、",
            lambda: f"（{chinese}）",
            lambda: f"{current}.",
            lambda: f"({current})",
        ),
        "chapter_hierarchy": (
            lambda: f"第{chinese}章",
            lambda: f"{chinese}、",
            lambda: f"（{chinese}）",
            lambda: f"{current}.",
            lambda: f"({current})",
        ),
        "chapter_section_hierarchy": (
            lambda: f"第{chinese}章",
            lambda: f"第{chinese}节",
            lambda: f"{chinese}、",
            lambda: f"（{chinese}）",
            lambda: f"{current}.",
            lambda: f"({current})",
        ),
        "part_chapter_section_hierarchy": (
            lambda: f"第{chinese}篇",
            lambda: f"第{chinese}章",
            lambda: f"第{chinese}节",
            lambda: f"{chinese}、",
            lambda: f"（{chinese}）",
            lambda: f"{current}.",
        ),
    }
    return patterns[style][level - 1]()


def number_outline_levels(levels: Iterable[int], style: str) -> list[str]:
    """Validate semantic outline levels and return canonical display numbers."""

    style = require_numbering_style(style)
    maximum = NUMBERING_STYLES[style]
    counters = [0] * maximum
    rendered: list[str] = []
    previous_level = 1
    for index, level in enumerate(levels):
        if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= maximum:
            raise ValueError(
                f"outline level at index {index} must be an integer from 1 to {maximum}"
            )
        if index == 0 and level != 1:
            raise ValueError("the first outline item must be level 1")
        if index > 0 and level > previous_level + 1:
            raise ValueError(f"outline level at index {index} skips an intermediate level")
        counters[level - 1] += 1
        for counter_index in range(level, maximum):
            counters[counter_index] = 0
        rendered.append(_format_counter(style, level, counters))
        previous_level = level
    return rendered
