"""Measure process-form list markers for hanging-indent geometry."""

from __future__ import annotations

import re
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
    for piece in re.findall(r"[\x00-\x7f]+|[^\x00-\x7f]+", list_marker_text(marker)):
        font = latin_font if ord(piece[0]) < 128 else cjk_font
        total += _font(str(font), scaled_size).getlength(piece) / scale
    return total
