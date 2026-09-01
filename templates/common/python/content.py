"""Shared rich-text normalization and list compatibility helpers."""

from __future__ import annotations

import re
from typing import Any


class ContentDataError(ValueError):
    """Raised when shared process-document content is invalid."""


FIGURE_REFERENCE_PATTERN = re.compile(r"\{\{fig:(fig-[A-Za-z0-9_-]{8,96})\}\}")
FIGURE_ID_PATTERN = re.compile(r"^fig-[A-Za-z0-9_-]{8,96}$")


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
        unknown = set(block) - {
            "type", "id", "path", "alt", "chapter", "width_mm", "caption",
            "source_citation_key",
        }
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
        figure_id = block.get("id")
        if figure_id is not None and (
            not isinstance(figure_id, str) or FIGURE_ID_PATTERN.fullmatch(figure_id) is None
        ):
            raise ContentDataError(f"{path}.id must be a stable figure id")
        chapter = block.get("chapter", 1)
        if isinstance(chapter, bool) or not isinstance(chapter, int) or not 1 <= chapter <= 99:
            raise ContentDataError(f"{path}.chapter must be an integer from 1 to 99")
        source_key = block.get("source_citation_key")
        if source_key is not None:
            source_key = require_text(source_key, f"{path}.source_citation_key", 200)
            if re.fullmatch(r"[A-Za-z0-9_:.+/-]+", source_key) is None:
                raise ContentDataError(f"{path}.source_citation_key has invalid characters")
        return {
            "type": "image",
            "id": figure_id,
            "path": image_path,
            "alt": alt,
            "chapter": chapter,
            "width_mm": float(width_mm),
            "caption_runs": normalize_paragraph(
                caption, f"{path}.caption", max_length
            )
            if caption is not None
            else None,
            "source_citation_key": source_key,
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


def number_and_resolve_figures(*block_groups: list[dict[str, Any]]) -> dict[str, str]:
    """Assign deterministic chapter-local numbers and resolve stable reference tokens."""
    counters: dict[int, int] = {}
    labels: dict[str, str] = {}
    legacy_index = 0
    for blocks in block_groups:
        for block in blocks:
            if block["type"] != "image":
                continue
            legacy_index += 1
            figure_id = block.get("id") or f"fig-legacy-{legacy_index:04d}"
            if figure_id in labels:
                raise ContentDataError(f"duplicate figure id: {figure_id}")
            chapter = block.get("chapter", 1)
            counters[chapter] = counters.get(chapter, 0) + 1
            label = f"图 {chapter}-{counters[chapter]}"
            block["id"] = figure_id
            block["figure_label"] = label
            labels[figure_id] = label

    def resolve_runs(runs: list[dict[str, Any]], path: str) -> None:
        for run in runs:
            def replacement(match: re.Match[str]) -> str:
                figure_id = match.group(1)
                if figure_id not in labels:
                    raise ContentDataError(f"{path} references unknown figure id: {figure_id}")
                return labels[figure_id]
            run["text"] = FIGURE_REFERENCE_PATTERN.sub(replacement, run["text"])

    for group_index, blocks in enumerate(block_groups):
        for block_index, block in enumerate(blocks):
            base = f"figure_groups[{group_index}][{block_index}]"
            if block["type"] == "paragraph":
                resolve_runs(block["runs"], base)
            elif block["type"] == "ordered_list":
                for item_index, item in enumerate(block["items"]):
                    resolve_runs(item["runs"], f"{base}.items[{item_index}]")
            elif block["type"] == "image" and block.get("caption_runs"):
                resolve_runs(block["caption_runs"], f"{base}.caption")
    return labels


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
