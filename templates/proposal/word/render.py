#!/usr/bin/env python3
"""Render the official SZTU proposal DOCX from schema-constrained JSON data."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt


SCHEMA_VERSION = "0.2"
METADATA_LIMITS = {
    "title": 80,
    "student_name": 20,
    "student_id": 30,
    "major": 40,
    "college": 50,
    "advisor": 30,
}
SECTION_KEYS = (
    "significance_and_status",
    "research_content",
    "methods_and_means",
    "research_steps",
    "references",
)
ADVISOR_TITLE_PATTERN = re.compile(r"(?:老师|教授|副教授|讲师|博士|硕士|导师)$")
TITLE_DISPLAY_WIDTH_LIMIT = 64.0


class DataError(ValueError):
    """Raised when input data does not match the proposal schema subset."""


def _require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DataError(f"{path} must be an object")
    return value


def _require_text(value: Any, path: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{path} must be a non-empty string")
    text = value.strip()
    if len(text) > max_length:
        raise DataError(f"{path} exceeds {max_length} characters")
    return text


def _display_width(text: str) -> float:
    return sum(0.5 if ord(char) < 128 else 1.0 for char in text)


def _runs_text(runs: list[dict[str, Any]]) -> str:
    return "".join(run["text"] for run in runs)


def _require_paragraph(value: Any, path: str, max_length: int) -> list[dict[str, Any]]:
    if isinstance(value, str):
        text = _require_text(value, path, max_length)
        return [{"text": text, "script": "normal", "italic": False, "bold": False}]
    paragraph = _require_object(value, path)
    if set(paragraph) != {"runs"}:
        raise DataError(f"{path} must contain only a non-empty runs array")
    runs = paragraph["runs"]
    if not isinstance(runs, list) or not runs or len(runs) > 100:
        raise DataError(f"{path}.runs must contain 1 to 100 items")
    clean_runs: list[dict[str, Any]] = []
    for index, raw_run in enumerate(runs):
        run_path = f"{path}.runs[{index}]"
        run = _require_object(raw_run, run_path)
        unknown = set(run) - {"text", "script", "italic", "bold"}
        if unknown:
            raise DataError(f"unknown fields in {run_path}: {sorted(unknown)}")
        text = run.get("text")
        if not isinstance(text, str) or not text.strip():
            raise DataError(f"{run_path}.text must be a non-empty string")
        if len(text) > max_length:
            raise DataError(f"{run_path}.text exceeds {max_length} characters")
        script = run.get("script", "normal")
        if script not in {"normal", "sub", "super"}:
            raise DataError(f"{run_path}.script must be normal, sub, or super")
        italic = run.get("italic", False)
        bold = run.get("bold", False)
        if not isinstance(italic, bool) or not isinstance(bold, bool):
            raise DataError(f"{run_path}.italic and .bold must be booleans")
        clean_runs.append(
            {"text": text, "script": script, "italic": italic, "bold": bold}
        )
    if sum(len(run["text"]) for run in clean_runs) > max_length:
        raise DataError(f"{path} exceeds {max_length} characters")
    return clean_runs


def validate_data(raw: Any) -> dict[str, Any]:
    data = _require_object(raw, "root")
    expected_root = {"schema_version", "metadata", "sections"}
    unknown_root = set(data) - expected_root
    if unknown_root:
        raise DataError(f"unknown root fields: {sorted(unknown_root)}")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise DataError(f"schema_version must be {SCHEMA_VERSION!r}")

    metadata = _require_object(data.get("metadata"), "metadata")
    unknown_metadata = set(metadata) - set(METADATA_LIMITS)
    if unknown_metadata:
        raise DataError(f"unknown metadata fields: {sorted(unknown_metadata)}")
    clean_metadata: dict[str, Any] = {}
    for key, limit in METADATA_LIMITS.items():
        value = metadata.get(key)
        clean_metadata[key] = (
            _require_paragraph(value, f"metadata.{key}", limit)
            if key == "title"
            else _require_text(value, f"metadata.{key}", limit)
        )
    if _display_width(_runs_text(clean_metadata["title"])) > TITLE_DISPLAY_WIDTH_LIMIT:
        raise DataError(
            "metadata.title is too wide for the official two-line title cell "
            f"(limit {TITLE_DISPLAY_WIDTH_LIMIT:g} display units)"
        )
    if ADVISOR_TITLE_PATTERN.search(clean_metadata["advisor"]):
        raise DataError("metadata.advisor must contain the name only, without a title")

    sections = _require_object(data.get("sections"), "sections")
    unknown_sections = set(sections) - set(SECTION_KEYS)
    if unknown_sections:
        raise DataError(f"unknown section fields: {sorted(unknown_sections)}")
    clean_sections: dict[str, list[list[dict[str, Any]]]] = {}
    for key in SECTION_KEYS:
        value = sections.get(key)
        if not isinstance(value, list) or not value:
            raise DataError(f"sections.{key} must be a non-empty array")
        if key == "significance_and_status" and len(value) < 2:
            raise DataError("sections.significance_and_status must contain at least 2 paragraphs")
        max_length = 1000 if key == "references" else 5000
        if len(value) > 50:
            raise DataError(f"sections.{key} may contain at most 50 items")
        clean_sections[key] = [
            _require_paragraph(item, f"sections.{key}[{index}]", max_length)
            for index, item in enumerate(value)
        ]

    return {
        "schema_version": SCHEMA_VERSION,
        "metadata": clean_metadata,
        "sections": clean_sections,
    }


def _set_run_font(run, *, name: str, size_pt: float, bold: bool = False) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size_pt)
    run.bold = bold


def _append_runs(paragraph, runs: list[dict[str, Any]], *, size_pt: float) -> None:
    for rich_run in runs:
        pieces = re.findall(r"[\x00-\x7f]+|[^\x00-\x7f]+", rich_run["text"])
        for piece in pieces:
            run = paragraph.add_run(piece)
            font_name = "Times New Roman" if ord(piece[0]) < 128 else "宋体"
            _set_run_font(run, name=font_name, size_pt=size_pt, bold=rich_run["bold"])
            run.italic = rich_run["italic"]
            run.font.subscript = rich_run["script"] == "sub"
            run.font.superscript = rich_run["script"] == "super"


def _remove_paragraph(paragraph) -> None:
    element = paragraph._element
    element.getparent().remove(element)
    paragraph._p = paragraph._element = None


def _fill_info_cell(
    cell,
    text: str | list[dict[str, Any]],
    *,
    size_pt: float = 10.5,
    alignment: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.CENTER,
) -> None:
    while len(cell.paragraphs) > 1:
        _remove_paragraph(cell.paragraphs[-1])
    paragraph = cell.paragraphs[0]
    paragraph.clear()
    paragraph.alignment = alignment
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1
    runs = (
        [{"text": text, "script": "normal", "italic": False, "bold": False}]
        if isinstance(text, str)
        else text
    )
    _append_runs(paragraph, runs, size_pt=size_pt)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _center_label_cell(cell) -> None:
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    for paragraph in cell.paragraphs:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)


def _format_body_paragraph(paragraph, *, references: bool, indent: bool = True) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT if references else WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1
    paragraph.paragraph_format.first_line_indent = None if references or not indent else Pt(21)


def _fill_section(
    cell,
    paragraphs: list[list[dict[str, Any]]],
    *,
    references: bool = False,
) -> None:
    if not cell.paragraphs:
        raise RuntimeError("section cell has no label paragraph")
    # Reuse the official paragraph slots, then remove unused blank slots. The
    # table rows already carry their official minimum heights; retaining every
    # blank paragraph would add its line height on top of wrapped content and
    # can push an otherwise normal document onto a third page in Word.
    slots = list(cell.paragraphs[1:])
    for index, text in enumerate(paragraphs):
        paragraph = slots[index] if index < len(slots) else cell.add_paragraph()
        paragraph.clear()
        _format_body_paragraph(paragraph, references=references)
        _append_runs(paragraph, text, size_pt=10.5)
    for paragraph in slots[len(paragraphs) :]:
        _remove_paragraph(paragraph)


def _plain_runs(text: str) -> list[dict[str, Any]]:
    return [{"text": text, "script": "normal", "italic": False, "bold": False}]


def _has_explicit_numbering(runs: list[dict[str, Any]]) -> bool:
    text = "".join(run["text"] for run in runs).lstrip()
    return re.match(r"^(?:第[一二三四五六七八九十]+阶段|[（(]?\d+[）)、.])", text) is not None


PARENTHESIZED_SUBITEM_PATTERN = re.compile(r"[（(](\d+)[）)]")


def _slice_runs(
    runs: list[dict[str, Any]], start: int, end: int
) -> list[dict[str, Any]]:
    """Return a style-preserving character slice of rich-text runs."""
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
    """Split an inline （1）（2） sequence into semantic subparagraphs.

    At least two consecutive markers starting at 1 are required, which avoids
    treating an isolated parenthesized number as a nested list. A newline after
    the final subitem starts an ordinary continuation paragraph.
    """
    text = "".join(run["text"] for run in runs)
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


def _fill_methods_section(
    cell,
    methods: list[list[dict[str, Any]]],
    steps: list[list[dict[str, Any]]],
) -> None:
    if not cell.paragraphs:
        raise RuntimeError("methods cell has no label paragraph")
    for paragraph in list(cell.paragraphs[1:]):
        _remove_paragraph(paragraph)

    groups = (
        ("本课题研究方法、手段如下：", methods),
        ("本课题研究步骤如下：", steps),
    )
    for heading, items in groups:
        heading_paragraph = cell.add_paragraph()
        _format_body_paragraph(heading_paragraph, references=False)
        _append_runs(heading_paragraph, _plain_runs(heading), size_pt=10.5)
        for index, item in enumerate(items, start=1):
            split_item = split_numbered_subitems(item)
            paragraph = cell.add_paragraph()
            _format_body_paragraph(paragraph, references=False)
            lead = split_item[0] if split_item else item
            if not _has_explicit_numbering(lead):
                _append_runs(paragraph, _plain_runs(f"{index}、"), size_pt=10.5)
            _append_runs(paragraph, lead, size_pt=10.5)
            if split_item:
                _, subitems, continuations = split_item
                for marker, subitem in subitems:
                    nested = cell.add_paragraph()
                    _format_body_paragraph(nested, references=False)
                    nested.paragraph_format.left_indent = Pt(10.5)
                    _append_runs(
                        nested, _plain_runs(f"{marker} "), size_pt=10.5
                    )
                    _append_runs(nested, subitem, size_pt=10.5)
                for continuation in continuations:
                    trailing = cell.add_paragraph()
                    _format_body_paragraph(trailing, references=False)
                    _append_runs(trailing, continuation, size_pt=10.5)


def _prevent_row_split(row) -> None:
    properties = row._tr.get_or_add_trPr()
    if properties.find(qn("w:cantSplit")) is None:
        properties.append(OxmlElement("w:cantSplit"))


def render(template: Path, data_path: Path, output: Path, *, overwrite: bool) -> None:
    if not template.is_file():
        raise FileNotFoundError(f"template not found: {template}")
    if output.suffix.lower() != ".docx":
        raise DataError("output path must end with .docx")
    if output.exists() and not overwrite:
        raise FileExistsError(f"output exists; pass --overwrite to replace it: {output}")

    data = validate_data(json.loads(data_path.read_text(encoding="utf-8")))
    document = Document(template)
    if len(document.tables) != 1:
        raise RuntimeError("expected exactly one table in the official template")
    table = document.tables[0]
    if len(table.rows) != 9 or len(table.columns) != 7:
        raise RuntimeError("expected the official 9-row, 7-column table grid")

    # Preserve the official compact metadata rows while allowing long titles,
    # college names, or majors to wrap without being clipped by an exact height.
    for row_index in (0, 1, 2):
        table.rows[row_index].height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST

    metadata = data["metadata"]
    for row_index, cell_index in ((0, 0), (1, 0), (1, 2), (1, 5), (2, 0), (2, 2)):
        _center_label_cell(table.rows[row_index].cells[cell_index])

    _fill_info_cell(
        table.rows[0].cells[1],
        metadata["title"],
        alignment=WD_ALIGN_PARAGRAPH.LEFT,
    )
    _fill_info_cell(table.rows[1].cells[1], metadata["student_name"])
    _fill_info_cell(table.rows[1].cells[3], metadata["student_id"])
    _fill_info_cell(
        table.rows[1].cells[6],
        metadata["major"],
        alignment=WD_ALIGN_PARAGRAPH.LEFT,
    )
    _fill_info_cell(
        table.rows[2].cells[1],
        metadata["college"],
        alignment=WD_ALIGN_PARAGRAPH.LEFT,
    )
    _fill_info_cell(table.rows[2].cells[4], metadata["advisor"])

    sections = data["sections"]
    _fill_section(table.rows[3].cells[0], sections["significance_and_status"])
    _fill_section(table.rows[4].cells[0], sections["research_content"])
    _fill_methods_section(
        table.rows[5].cells[0],
        sections["methods_and_means"],
        sections["research_steps"],
    )
    _fill_section(table.rows[6].cells[0], sections["references"], references=True)

    # Keep handwritten signature and review regions together when they fit,
    # while allowing all preceding content to flow naturally across pages.
    for row_index, height_mm in {7: 22, 8: 88}.items():
        table.rows[row_index].height = Mm(height_mm)
        table.rows[row_index].height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        _prevent_row_split(table.rows[row_index])

    output.parent.mkdir(parents=True, exist_ok=True)
    document.core_properties.comments = (
        "Generated deterministically from proposal schema v0.2; "
        "signature and review fields intentionally remain blank."
    )
    document.save(output)

    reopened = Document(output)
    if len(reopened.tables) != 1 or len(reopened.tables[0].rows) != 9:
        raise RuntimeError("rendered DOCX failed structural reopening check")


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="proposal JSON data")
    parser.add_argument("--output", type=Path, required=True, help="output .docx path")
    parser.add_argument(
        "--template",
        type=Path,
        default=script_dir / "official-template.docx",
        help="official DOCX template",
    )
    parser.add_argument("--overwrite", action="store_true", help="replace an existing output")
    args = parser.parse_args()

    try:
        render(args.template, args.data, args.output, overwrite=args.overwrite)
    except (DataError, FileNotFoundError, FileExistsError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
