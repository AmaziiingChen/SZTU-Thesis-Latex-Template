"""Shared rich-text normalization and list compatibility helpers."""

from __future__ import annotations

import re
from typing import Any


class ContentDataError(ValueError):
    """Raised when shared process-document content is invalid."""


UNICODE_SCRIPT_CHARACTERS: dict[str, tuple[str, str]] = {
    "⁰": ("0", "super"),
    "¹": ("1", "super"),
    "²": ("2", "super"),
    "³": ("3", "super"),
    "⁴": ("4", "super"),
    "⁵": ("5", "super"),
    "⁶": ("6", "super"),
    "⁷": ("7", "super"),
    "⁸": ("8", "super"),
    "⁹": ("9", "super"),
    "⁺": ("+", "super"),
    "⁻": ("−", "super"),
    "⁼": ("=", "super"),
    "⁽": ("(", "super"),
    "⁾": (")", "super"),
    "ⁱ": ("i", "super"),
    "ⁿ": ("n", "super"),
    "₀": ("0", "sub"),
    "₁": ("1", "sub"),
    "₂": ("2", "sub"),
    "₃": ("3", "sub"),
    "₄": ("4", "sub"),
    "₅": ("5", "sub"),
    "₆": ("6", "sub"),
    "₇": ("7", "sub"),
    "₈": ("8", "sub"),
    "₉": ("9", "sub"),
    "₊": ("+", "sub"),
    "₋": ("−", "sub"),
    "₌": ("=", "sub"),
    "₍": ("(", "sub"),
    "₎": (")", "sub"),
    "ₐ": ("a", "sub"),
    "ₑ": ("e", "sub"),
    "ₒ": ("o", "sub"),
    "ₓ": ("x", "sub"),
    "ₕ": ("h", "sub"),
    "ₖ": ("k", "sub"),
    "ₗ": ("l", "sub"),
    "ₘ": ("m", "sub"),
    "ₙ": ("n", "sub"),
    "ₚ": ("p", "sub"),
    "ₛ": ("s", "sub"),
    "ₜ": ("t", "sub"),
}

PLAIN_SCIENTIFIC_CHARACTER_REPLACEMENTS = {"℃": "°C"}


