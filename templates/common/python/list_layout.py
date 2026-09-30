"""Measure process-form list markers for hanging-indent geometry."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from .content import list_marker_text


@lru_cache(maxsize=16)
def _font(path: str, scaled_size: int):
    return ImageFont.truetype(path, scaled_size)


def marker_advance_pt(
    marker: str, *, size_pt: float, latin_font: Path, cjk_font: Path
) -> float:
    """Return the marker and thin separator advance in the configured Word fonts."""
    scale = 16
    scaled_size = round(size_pt * scale)
    total = 0.0
    for char in list_marker_text(marker):
        # U+2009 is spacing between marker and body; Word lays it out as Latin
        # spacing even when the preceding marker uses the CJK font.
        font = latin_font if ord(char) < 128 or char == "\u2009" else cjk_font
        total += _font(str(font), scaled_size).getlength(char) / scale
    return total
