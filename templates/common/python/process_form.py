"""Shared layout contract and LaTeX bundle support for process-document forms."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .typography import load_document_layout


COMMON_DIR = Path(__file__).resolve().parents[1]
LATEX_SUPPORT_NAME = "sztu-process-form.tex"


def disable_word_numbering(paragraph) -> None:
    """Disable both direct and style-inherited numbering for explicit text labels."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    properties = paragraph._p.get_or_add_pPr()
    for old in list(properties.findall(qn("w:numPr"))):
        properties.remove(old)
    numbering = OxmlElement("w:numPr")
    identifier = OxmlElement("w:numId")
    identifier.set(qn("w:val"), "0")
    numbering.append(identifier)
    properties.append(numbering)

def set_word_cell_vertical_padding(cell, padding_mm: float) -> None:
    """Set only top/bottom insets, preserving the template's horizontal margins."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm

    properties = cell._tc.get_or_add_tcPr()
    margins = properties.find(qn("w:tcMar"))
    if margins is None:
        margins = OxmlElement("w:tcMar")
        properties.append(margins)
    for side in ("top", "bottom"):
        edge = margins.find(qn(f"w:{side}"))
        if edge is None:
            edge = OxmlElement(f"w:{side}")
            margins.append(edge)
        edge.set(qn("w:w"), str(Mm(padding_mm).twips))
        edge.set(qn("w:type"), "dxa")


_TABLE_NUMBER_TOKENS = (
    "border_pt",
    "horizontal_padding_mm",
    "top_bottom_padding_mm",
    "flow_vertical_padding_mm",
    "flow_end_space_mm",
    "section_title_content_gap_mm",
)
_PARAGRAPH_NUMBER_TOKENS = (
    "first_line_indent_em",
    "list_level_indent_em",
    "list_hanging_indent_em",
    "list_marker_gap_em",
)


def _require_nonnegative_number(container: dict[str, Any], key: str, path: str) -> float:
    value = container.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{path}.{key} must be a non-negative number")
    return float(value)


def load_process_document_layout(path: Path) -> dict[str, Any]:
    """Load one document layout and enforce the shared process-form contract."""

    layout = load_document_layout(path)
    table = layout.get("table")
    paragraphs = layout.get("paragraphs")
    if not isinstance(table, dict):
        raise ValueError("process-document layout must contain a table object")
    if not isinstance(paragraphs, dict):
        raise ValueError("process-document layout must contain a paragraphs object")
    for key in _TABLE_NUMBER_TOKENS:
        _require_nonnegative_number(table, key, "table")
    for key in _PARAGRAPH_NUMBER_TOKENS:
        _require_nonnegative_number(paragraphs, key, "paragraphs")
    max_depth = paragraphs.get("list_max_depth")
    if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth < 1:
        raise ValueError("paragraphs.list_max_depth must be a positive integer")
    markers = paragraphs.get("unordered_list_markers")
    if not isinstance(markers, list) or len(markers) < max_depth:
        raise ValueError(
            "paragraphs.unordered_list_markers must cover every supported list level"
        )
    return layout


def process_form_latex_tokens(layout: dict[str, Any]) -> list[str]:
    """Generate the shared LaTeX dimensions consumed by the common form skin."""

    table = layout["table"]
    padding = _require_nonnegative_number(
        table, "horizontal_padding_mm", "table"
    )
    return [
        rf"\newcommand{{\SZTUFormRuleWidth}}{{{float(table['border_pt']):g}pt}}",
        rf"\newcommand{{\SZTUCellHorizontalPadding}}{{{padding:g}mm}}",
        rf"\newcommand{{\SZTUCellHorizontalPaddingDouble}}{{{2 * padding:g}mm}}",
        rf"\newcommand{{\SZTUFixedVerticalPadding}}{{{float(table['top_bottom_padding_mm']):g}mm}}",
        rf"\newcommand{{\SZTUFlowVerticalPadding}}{{{float(table['flow_vertical_padding_mm']):g}mm}}",
        rf"\newcommand{{\SZTUFlowEndSpace}}{{{float(table['flow_end_space_mm']):g}mm}}",
        rf"\newcommand{{\SZTUSectionTitleContentGap}}{{{float(table['section_title_content_gap_mm']):g}mm}}",
    ]


def copy_process_form_latex_support(output_dir: Path) -> Path:
    """Copy the versioned common LaTeX form skin into a self-contained bundle."""

    source = COMMON_DIR / "latex" / LATEX_SUPPORT_NAME
    destination = output_dir / LATEX_SUPPORT_NAME
    shutil.copy2(source, destination)
    return destination
