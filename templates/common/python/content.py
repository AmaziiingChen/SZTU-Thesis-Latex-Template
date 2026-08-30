"""Shared rich-text normalization and list compatibility helpers."""

from __future__ import annotations

import re
from typing import Any


class ContentDataError(ValueError):
    """Raised when shared process-document content is invalid."""


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
        return [{"text": text, "script": "normal", "italic": False, "bold": False}]
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
        clean_runs.append(
            {"text": text, "script": script, "italic": italic, "bold": bold}
        )
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
) -> dict[str, Any]:
    """Normalize a paragraph or explicit ordered list into one stable shape."""
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
    if block.get("type") != "ordered_list":
        raise ContentDataError(
            f"{path}.type must be paragraph, ordered_list, or image"
        )
    unknown = set(block) - {"type", "items"}
    items = block.get("items")
    if unknown or not isinstance(items, list) or not items or len(items) > max_list_items:
        raise ContentDataError(
            f"{path} ordered_list must contain only type and 1 to {max_list_items} items"
        )
    clean_items = []
    for index, raw_item in enumerate(items):
        item_path = f"{path}.items[{index}]"
        item = require_object(raw_item, item_path)
        item_unknown = set(item) - {"marker", "content"}
        if item_unknown or "content" not in item:
            raise ContentDataError(
                f"{item_path} must contain only optional marker and content"
            )
        marker = item.get("marker")
        if marker is not None:
            marker = require_text(marker, f"{item_path}.marker", 20)
        clean_items.append(
            {
                "marker": marker,
                "runs": normalize_paragraph(
                    item["content"], f"{item_path}.content", max_length
                ),
            }
        )
    return {"type": "ordered_list", "items": clean_items}


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
