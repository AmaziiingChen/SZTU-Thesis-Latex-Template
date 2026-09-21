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
FIGURE_ID_PATTERN = re.compile(r"fig-[A-Za-z0-9_-]{8,96}")
FIGURE_REFERENCE_PATTERN = re.compile(r"\{\{fig:(fig-[A-Za-z0-9_-]{8,96})\}\}")
FIGURE_SOURCE_KEY_PATTERN = re.compile(r"[A-Za-z0-9_:.+/-]{1,200}")
EQUATION_ID_PATTERN = re.compile(r"eq-[A-Za-z0-9_-]{8,96}")
EQUATION_REFERENCE_PATTERN = re.compile(r"\{\{eq:(eq-[A-Za-z0-9_-]{8,96})\}\}")
MATH_TEXT_PATTERN = re.compile(
    r"[A-Za-z0-9αβγδεζηθικλμνξοπρστυφχψωΓΔΘΛΞΠΣΥΦΨΩ +\-\u2212=\u00d7\u00b7/(),.\[\]<>\u2264\u2265%|:]+"
)
MATH_NODE_TYPES = {"text", "row", "fraction", "subscript", "superscript", "square_root"}


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


def normalize_math_expression(
    value: Any,
    path: str,
    *,
    max_depth: int = 8,
    max_nodes: int = 100,
    _depth: int = 1,
    _counter: list[int] | None = None,
) -> dict[str, Any]:
    """Normalize a renderer-independent display-math AST.

    The public data model deliberately has no raw TeX/MathML/OMML escape hatch.
    Word and LaTeX therefore render the same validated semantic tree.
    """
    if _depth > max_depth:
        raise ContentDataError(f"{path} exceeds the maximum math depth of {max_depth}")
    counter = _counter if _counter is not None else [0]
    counter[0] += 1
    if counter[0] > max_nodes:
        raise ContentDataError(f"{path} exceeds the maximum of {max_nodes} math nodes")
    node = require_object(value, path)
    node_type = node.get("type")
    if node_type not in MATH_NODE_TYPES:
        raise ContentDataError(f"{path}.type is not a supported math node")

    def child(raw: Any, child_path: str) -> dict[str, Any]:
        return normalize_math_expression(
            raw,
            child_path,
            max_depth=max_depth,
            max_nodes=max_nodes,
            _depth=_depth + 1,
            _counter=counter,
        )

    if node_type == "text":
        if set(node) != {"type", "value"}:
            raise ContentDataError(f"{path} text node must contain only type and value")
        text = require_text(node.get("value"), f"{path}.value", 100)
        if MATH_TEXT_PATTERN.fullmatch(text) is None:
            raise ContentDataError(f"{path}.value contains unsupported math characters")
        return {"type": "text", "value": text}
    if node_type == "row":
        if set(node) != {"type", "items"}:
            raise ContentDataError(f"{path} row node must contain only type and items")
        items = node.get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= 50:
            raise ContentDataError(f"{path}.items must contain 1 to 50 math nodes")
        return {
            "type": "row",
            "items": [child(item, f"{path}.items[{index}]") for index, item in enumerate(items)],
        }
    fields = {
        "fraction": ("numerator", "denominator"),
        "subscript": ("base", "sub"),
        "superscript": ("base", "super"),
        "square_root": ("body",),
    }[node_type]
    if set(node) != {"type", *fields}:
        raise ContentDataError(f"{path} {node_type} node has invalid fields")
    return {
        "type": node_type,
        **{field: child(node[field], f"{path}.{field}") for field in fields},
    }