def _expand_legacy_scientific_run(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert compatibility glyphs into semantic run properties."""

    expanded: list[dict[str, Any]] = []
    explicit_script = run["script"]
    for character in run["text"]:
        mapped = UNICODE_SCRIPT_CHARACTERS.get(character)
        if mapped is not None:
            text, inferred_script = mapped
            script = explicit_script if explicit_script != "normal" else inferred_script
        else:
            text = PLAIN_SCIENTIFIC_CHARACTER_REPLACEMENTS.get(character, character)
            script = explicit_script
        style = {
            "script": script,
            "italic": run["italic"],
            "bold": run["bold"],
        }
        previous = expanded[-1] if expanded else None
        if previous is not None and all(
            previous[key] == value for key, value in style.items()
        ):
            previous["text"] += text
        else:
            expanded.append({"text": text, **style})
    return expanded


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContentDataError(f"{path} must be an object")
    return value


def require_text(value: Any, path: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentDataError(f"{path} must be a non-empty string")
    text = value.strip()
    if len(text) > max_length:
        raise ContentDataError(f"{path} exceeds {max_length} characters")
    return text


def display_width(text: str) -> float:
    return sum(0.5 if ord(char) < 128 else 1.0 for char in text)


ARABIC_MONTH_PATTERN = r"(?:0?[1-9]|1[0-2])"
CHINESE_MONTH_PATTERN = r"(?:[一二三四五六七八九]|十[一二]?)"
MONTH_RANGE_CONNECTOR_PATTERN = r"[-–—－~～至]"
CALENDAR_DATE_PREFIX_PATTERN = re.compile(
    rf"^\s*(?:"
    rf"(?:19|20)\d{{2}}\s*年\s*(?:"
    rf"{ARABIC_MONTH_PATTERN}\s*(?:月|{MONTH_RANGE_CONNECTOR_PATTERN}\s*{ARABIC_MONTH_PATTERN}\s*月)"
    rf"|{CHINESE_MONTH_PATTERN}\s*月"
    rf")"
    rf"|(?:19|20)\d{{2}}\s*[-./]\s*{ARABIC_MONTH_PATTERN}(?!\d)"
    rf"|{ARABIC_MONTH_PATTERN}\s*(?:月|{MONTH_RANGE_CONNECTOR_PATTERN}\s*{ARABIC_MONTH_PATTERN}\s*月)"
    rf"|{CHINESE_MONTH_PATTERN}\s*月"
    rf")"
)


def starts_with_calendar_date(text: str) -> bool:
    """Return whether a schedule label begins with a calendar month/date.

    Week labels such as ``第1—2周`` are deliberately excluded, while compact
    month ranges such as ``2026年1—2月`` remain date-prefixed paragraphs.
    """

    return CALENDAR_DATE_PREFIX_PATTERN.match(text) is not None


def runs_text(runs: list[dict[str, Any]]) -> str:
    return "".join(run["text"] for run in runs)


def normalize_paragraph(
    value: Any,
    path: str,
    max_length: int,
    *,
    max_runs: int = 100,
) -> list[dict[str, Any]]:
    if isinstance(value, str):
        text = require_text(value, path, max_length)
        return _expand_legacy_scientific_run(
            {"text": text, "script": "normal", "italic": False, "bold": False}
        )
    paragraph = require_object(value, path)
    unknown_paragraph = set(paragraph) - {"type", "runs"}
    if unknown_paragraph or "runs" not in paragraph:
        raise ContentDataError(f"{path} must contain only type and a non-empty runs array")
    if paragraph.get("type", "paragraph") != "paragraph":
        raise ContentDataError(f"{path}.type must be paragraph")
    runs = paragraph["runs"]
    if not isinstance(runs, list) or not runs or len(runs) > max_runs:
        raise ContentDataError(f"{path}.runs must contain 1 to {max_runs} items")
    clean_runs: list[dict[str, Any]] = []
    for index, raw_run in enumerate(runs):
        run_path = f"{path}.runs[{index}]"
        run = require_object(raw_run, run_path)
        unknown = set(run) - {"text", "script", "italic", "bold"}
        if unknown:
            raise ContentDataError(f"unknown fields in {run_path}: {sorted(unknown)}")
        text = run.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ContentDataError(f"{run_path}.text must be a non-empty string")
        if len(text) > max_length:
            raise ContentDataError(f"{run_path}.text exceeds {max_length} characters")
        script = run.get("script", "normal")
        if script not in {"normal", "sub", "super"}:
            raise ContentDataError(f"{run_path}.script must be normal, sub, or super")
        italic = run.get("italic", False)
        bold = run.get("bold", False)
        if not isinstance(italic, bool) or not isinstance(bold, bool):
            raise ContentDataError(f"{run_path}.italic and .bold must be booleans")
        clean_runs.extend(
            _expand_legacy_scientific_run(
                {"text": text, "script": script, "italic": italic, "bold": bold}
            )
        )
    if len(clean_runs) > max_runs:
        raise ContentDataError(f"{path}.runs exceeds {max_runs} normalized items")
    if sum(len(run["text"]) for run in clean_runs) > max_length:
        raise ContentDataError(f"{path} exceeds {max_length} characters")
    return clean_runs


def plain_runs(text: str) -> list[dict[str, Any]]:
    return [{"text": text, "script": "normal", "italic": False, "bold": False}]


def normalize_content_block(
    value: Any,
    path: str,
    max_length: int,
    *,
    max_list_items: int = 100,
    max_list_depth: int = 4,
) -> dict[str, Any]:
    """Normalize a paragraph, list, or image into one stable shape.

    Legacy flat ``ordered_list`` blocks remain valid. New list items may carry
    one ``children`` list block, with the root list counted as depth one.
    """
    if not isinstance(value, dict) or value.get("type", "paragraph") == "paragraph":
        return {
            "type": "paragraph",
            "runs": normalize_paragraph(value, path, max_length),
        }
    block = require_object(value, path)
    if block.get("type") == "image":
        unknown = set(block) - {"type", "path", "alt", "width_mm", "caption"}
        if unknown:
            raise ContentDataError(f"unknown fields in {path}: {sorted(unknown)}")
        image_path = require_text(block.get("path"), f"{path}.path", 1000)
        alt = require_text(block.get("alt"), f"{path}.alt", 500)
        width_mm = block.get("width_mm", 120.0)
        if (
            isinstance(width_mm, bool)
            or not isinstance(width_mm, (int, float))
            or not 20 <= float(width_mm) <= 146
        ):
            raise ContentDataError(f"{path}.width_mm must be between 20 and 146")
        caption = block.get("caption")
        return {
            "type": "image",
            "path": image_path,
            "alt": alt,
            "width_mm": float(width_mm),
            "caption_runs": normalize_paragraph(
                caption, f"{path}.caption", max_length
            )
            if caption is not None
            else None,
        }
    if block.get("type") not in {"ordered_list", "unordered_list"}:
        raise ContentDataError(
            f"{path}.type must be paragraph, ordered_list, unordered_list, or image"
        )
    return normalize_list_block(
        block,
        path,
        max_length,
        max_list_items=max_list_items,
        max_list_depth=max_list_depth,
    )


def normalize_list_block(
    value: Any,
    path: str,
    max_length: int,
    *,
    max_list_items: int = 100,
    max_list_depth: int = 4,
    _depth: int = 1,
) -> dict[str, Any]:
    """Normalize one ordered or unordered list tree, capped at four levels."""
    if max_list_depth < 1:
        raise ContentDataError("max_list_depth must be at least 1")
    if _depth > max_list_depth:
        raise ContentDataError(
            f"{path} exceeds the maximum list depth of {max_list_depth}"
        )
    block = require_object(value, path)
    list_type = block.get("type")
    if list_type not in {"ordered_list", "unordered_list"}:
        raise ContentDataError(
            f"{path}.type must be ordered_list or unordered_list"
        )
    unknown = set(block) - {"type", "items"}
    items = block.get("items")
    if unknown or not isinstance(items, list) or not items or len(items) > max_list_items:
        raise ContentDataError(
            f"{path} {list_type} must contain only type and 1 to {max_list_items} items"
        )
    clean_items = []
    for index, raw_item in enumerate(items):
        item_path = f"{path}.items[{index}]"
        item = require_object(raw_item, item_path)
        allowed = {"content", "children"}
        if list_type == "ordered_list":
            allowed.add("marker")
        item_unknown = set(item) - allowed
        if item_unknown or "content" not in item:
            marker_clause = "optional marker, " if list_type == "ordered_list" else ""
            raise ContentDataError(
                f"{item_path} must contain only {marker_clause}content, and optional children"
            )
        marker = item.get("marker")
        if marker is not None:
            marker = require_text(marker, f"{item_path}.marker", 20)
        children = None
        if "children" in item:
            if _depth >= max_list_depth:
                raise ContentDataError(
                    f"{item_path}.children exceeds the maximum list depth of {max_list_depth}"
                )
            children = normalize_list_block(
                item["children"],
                f"{item_path}.children",
                max_length,
                max_list_items=max_list_items,
                max_list_depth=max_list_depth,
                _depth=_depth + 1,
            )
        clean_items.append(
            {
                "marker": marker,
                "runs": normalize_paragraph(
                    item["content"], f"{item_path}.content", max_length
                ),
                "children": children,
            }
        )
    return {"type": list_type, "items": clean_items}


def has_explicit_numbering(runs: list[dict[str, Any]]) -> bool:
    text = runs_text(runs).lstrip()
    return re.match(r"^(?:第[一二三四五六七八九十]+阶段|[（(]?\d+[）)、.])", text) is not None


PARENTHESIZED_SUBITEM_PATTERN = re.compile(r"[（(](\d+)[）)]")


def _slice_runs(
    runs: list[dict[str, Any]], start: int, end: int
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    cursor = 0
    for run in runs:
        text = run["text"]
        run_end = cursor + len(text)
        overlap_start = max(start, cursor)
        overlap_end = min(end, run_end)
        if overlap_start < overlap_end:
            copied = dict(run)
            copied["text"] = text[overlap_start - cursor : overlap_end - cursor]
            result.append(copied)
        cursor = run_end
    while result and not result[0]["text"].strip():
        result.pop(0)
    while result and not result[-1]["text"].strip():
        result.pop()
    if result:
        result[0]["text"] = result[0]["text"].lstrip()
        result[-1]["text"] = result[-1]["text"].rstrip()
    return [run for run in result if run["text"]]


def split_numbered_subitems(
    runs: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[tuple[str, list[dict[str, Any]]]],
    list[list[dict[str, Any]]],
] | None:
    """Split a legacy inline （1）（2） sequence while preserving run styles."""
    text = runs_text(runs)
    matches = list(PARENTHESIZED_SUBITEM_PATTERN.finditer(text))
    numbers = [int(match.group(1)) for match in matches]
    if (
        len(matches) < 2
        or numbers != list(range(1, len(matches) + 1))
        or not text[: matches[0].start()].strip()
    ):
        return None

    lead = _slice_runs(runs, 0, matches[0].start())
    subitems: list[tuple[str, list[dict[str, Any]]]] = []
    continuations: list[list[dict[str, Any]]] = []
    for index, match in enumerate(matches):
        item_start = match.end()
        item_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        if index == len(matches) - 1:
            newline = text.find("\n", item_start, item_end)
            if newline != -1:
                item_end = newline
                continuation_start = newline + 1
                for line in text[continuation_start:].splitlines():
                    line_start = text.find(line, continuation_start)
                    line_end = line_start + len(line)
                    continuation_start = line_end
                    paragraph = _slice_runs(runs, line_start, line_end)
                    if paragraph:
                        continuations.append(paragraph)
        item = _slice_runs(runs, item_start, item_end)
        if not item:
            return None
        subitems.append((match.group(0), item))
    return lead, subitems, continuations