def normalize_content_block(
    value: Any,
    path: str,
    max_length: int,
    *,
    max_list_items: int = 100,
    max_list_depth: int = 4,
) -> dict[str, Any]:
    """Normalize one public process-document content block into a stable shape.

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
        unknown = set(block) - {
            "type",
            "id",
            "path",
            "alt",
            "chapter",
            "width_mm",
            "caption",
            "source_citation_key",
        }
        if unknown:
            raise ContentDataError(f"unknown fields in {path}: {sorted(unknown)}")
        figure_id = block.get("id")
        if figure_id is not None and (
            not isinstance(figure_id, str)
            or FIGURE_ID_PATTERN.fullmatch(figure_id) is None
        ):
            raise ContentDataError(f"{path}.id must be a stable figure id")
        image_path = require_text(block.get("path"), f"{path}.path", 1000)
        alt = require_text(block.get("alt"), f"{path}.alt", 500)
        chapter = block.get("chapter", 1)
        if (
            isinstance(chapter, bool)
            or not isinstance(chapter, int)
            or not 1 <= chapter <= 99
        ):
            raise ContentDataError(f"{path}.chapter must be an integer from 1 to 99")
        width_mm = block.get("width_mm", 120.0)
        if (
            isinstance(width_mm, bool)
            or not isinstance(width_mm, (int, float))
            or not 20 <= float(width_mm) <= 146
        ):
            raise ContentDataError(f"{path}.width_mm must be between 20 and 146")
        caption = block.get("caption")
        if figure_id is not None and caption is None:
            raise ContentDataError(f"{path}.caption is required for a referenced figure")
        source_citation_key = block.get("source_citation_key")
        if source_citation_key is not None and (
            not isinstance(source_citation_key, str)
            or FIGURE_SOURCE_KEY_PATTERN.fullmatch(source_citation_key) is None
        ):
            raise ContentDataError(
                f"{path}.source_citation_key contains unsupported characters"
            )
        normalized = {
            "type": "image",
            "path": image_path,
            "alt": alt,
            "chapter": chapter,
            "width_mm": float(width_mm),
            "caption_runs": normalize_paragraph(
                caption, f"{path}.caption", max_length
            )
            if caption is not None
            else None,
        }
        if figure_id is not None:
            normalized["id"] = figure_id
        if source_citation_key is not None:
            normalized["source_citation_key"] = source_citation_key
        return normalized
    if block.get("type") == "figure_group":
        unknown = set(block) - {
            "type",
            "id",
            "chapter",
            "items",
            "columns",
            "caption",
            "source_citation_key",
        }
        if unknown:
            raise ContentDataError(f"unknown fields in {path}: {sorted(unknown)}")
        figure_id = block.get("id")
        if figure_id is not None and (
            not isinstance(figure_id, str)
            or FIGURE_ID_PATTERN.fullmatch(figure_id) is None
        ):
            raise ContentDataError(f"{path}.id must be a stable figure id")
        chapter = block.get("chapter", 1)
        if (
            isinstance(chapter, bool)
            or not isinstance(chapter, int)
            or not 1 <= chapter <= 99
        ):
            raise ContentDataError(f"{path}.chapter must be an integer from 1 to 99")
        raw_items = block.get("items")
        if not isinstance(raw_items, list) or not 2 <= len(raw_items) <= 4:
            raise ContentDataError(f"{path}.items must contain 2 to 4 images")
        columns = block.get("columns", len(raw_items))
        if isinstance(columns, bool) or not isinstance(columns, int) or not 1 <= columns <= 4:
            raise ContentDataError(f"{path}.columns must be from 1 to 4")
        items = []
        for index, raw_item in enumerate(raw_items):
            item_path = f"{path}.items[{index}]"
            item = require_object(raw_item, item_path)
            item_unknown = set(item) - {"path", "alt", "caption"}
            if item_unknown:
                raise ContentDataError(
                    f"unknown fields in {item_path}: {sorted(item_unknown)}"
                )
            child = {
                "path": require_text(item.get("path"), f"{item_path}.path", 1000),
                "alt": require_text(item.get("alt"), f"{item_path}.alt", 500),
                "subfigure_label": f"（{chr(ord('a') + index)}）",
                "caption_runs": normalize_paragraph(
                    item["caption"], f"{item_path}.caption", max_length
                )
                if item.get("caption") is not None
                else None,
            }
            items.append(child)
        source_citation_key = block.get("source_citation_key")
        if source_citation_key is not None and (
            not isinstance(source_citation_key, str)
            or FIGURE_SOURCE_KEY_PATTERN.fullmatch(source_citation_key) is None
        ):
            raise ContentDataError(
                f"{path}.source_citation_key contains unsupported characters"
            )
        normalized = {
            "type": "figure_group",
            "chapter": chapter,
            "items": items,
            "columns": columns,
            "caption_runs": normalize_paragraph(
                block.get("caption"), f"{path}.caption", max_length
            ),
        }
        if figure_id is not None:
            normalized["id"] = figure_id
        if source_citation_key is not None:
            normalized["source_citation_key"] = source_citation_key
        return normalized
    if block.get("type") == "data_table":
        unknown = set(block) - {"type", "columns", "rows", "caption", "style"}
        if unknown:
            raise ContentDataError(f"unknown fields in {path}: {sorted(unknown)}")
        style = block.get("style", "grid")
        if style not in {"grid", "three_line"}:
            raise ContentDataError(f"{path}.style must be grid or three_line")
        raw_columns = block.get("columns")
        if not isinstance(raw_columns, list) or not 2 <= len(raw_columns) <= 8:
            raise ContentDataError(f"{path}.columns must contain 2 to 8 columns")
        columns = []
        for index, raw_column in enumerate(raw_columns):
            column_path = f"{path}.columns[{index}]"
            column = require_object(raw_column, column_path)
            column_unknown = set(column) - {"header", "width_weight", "alignment"}
            if column_unknown:
                raise ContentDataError(
                    f"unknown fields in {column_path}: {sorted(column_unknown)}"
                )
            width_weight = column.get("width_weight", 1.0)
            if (
                isinstance(width_weight, bool)
                or not isinstance(width_weight, (int, float))
                or not 0.25 <= float(width_weight) <= 10
            ):
                raise ContentDataError(
                    f"{column_path}.width_weight must be between 0.25 and 10"
                )
            alignment = column.get("alignment", "left")
            if alignment not in {"left", "center", "right"}:
                raise ContentDataError(
                    f"{column_path}.alignment must be left, center, or right"
                )
            columns.append(
                {
                    "header_runs": normalize_paragraph(
                        column.get("header"), f"{column_path}.header", max_length
                    ),
                    "width_weight": float(width_weight),
                    "alignment": alignment,
                }
            )
        raw_rows = block.get("rows")
        if not isinstance(raw_rows, list) or not 1 <= len(raw_rows) <= 40:
            raise ContentDataError(f"{path}.rows must contain 1 to 40 rows")
        rows = []
        for row_index, raw_row in enumerate(raw_rows):
            row_path = f"{path}.rows[{row_index}]"
            row = require_object(raw_row, row_path)
            if set(row) != {"cells"}:
                raise ContentDataError(f"{row_path} must contain only cells")
            raw_cells = row.get("cells")
            if not isinstance(raw_cells, list) or len(raw_cells) != len(columns):
                raise ContentDataError(
                    f"{row_path}.cells must match the {len(columns)} table columns"
                )
            rows.append(
                [
                    normalize_paragraph(
                        cell, f"{row_path}.cells[{cell_index}]", max_length
                    )
                    for cell_index, cell in enumerate(raw_cells)
                ]
            )
        return {
            "type": "data_table",
            "style": style,
            "columns": columns,
            "rows": rows,
            "caption_runs": normalize_paragraph(
                block["caption"], f"{path}.caption", max_length
            )
            if block.get("caption") is not None
            else None,
        }
    if block.get("type") == "equation":
        unknown = set(block) - {"type", "id", "chapter", "expression", "alt"}
        if unknown:
            raise ContentDataError(f"unknown fields in {path}: {sorted(unknown)}")
        equation_id = block.get("id")
        if equation_id is not None and (
            not isinstance(equation_id, str)
            or EQUATION_ID_PATTERN.fullmatch(equation_id) is None
        ):
            raise ContentDataError(f"{path}.id must be a stable equation id")
        chapter = block.get("chapter", 1)
        if (
            isinstance(chapter, bool)
            or not isinstance(chapter, int)
            or not 1 <= chapter <= 99
        ):
            raise ContentDataError(f"{path}.chapter must be an integer from 1 to 99")
        normalized = {
            "type": "equation",
            "chapter": chapter,
            "expression": normalize_math_expression(
                block.get("expression"), f"{path}.expression"
            ),
            "alt": require_text(block.get("alt"), f"{path}.alt", 500),
        }
        if equation_id is not None:
            normalized["id"] = equation_id
        return normalized
    if block.get("type") not in {"ordered_list", "unordered_list"}:
        raise ContentDataError(
            f"{path}.type must be paragraph, ordered_list, unordered_list, image, "
            "figure_group, data_table, or equation"
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


def resolve_list_marker(
    list_type: str,
    explicit_marker: str | None,
    index: int,
    depth: int,
    unordered_markers: list[str] | tuple[str, ...],
) -> str:
    """Resolve one process-document list marker without changing explicit input."""
    if list_type == "ordered_list":
        return explicit_marker or f"{index}."
    if list_type != "unordered_list":
        raise ContentDataError(f"unsupported list type: {list_type}")
    if not 1 <= depth <= len(unordered_markers):
        raise ContentDataError(
            f"unordered list depth must be between 1 and {len(unordered_markers)}"
        )
    return unordered_markers[depth - 1]


def list_marker_text(marker: str) -> str:
    """Join a list marker to its body with the process-form narrow gap."""
    return f"{marker}\u2009"


def _iter_content_run_groups(block: dict[str, Any]):
    if block["type"] == "paragraph":
        yield block["runs"]
        return
    if block["type"] == "figure_group":
        yield block["caption_runs"]
        for item in block["items"]:
            if item["caption_runs"]:
                yield item["caption_runs"]
        return
    if block["type"] == "data_table":
        for column in block["columns"]:
            yield column["header_runs"]
        for row in block["rows"]:
            yield from row
        if block["caption_runs"]:
            yield block["caption_runs"]
        return
    if block["type"] not in {"ordered_list", "unordered_list"}:
        return
    for item in block["items"]:
        yield item["runs"]
        if item["children"] is not None:
            yield from _iter_content_run_groups(item["children"])


def _resolve_figure_references(
    runs: list[dict[str, Any]],
    labels: dict[str, str],
    *,
    path: str,
) -> None:
    for run_index, run in enumerate(runs):
        def replacement(match: re.Match[str]) -> str:
            figure_id = match.group(1)
            label = labels.get(figure_id)
            if label is None:
                raise ContentDataError(
                    f"{path}.runs[{run_index}] references unknown figure {figure_id}"
                )
            return label

        run["text"] = FIGURE_REFERENCE_PATTERN.sub(replacement, run["text"])
        if "{{fig:" in run["text"]:
            raise ContentDataError(
                f"{path}.runs[{run_index}] contains an invalid figure reference"
            )


def prepare_figure_content(
    block_groups: list[list[dict[str, Any]]],
) -> dict[str, str]:
    """Assign stable display numbers and resolve references across body sections."""

    chapter_counts: dict[int, int] = {}
    labels: dict[str, str] = {}
    for blocks in block_groups:
        for block in blocks:
            if block["type"] not in {"image", "figure_group"}:
                continue
            chapter = block["chapter"]
            sequence = chapter_counts.get(chapter, 0) + 1
            chapter_counts[chapter] = sequence
            block["figure_label"] = f"图 {chapter}-{sequence}"
            figure_id = block.get("id")
            if figure_id is None:
                continue
            if figure_id in labels:
                raise ContentDataError(f"duplicate figure id: {figure_id}")
            labels[figure_id] = block["figure_label"]

    for group_index, blocks in enumerate(block_groups):
        for block_index, block in enumerate(blocks):
            for runs in _iter_content_run_groups(block):
                _resolve_figure_references(
                    runs,
                    labels,
                    path=f"figure_groups[{group_index}][{block_index}]",
                )
    return labels


def prepare_equation_content(
    block_groups: list[list[dict[str, Any]]],
) -> dict[str, str]:
    """Number identified equations by chapter and resolve semantic references."""
    chapter_counts: dict[int, int] = {}
    labels: dict[str, str] = {}
    for blocks in block_groups:
        for block in blocks:
            if block["type"] != "equation" or block.get("id") is None:
                continue
            chapter = block["chapter"]
            sequence = chapter_counts.get(chapter, 0) + 1
            chapter_counts[chapter] = sequence
            equation_id = block["id"]
            if equation_id in labels:
                raise ContentDataError(f"duplicate equation id: {equation_id}")
            label = f"({chapter}-{sequence})"
            block["equation_label"] = label
            labels[equation_id] = label

    for group_index, blocks in enumerate(block_groups):
        for block_index, block in enumerate(blocks):
            for runs in _iter_content_run_groups(block):
                for run_index, run in enumerate(runs):
                    def replacement(match: re.Match[str]) -> str:
                        equation_id = match.group(1)
                        label = labels.get(equation_id)
                        if label is None:
                            raise ContentDataError(
                                f"equation_groups[{group_index}][{block_index}].runs[{run_index}] "
                                f"references unknown equation {equation_id}"
                            )
                        return label

                    run["text"] = EQUATION_REFERENCE_PATTERN.sub(replacement, run["text"])
                    if "{{eq:" in run["text"]:
                        raise ContentDataError(
                            f"equation_groups[{group_index}][{block_index}].runs[{run_index}] "
                            "contains an invalid equation reference"
                        )
    return labels


def figure_caption_runs(block: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the renderer-owned numbered caption for one image or group."""

    label = block.get("figure_label")
    if not isinstance(label, str) or not label:
        raise ContentDataError("figure content must be prepared before rendering")
    result = plain_runs(label)
    caption_runs = block.get("caption_runs") or []
    if caption_runs:
        result.extend(plain_runs(" "))
        result.extend(dict(run) for run in caption_runs)
    source_key = block.get("source_citation_key")
    if source_key:
        result.extend(plain_runs(f"（来源：{source_key}）"))
    return result


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
