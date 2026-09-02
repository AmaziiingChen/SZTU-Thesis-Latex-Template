#!/usr/bin/env python3
"""Render the SZTU task-book LaTeX bundle from the shared JSON input."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


TEMPLATES_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_DIR = TEMPLATES_DIR.parent
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

from common.python.content import (  # noqa: E402
    display_width,
    figure_caption_runs,
    starts_with_calendar_date,
)
from common.python.font_files import (  # noqa: E402
    cjk_emphasis_options,
    resolve_font_files,
    tex_font_parts,
)
from common.python.process_form import (  # noqa: E402
    copy_process_form_latex_support,
    load_process_document_layout,
    process_form_latex_tokens,
)


CJK_CHARACTER = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
CJK_TRAILING_PUNCTUATION = frozenset("，。；：！？、,.!?;:）)]】》〉」』”’…")
NUMBERED_PREFIX = re.compile(r"^\s*(?:[0-9]+|[一二三四五六七八九十]+)[、.．)]\s*")
LAYOUT = load_process_document_layout(
    Path(__file__).resolve().parents[1] / "spec" / "layout.json"
)
LIST_FIRST_LEVEL_INDENT_EM = LAYOUT["paragraphs"]["list_first_level_indent_em"]
LIST_LEVEL_INDENT_EM = LAYOUT["paragraphs"]["list_level_indent_em"]
LIST_MAX_DEPTH = LAYOUT["paragraphs"]["list_max_depth"]
UNORDERED_LIST_MARKERS = LAYOUT["paragraphs"]["unordered_list_markers"]


def _load_model(script_dir: Path):
    model_path = script_dir.parent / "python" / "model.py"
    spec = importlib.util.spec_from_file_location("task_book_model", model_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load shared task-book validator: {model_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "validate_data", None)):
        raise RuntimeError(f"validate_data(raw) is missing from {model_path}")
    return module


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def _first(data: dict[str, Any], paths: tuple[str, ...], default: Any) -> Any:
    for path in paths:
        value = _nested(data, path, None)
        if value is not None:
            return value
    return default


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "#": r"\#",
        "%": r"\%",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "\n": r"\\",
    }
    return "".join(replacements.get(character, character) for character in text)


def cover_label_tex(text: str) -> str:
    """Preserve the official cover label's deliberate half-em spacing."""
    return tex_escape(text).replace(" ", r"\hspace{0.5em}")


def _render_rich_run(run: dict[str, Any], text: str) -> str:
    value = tex_escape(text)
    # Keep numeric ranges intact.  A discretionary line break after an ASCII
    # hyphen can make plain-text extraction silently drop the range separator.
    value = re.sub(
        r"(?<=\d)-(?=\d)",
        lambda _match: r"\mbox{-}",
        value,
    )
    if run.get("script", "normal") == "sub":
        value = rf"\textsubscript{{{value}}}"
    elif run.get("script", "normal") == "super":
        value = rf"\textsuperscript{{{value}}}"
    if run.get("italic", False):
        value = rf"\textit{{{value}}}"
    if run.get("bold", False):
        value = rf"\textbf{{{value}}}"
    return value


def _cjk_widow_target(runs: list[dict[str, Any]]) -> tuple[int, int] | None:
    """Keep a final CJK glyph and trailing punctuation with its predecessor."""
    flat = "".join(run["text"] for run in runs)
    index = len(flat) - 1
    while index >= 0 and flat[index].isspace():
        index -= 1
    while index >= 0 and flat[index] in CJK_TRAILING_PUNCTUATION:
        index -= 1
    if (
        index <= 0
        or CJK_CHARACTER.fullmatch(flat[index]) is None
        or CJK_CHARACTER.fullmatch(flat[index - 1]) is None
    ):
        return None
    cursor = 0
    for run_index, run in enumerate(runs):
        next_cursor = cursor + len(run["text"])
        if cursor <= index < next_cursor:
            return run_index, index - cursor
        cursor = next_cursor
    raise AssertionError("CJK widow target escaped normalized runs")


def rich_runs(runs: list[dict[str, Any]]) -> str:
    rendered: list[str] = []
    widow_target = _cjk_widow_target(runs)
    for run_index, run in enumerate(runs):
        if widow_target is not None and run_index == widow_target[0]:
            split_at = widow_target[1]
            if split_at:
                rendered.append(_render_rich_run(run, run["text"][:split_at]))
            rendered.append(r"\nobreak{}")
            rendered.append(_render_rich_run(run, run["text"][split_at:]))
        else:
            rendered.append(_render_rich_run(run, run["text"]))
    return "".join(rendered)


def split_cover_title_runs(
    runs: list[dict[str, Any]], *, line_capacity: float
) -> list[list[dict[str, Any]]]:
    """Split the official cover title into one or two style-preserving lines."""

    if line_capacity <= 0:
        raise RuntimeError("cover title line capacity must be positive")
    lines: list[list[dict[str, Any]]] = [[]]
    line_width = 0.0
    for source_run in runs:
        for char in source_run["text"]:
            if char == "\n":
                if not lines[-1]:
                    continue
                if len(lines) == 2:
                    raise ValueError(
                        "metadata.title exceeds the official two-line cover capacity"
                    )
                lines.append([])
                line_width = 0.0
                continue
            width = display_width(char)
            if line_width + width > line_capacity and lines[-1]:
                if len(lines) == 2:
                    raise ValueError(
                        "metadata.title exceeds the official two-line cover capacity"
                    )
                lines.append([])
                line_width = 0.0
            if lines[-1] and all(
                lines[-1][-1].get(key) == source_run.get(key)
                for key in ("script", "italic", "bold")
            ):
                lines[-1][-1]["text"] += char
            else:
                copied = dict(source_run)
                copied["text"] = char
                lines[-1].append(copied)
            line_width += width
    if not lines[-1]:
        lines.pop()
    if not 1 <= len(lines) <= 2:
        raise ValueError("metadata.title must occupy one or two cover lines")
    return lines


def _safe_asset_name(source: Path) -> str:
    suffix = source.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".pdf"}:
        raise ValueError(f"LaTeX image must be PNG, JPEG, or PDF: {source}")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    stem = re.sub(r"[^a-zA-Z0-9-]+", "-", source.stem).strip("-") or "image"
    return f"{stem}-{digest}{suffix}"


def _resolve_image(path_text: str, data_dir: Path) -> Path:
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", path_text):
        raise ValueError("remote image URLs are forbidden; use a local file")
    source = Path(path_text).expanduser()
    if not source.is_absolute():
        source = data_dir / source
    source = source.resolve()
    if not source.is_file():
        raise ValueError(f"image file does not exist: {source}")
    return source


def render_blocks(
    blocks: list[dict[str, Any]],
    *,
    data_dir: Path,
    assets_dir: Path,
    paragraph_macro: str = "TaskBodyParagraph",
) -> str:
    rendered: list[str] = []
    for block in blocks:
        block_type = block["type"]
        if block_type == "paragraph":
            rendered.append(rf"\{paragraph_macro}{{{rich_runs(block['runs'])}}}")
        elif block_type in {"ordered_list", "unordered_list"}:
            rendered.append(render_list_block(block))
        elif block_type == "image":
            source = _resolve_image(block["path"], data_dir)
            asset_name = _safe_asset_name(source)
            assets_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, assets_dir / asset_name)
            caption_runs = block.get("caption_runs")
            caption = rich_runs(caption_runs) if caption_runs else ""
            rendered.append(
                rf"\TaskFigure{{assets/{tex_escape(asset_name)}}}"
                rf"{{{float(block['width_mm']):g}mm}}{{{caption}}}"
            )
        elif block_type == "data_table":
            rendered.append(render_data_table(block))
        elif block_type == "figure_group":
            rendered.append(
                render_figure_group(
                    block,
                    data_dir=data_dir,
                    assets_dir=assets_dir,
                )
            )
        else:
            raise AssertionError(f"unsupported normalized block: {block_type}")
    return "\n".join(rendered)


def render_data_table(block: dict[str, Any]) -> str:
    alignments = {"left": "l", "center": "c", "right": "r"}
    colspec = "".join(
        rf"X[{column['width_weight']:g},{alignments[column['alignment']]},m]"
        for column in block["columns"]
    )
    header = " & ".join(
        rf"\textbf{{{rich_runs(column['header_runs'])}}}"
        for column in block["columns"]
    )
    rows = [" & ".join(rich_runs(cell) for cell in row) for row in block["rows"]]
    row_break = r" \\" + "\n"
    body = row_break.join([header, *rows])
    caption = (
        rf"\par\vspace{{{float(LAYOUT['embedded_table']['caption_space_before_pt']):g}pt}}"
        rf"\BodyText{{{rich_runs(block['caption_runs'])}}}\par"
        if block["caption_runs"]
        else ""
    )
    border = float(LAYOUT["embedded_table"]["border_pt"])
    padding = float(LAYOUT["embedded_table"]["cell_padding_mm"])
    options = (
        f"width=\\linewidth,colspec={{{colspec}}},"
        f"columns={{colsep={padding:g}mm}},rows={{valign=m,rowsep={padding:g}mm}},"
        f"hlines={{{border:g}pt}},vlines={{{border:g}pt}}"
    )
    return (
        r"\par\noindent\begin{minipage}{\linewidth}\centering" "\n"
        rf"\begin{{tblr}}{{{options}}}" "\n"
        f"{body}{row_break}"
        r"\end{tblr}" "\n"
        f"{caption}"
        r"\end{minipage}\par"
    )


def render_figure_group(
    block: dict[str, Any],
    *,
    data_dir: Path,
    assets_dir: Path,
) -> str:
    count = len(block["items"])
    gap_fraction = float(LAYOUT["figure_group"]["column_gap_mm"]) / float(
        LAYOUT["figure_group"]["width_mm"]
    )
    width_fraction = (1.0 - gap_fraction * (count - 1)) / count
    items: list[str] = []
    for item in block["items"]:
        source = _resolve_image(item["path"], data_dir)
        asset_name = _safe_asset_name(source)
        assets_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, assets_dir / asset_name)
        subcaption = tex_escape(item["subfigure_label"])
        if item["caption_runs"]:
            subcaption += rich_runs(item["caption_runs"])
        items.append(
            rf"\begin{{minipage}}[t]{{{width_fraction:.4f}\linewidth}}"
            rf"\centering\includegraphics[width=\linewidth,height="
            rf"{float(LAYOUT['figure_group']['max_item_height_mm']):g}mm,keepaspectratio]"
            rf"{{assets/{tex_escape(asset_name)}}}\par"
            rf"\vspace{{2pt}}\BodyText{{{subcaption}}}\par\end{{minipage}}"
        )
    caption = rich_runs(figure_caption_runs(block))
    return (
        r"\par\noindent\begin{minipage}{\linewidth}\centering" "\n"
        + r"\hfill".join(items)
        + "\n"
        + rf"\vspace{{3pt}}\BodyText{{{caption}}}\par"
        + r"\end{minipage}\par"
    )


def _list_marker(block: dict[str, Any], item: dict[str, Any], index: int, depth: int) -> str:
    if block["type"] == "ordered_list":
        return item["marker"] or f"（{index}）"
    return UNORDERED_LIST_MARKERS[depth - 1]


def render_list_block(block: dict[str, Any], *, depth: int = 1) -> str:
    if not 1 <= depth <= LIST_MAX_DEPTH:
        raise AssertionError(f"normalized list depth escaped bounds: {depth}")
    marker_indent = LIST_FIRST_LEVEL_INDENT_EM + (depth - 1) * LIST_LEVEL_INDENT_EM
    rendered: list[str] = []
    for index, item in enumerate(block["items"], start=1):
        marker = tex_escape(_list_marker(block, item, index, depth))
        rendered.append(
            rf"\TaskListItem{{{marker_indent:g}}}{{{marker}}}{{{rich_runs(item['runs'])}}}"
        )
        if item["children"]:
            rendered.append(render_list_block(item["children"], depth=depth + 1))
    return "\n".join(rendered)


def render_schedule(items: list[dict[str, Any]]) -> str:
    rendered: list[str] = []
    for item in items:
        period = item["period"]
        content = rf"{tex_escape(period)}：{rich_runs(item['content'])}"
        macro = (
            "TaskScheduleDateParagraph"
            if starts_with_calendar_date(period)
            else "TaskBodyParagraph"
        )
        rendered.append(rf"\{macro}{{{content}}}")
    return "\n".join(rendered)


def render_references(items: list[list[dict[str, Any]]]) -> str:
    return "\n".join(rf"\TaskReference{{{rich_runs(item)}}}" for item in items)


def _notice_text(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("text", "content", "body"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    raise ValueError("each notice item must contain non-empty text")


def render_notice_items(items: list[Any]) -> str:
    rendered: list[str] = []
    for index, raw_item in enumerate(items, start=1):
        text = _notice_text(raw_item)
        marker = raw_item.get("marker") if isinstance(raw_item, dict) else None
        if isinstance(marker, str) and marker.strip():
            rendered.append(
                rf"\TaskNoticeItem{{{tex_escape(marker.strip())}}}{{{tex_escape(text)}}}"
            )
        elif NUMBERED_PREFIX.match(text):
            rendered.append(rf"\TaskNoticeParagraph{{{tex_escape(text)}}}")
        else:
            rendered.append(
                rf"\TaskNoticeItem{{{index}、}}{{{tex_escape(text)}}}"
            )
    return "\n".join(rendered)


def fonts_tex(fonts: dict[str, Path]) -> str:
    school_dir, school_name = tex_font_parts(fonts["STXingkai"])
    simhei_dir, simhei = tex_font_parts(fonts["SimHei"])
    simsun_dir, simsun = tex_font_parts(fonts["SimSun"])
    times_dir, times = tex_font_parts(fonts["Times New Roman"])
    times_bold_dir, times_bold = tex_font_parts(fonts["Times New Roman Bold"])
    times_italic_dir, times_italic = tex_font_parts(fonts["Times New Roman Italic"])
    times_bold_italic_dir, times_bold_italic = tex_font_parts(
        fonts["Times New Roman Bold Italic"]
    )
    if len({times_dir, times_bold_dir, times_italic_dir, times_bold_italic_dir}) != 1:
        raise ValueError("all Times New Roman style files must be in the same directory")
    school_options = cjk_emphasis_options(school_dir)
    simhei_options = cjk_emphasis_options(simhei_dir)
    simsun_options = cjk_emphasis_options(simsun_dir)
    return "\n".join(
        [
            "% Generated file. Exact official fonts; missing fonts are fatal.",
            rf"\setCJKmainfont[{simsun_options}]{{{simsun}}}",
            rf"\setCJKsansfont[{simhei_options}]{{{simhei}}}",
            rf"\newCJKfontfamily\schoolmark[{school_options}]{{{school_name}}}",
            rf"\newCJKfontfamily\heiti[{simhei_options}]{{{simhei}}}",
            rf"\newCJKfontfamily\heitiBold[{simhei_options}]{{{simhei}}}",
            rf"\newfontfamily\heitiLatin[{simhei_options}]{{{simhei}}}",
            rf"\newCJKfontfamily\songti[{simsun_options}]{{{simsun}}}",
            rf"\newCJKfontfamily\songtiBold[{simsun_options}]{{{simsun}}}",
            rf"\setmainfont[Path={{{times_dir}}},BoldFont={{{times_bold}}},ItalicFont={{{times_italic}}},BoldItalicFont={{{times_bold_italic}}}]{{{times}}}",
            "",
        ]
    )


def _style(layout: dict[str, Any], name: str) -> dict[str, Any]:
    typography = layout.get("typography", {})
    if name not in typography:
        raise ValueError(f"layout typography.{name} is required")
    return typography[name]


def typography_tex(layout: dict[str, Any]) -> str:
    page = layout["page"]
    cover = layout["cover"]
    table = layout["table"]
    paragraphs = layout["paragraphs"]
    heights = layout["section_min_heights_mm"]
    signature = layout["signature"]
    checkbox = layout["checkbox"]
    pagination = layout["latex_pagination"]
    notice = layout.get("notice", {})
    padding = float(table["horizontal_padding_mm"])
    table_width = float(table["width_mm"])
    right_inset = float(signature["right_inset_mm"])
    topic_size_pt = float(_style(layout, "topic_body")["size_pt"])
    topic_indent_mm = topic_size_pt * 5 * 25.4 / 72.0
    self_proposed_indent_mm = (
        topic_size_pt
        * float(signature.get("self_proposed_left_indent_em", 5.0))
        * 25.4
        / 72.0
    )
    topic_project_label_width = float(
        signature.get("topic_project_label_width_mm", 25.0)
    )
    topic_project_blank_width = (
        table_width
        - 2 * padding
        - topic_indent_mm
        - topic_project_label_width
        - right_inset
    )

    def paragraph_number(primary: str, fallback: str | None = None, default: float = 0.0) -> float:
        if primary in paragraphs:
            return float(paragraphs[primary])
        if fallback is not None and fallback in paragraphs:
            return float(paragraphs[fallback])
        return default

    def height(primary: str, fallback: str) -> float:
        if primary in heights:
            return float(heights[primary])
        if fallback in heights:
            return float(heights[fallback])
        raise ValueError(
            f"layout section_min_heights_mm requires {primary!r} or {fallback!r}"
        )

    topic_height = height("topic_information", "topic_information")
    college_height = height("college_leader_opinion", "college_opinion")
    styles = (
        "cover_number",
        "school_name",
        "document_title",
        "cohort",
        "cover_label",
        "cover_value",
        "cover_title_value",
        "notice_title",
        "notice_body",
        "section_title",
        "title_row_value",
        "body",
        "topic_body",
        "signature",
    )
    lines = ["% Generated file. Shared size map plus task-book layout tokens."]
    for name in styles:
        command = "SZTU" + "".join(part.title() for part in name.split("_")) + "Size"
        if name == "cover_title_value":
            style = dict(layout.get("typography", {}).get(name) or _style(layout, "cover_label"))
            style.update({"latex_zihao": "3", "bold": False})
        elif name == "title_row_value":
            style = dict(layout.get("typography", {}).get(name) or _style(layout, "section_title"))
            style.update({"latex_zihao": "-4", "bold": False})
        elif name in {"notice_body", "body"}:
            style = dict(_style(layout, name))
            style.update({"latex_zihao": "-4", "bold": False})
        else:
            style = _style(layout, name)
        weight = r"\bfseries" if style.get("bold", False) else r"\mdseries"
        lines.append(
            rf"\newcommand{{\{command}}}{{\zihao{{{style['latex_zihao']}}}}}"
        )
        style_command = command.removesuffix("Size") + "Style"
        lines.append(
            rf"\newcommand{{\{style_command}}}"
            rf"{{\zihao{{{style['latex_zihao']}}}{weight}}}"
        )
    lines.extend(
        [
            rf"\newcommand{{\SZTUPageTopMargin}}{{{float(page['top_margin_mm']):g}mm}}",
            rf"\newcommand{{\SZTUPageBottomMargin}}{{{float(page['bottom_margin_mm']):g}mm}}",
            rf"\newcommand{{\SZTUPageLeftMargin}}{{{float(page['left_margin_mm']):g}mm}}",
            rf"\newcommand{{\SZTUPageRightMargin}}{{{float(page['right_margin_mm']):g}mm}}",
            rf"\newcommand{{\SZTUCoverContentWidth}}{{{float(cover['content_width_mm']):g}mm}}",
            rf"\newcommand{{\SZTUCoverNumberTop}}{{{float(cover['number_top_mm']):g}mm}}",
            rf"\newcommand{{\SZTUSchoolNameTop}}{{{float(cover['school_name_top_mm']):g}mm}}",
            rf"\newcommand{{\SZTUDocumentTitleTop}}{{{float(cover['document_title_top_mm']):g}mm}}",
            rf"\newcommand{{\SZTUCohortTop}}{{{float(cover['cohort_top_mm']):g}mm}}",
            rf"\newcommand{{\SZTUTitleFieldTop}}{{{float(cover['title_field_top_mm']):g}mm}}",
            rf"\newcommand{{\SZTUMetadataRowOneTop}}{{{float(cover['metadata_rows_top_mm'][0]):g}mm}}",
            rf"\newcommand{{\SZTUMetadataRowTwoTop}}{{{float(cover['metadata_rows_top_mm'][1]):g}mm}}",
            rf"\newcommand{{\SZTUMetadataRowThreeTop}}{{{float(cover['metadata_rows_top_mm'][2]):g}mm}}",
            rf"\newcommand{{\SZTUMetadataRowFourTop}}{{{float(cover['metadata_rows_top_mm'][3]):g}mm}}",
            rf"\newcommand{{\SZTUMetadataColumnGap}}{{{float(cover['metadata_column_gap_mm']):g}mm}}",
            rf"\newcommand{{\SZTUShortFieldUnderlineWidth}}{{{float(cover['short_field_underline_width_mm']):g}mm}}",
            rf"\newcommand{{\SZTUShortFieldLabelWidth}}{{{(float(cover['content_width_mm']) - 2 * float(cover['short_field_underline_width_mm']) - float(cover['metadata_column_gap_mm'])) / 2:g}mm}}",
            rf"\newcommand{{\SZTUFullFieldUnderlineWidth}}{{{float(cover['full_field_underline_width_mm']):g}mm}}",
            rf"\newcommand{{\SZTUTitleUnderlineWidth}}{{{float(cover['title_underline_width_mm']):g}mm}}",
            rf"\newcommand{{\SZTUCoverUnderlineWidth}}{{{float(cover['underline_pt']):g}pt}}",
            rf"\newcommand{{\SZTUTitleSingleLineUnderlineOffset}}{{{float(cover['title_latex_single_line_rule_offset_mm']):g}mm}}",
            rf"\newcommand{{\SZTUTitleSingleLineSubscriptUnderlineOffset}}{{{float(cover['title_latex_single_line_subscript_rule_offset_mm']):g}mm}}",
            rf"\newcommand{{\SZTUTitleTwoLineUnderlineOffset}}{{{float(cover['title_latex_two_line_rule_offset_mm']):g}mm}}",
            rf"\newcommand{{\SZTUTitleTwoLineSubscriptUnderlineOffset}}{{{float(cover['title_latex_two_line_subscript_rule_offset_mm']):g}mm}}",
            rf"\newcommand{{\SZTUNoticeTitleTop}}{{{float(notice.get('title_top_mm', 42.45)):g}mm}}",
            rf"\newcommand{{\SZTUNoticeFirstItemTop}}{{{float(notice.get('first_item_top_mm', 71.05)):g}mm}}",
            rf"\newcommand{{\SZTUNoticeHangingIndent}}{{{(float(notice['hanging_chars_hundredth']) / 100 * 10.5) if 'hanging_chars_hundredth' in notice else (float(notice.get('hanging_indent_twip', 403)) / 20):g}pt}}",
            rf"\newcommand{{\SZTUNoticeItemGap}}{{{float(notice.get('item_space_after_pt', 0.0)):g}pt}}",
            rf"\newcommand{{\SZTUTableWidth}}{{{table_width:g}mm}}",
            *process_form_latex_tokens(layout),
            rf"\newcommand{{\SZTUBodyLineSpacing}}{{{float(paragraphs['body_line_spacing']):g}}}",
            rf"\newcommand{{\SZTUNoticeLineSpacing}}{{{float(paragraphs['notice_line_spacing']):g}}}",
            rf"\newcommand{{\SZTUFirstLineIndent}}{{{float(paragraphs['first_line_indent_em']):g}em}}",
            rf"\newcommand{{\SZTUListHangingIndent}}{{{paragraph_number('list_hanging_indent_em', default=2.0):g}em}}",
            rf"\newcommand{{\SZTUScheduleLabelWidth}}{{{paragraph_number('schedule_period_width_em', 'schedule_label_width_em', 11.0):g}em}}",
            rf"\newcommand{{\SZTUTitleRowMinHeight}}{{{height('title_row', 'title'):g}mm}}",
            rf"\newcommand{{\SZTUBasicMinHeight}}{{{height('basic_content_and_requirements', 'basic_content'):g}mm}}",
            rf"\newcommand{{\SZTUScheduleMinHeight}}{{{height('schedule', 'schedule'):g}mm}}",
            rf"\newcommand{{\SZTUMaterialsMinHeight}}{{{height('required_materials_and_references', 'materials_and_references'):g}mm}}",
            rf"\newcommand{{\SZTUTopicInfoHeight}}{{{float(pagination.get('topic_information_height_mm', topic_height)):g}mm}}",
            rf"\newcommand{{\SZTUCollegeOpinionHeight}}{{{max(float(pagination.get('college_leader_opinion_height_mm', college_height)), 66.2):g}mm}}",
            rf"\newcommand{{\SZTUSignatureRightInset}}{{{float(signature['right_inset_mm']):g}mm}}",
            rf"\newcommand{{\SZTUTeacherSignatureBlank}}{{{float(signature.get('teacher_blank_width_mm', signature.get('advisor_blank_width_mm'))):g}mm}}",
            rf"\newcommand{{\SZTUCollegeSignatureBlank}}{{{float(signature.get('college_leader_blank_width_mm', signature.get('college_blank_width_mm'))):g}mm}}",
            rf"\newcommand{{\SZTUTopicIndent}}{{{topic_indent_mm:g}mm}}",
            rf"\newcommand{{\SZTUSelfProposedIndent}}{{{self_proposed_indent_mm:g}mm}}",
            rf"\newcommand{{\SZTUTopicOtherBlank}}{{{float(signature.get('topic_other_blank_width_mm', 32.0)):g}mm}}",
            rf"\newcommand{{\SZTUTopicProjectLabelWidth}}{{{topic_project_label_width:g}mm}}",
            rf"\newcommand{{\SZTUTopicProjectBlank}}{{{topic_project_blank_width:g}mm}}",
            rf"\newcommand{{\SZTUTopicUnderlineGap}}{{{float(signature.get('topic_underline_gap_mm', 0.0)):g}mm}}",
            rf"\newcommand{{\SZTUCheckboxSize}}{{{float(checkbox.get('size_em', 0.72)):g}em}}",
            rf"\newcommand{{\SZTUCheckboxOutlineWidth}}{{{float(checkbox.get('outline_pt', 0.5)):g}pt}}",
            rf"\newcommand{{\SZTUCheckboxTickWidth}}{{{float(checkbox.get('tick_pt', 0.7)):g}pt}}",
            rf"\newcommand{{\SZTUDateYearBlank}}{{{float(signature.get('date_year_blank_width_mm', 12.7)):g}mm}}",
            rf"\newcommand{{\SZTUDateMonthBlank}}{{{float(signature.get('date_month_blank_width_mm', 6.35)):g}mm}}",
            rf"\newcommand{{\SZTUDateDayBlank}}{{{float(signature.get('date_day_blank_width_mm', 6.35)):g}mm}}",
            rf"\newcommand{{\SZTUDateLabelWidth}}{{{float(signature.get('date_label_width_mm', 5.0)):g}mm}}",
            "",
        ]
    )
    return "\n".join(lines)


def fixed_tex(fixed: dict[str, Any]) -> str:
    notice_items = _first(
        fixed,
        ("notice.items", "notice.paragraphs", "notices", "notice_items"),
        [],
    )
    if not isinstance(notice_items, list) or not notice_items:
        raise ValueError("fixed-content notice.items must be a non-empty array")

    labels = {
        "FixedSchoolName": _first(
            fixed, ("cover.school_name", "school_name"), "深圳技术大学"
        ),
        "FixedDocumentTitle": _first(
            fixed,
            ("cover.document_title", "cover.title", "document_title"),
            "本科毕业论文（设计）任务书",
        ),
        "FixedCoverNumberLabel": _first(
            fixed,
            ("cover.document_number_label", "cover.number_label"),
            "编号(学号)：",
        ),
        "FixedCoverTitleLabel": _first(
            fixed, ("cover.field_labels.title",), "题目："
        ),
        "FixedCoverCollegeLabel": _first(
            fixed, ("cover.field_labels.college",), "学    院："
        ),
        "FixedCoverMajorLabel": _first(
            fixed, ("cover.field_labels.major",), "专    业："
        ),
        "FixedCoverClassLabel": _first(
            fixed, ("cover.field_labels.class_name",), "班    级："
        ),
        "FixedCoverStudentIdLabel": _first(
            fixed, ("cover.field_labels.student_id",), "学    号："
        ),
        "FixedCoverStudentNameLabel": _first(
            fixed, ("cover.field_labels.student_name",), "学生姓名："
        ),
        "FixedCoverAdvisorLabel": _first(
            fixed, ("cover.field_labels.advisor",), "指导教师："
        ),
        "FixedNoticeTitle": _first(
            fixed, ("notice.title", "notice_title"), "本科生毕业论文（设计）须知"
        ),
        "FixedTitleRowLabel": _first(
            fixed,
            ("body.section_labels.title",),
            "题目名称：",
        ),
        "FixedBasicSectionTitle": _first(
            fixed,
            ("body.section_labels.basic_content_and_requirements",),
            "一、毕业论文(设计)基本内容与要求：",
        ),
        "FixedScheduleSectionTitle": _first(
            fixed, ("body.section_labels.schedule",), "二、进度安排："
        ),
        "FixedMaterialsSectionTitle": _first(
            fixed,
            ("body.section_labels.required_materials_and_references",),
            "三、需收集的资料和指导性参考文献：",
        ),
        "FixedTopicSectionTitle": _first(
            fixed, ("body.section_labels.topic_information",), "四、选题信息："
        ),
        "FixedTopicNatureLabel": _first(
            fixed, ("body.topic_information.nature_label",), "选题性质："
        ),
        "FixedTopicSourceLabel": _first(
            fixed, ("body.topic_information.source_label",), "选题来源："
        ),
        "FixedNatureDesignLabel": _first(
            fixed,
            ("body.topic_information.nature_options.graduation_design",),
            "毕业设计",
        ),
        "FixedNatureThesisLabel": _first(
            fixed,
            ("body.topic_information.nature_options.graduation_thesis",),
            "毕业论文",
        ),
        "FixedResearchProjectLabel": _first(
            fixed,
            ("body.topic_information.source_options.research_project",),
            "1. 科研项目",
        ),
        "FixedPracticeProjectLabel": _first(
            fixed,
            ("body.topic_information.source_options.practice_project",),
            "2. 实践项目",
        ),
        "FixedSelfProposedLabel": _first(
            fixed,
            ("body.topic_information.source_options.self_proposed",),
            "3. 自拟题目",
        ),
        "FixedNationalLabel": _first(
            fixed,
            ("body.topic_information.research_project_levels.national",),
            "国家级",
        ),
        "FixedProvincialLabel": _first(
            fixed,
            ("body.topic_information.research_project_levels.provincial_ministerial",),
            "省部级",
        ),
        "FixedOtherLevelLabel": _first(
            fixed,
            ("body.topic_information.research_project_levels.other",),
            "其他：",
        ),
        "FixedProjectNumberLabel": _first(
            fixed,
            ("body.topic_information.project_number_label",),
            "项目编号：",
        ),
        "FixedTeacherProposedLabel": _first(
            fixed,
            ("body.topic_information.self_proposed_by_options.teacher",),
            "教师自拟",
        ),
        "FixedStudentProposedLabel": _first(
            fixed,
            ("body.topic_information.self_proposed_by_options.student",),
            "学生自拟",
        ),
        "FixedJointProposedLabel": _first(
            fixed,
            ("body.topic_information.self_proposed_by_options.teacher_student_joint",),
            "师生共拟",
        ),
        "FixedTeacherSignatureLabel": _first(
            fixed, ("body.signature_labels.advisor",), "指导教师签名："
        ),
        "FixedCollegeOpinionLabel": _first(
            fixed,
            ("body.signature_labels.college_opinion",),
            "学院领导意见：",
        ),
        "FixedCollegeSignatureLabel": _first(
            fixed, ("body.signature_labels.college_leader",), "签名："
        ),
    }
    cohort_format = _first(fixed, ("cover.cohort_format",), "（{graduation_year}届）")
    if not isinstance(cohort_format, str) or cohort_format.count("{graduation_year}") != 1:
        raise ValueError("fixed-content cover.cohort_format must contain {graduation_year} once")
    # The revised official task-book shortens these two printed choices.  Keep
    # the enum names in JSON unchanged; only their fixed display wording changes.
    labels["FixedNatureDesignLabel"] = "设计"
    labels["FixedNatureThesisLabel"] = "论文"

    lines = ["% Generated file. Fixed official wording comes from spec/fixed-content.json."]
    cover_field_labels = {
        "FixedCoverTitleLabel",
        "FixedCoverCollegeLabel",
        "FixedCoverMajorLabel",
        "FixedCoverClassLabel",
        "FixedCoverStudentIdLabel",
        "FixedCoverStudentNameLabel",
        "FixedCoverAdvisorLabel",
    }
    for name, value in labels.items():
        escaped = (
            cover_label_tex(str(value))
            if name in cover_field_labels
            else tex_escape(str(value))
        )
        lines.append(rf"\long\def\{name}{{{escaped}}}")
    before_year, after_year = cohort_format.split("{graduation_year}")
    lines.append(
        rf"\long\def\FixedCohortText{{{tex_escape(before_year)}{{\GraduationYear}}{tex_escape(after_year)}}}"
    )
    lines.append(
        rf"\long\def\FixedNoticeItems{{{render_notice_items(notice_items)}}}"
    )
    return "\n".join(lines) + "\n"


def _box(selected: bool) -> str:
    return r"\CheckedBox{}" if selected else r"\EmptyBox{}"


def topic_tex(topic: dict[str, Any]) -> dict[str, str]:
    nature = topic["nature"]
    source = topic["source"]
    source_type = source["type"]
    research = source.get("research_project") or {}
    level = research.get("level")
    proposed_by = source.get("self_proposed_by")
    other_level = tex_escape(research.get("other_level") or "")
    project_number = tex_escape(research.get("project_number") or "")
    return {
        "NatureDesignBox": _box(nature == "graduation_design"),
        "NatureThesisBox": _box(nature == "graduation_thesis"),
        "PracticeProjectBox": _box(source_type == "practice_project"),
        "NationalProjectBox": _box(source_type == "research_project" and level == "national"),
        "ProvincialProjectBox": _box(
            source_type == "research_project" and level == "provincial_ministerial"
        ),
        "TeacherProposedBox": _box(source_type == "self_proposed" and proposed_by == "teacher"),
        "StudentProposedBox": _box(source_type == "self_proposed" and proposed_by == "student"),
        "JointProposedBox": _box(
            source_type == "self_proposed" and proposed_by == "teacher_student_joint"
        ),
        "OtherProjectLevel": other_level,
        "ProjectNumber": project_number,
    }


def data_tex(
    data: dict[str, Any],
    *,
    data_dir: Path,
    assets_dir: Path,
    cover_title_lines: list[list[dict[str, Any]]],
) -> str:
    metadata = data["metadata"]
    sections = data["sections"]
    student_id_breakable = r"\allowbreak{}".join(
        tex_escape(character) for character in metadata["student_id"]
    )
    macros = {
        "GraduationYear": tex_escape(str(metadata["graduation_year"])),
        "TaskTitle": rich_runs(metadata["title"]),
        "TaskCoverTitleLineCount": str(len(cover_title_lines)),
        "TaskCoverTitleLineOneHasSubscript": str(
            int(any(run.get("script") == "sub" for run in cover_title_lines[0]))
        ),
        "TaskCoverTitleLineTwoHasSubscript": str(
            int(
                len(cover_title_lines) == 2
                and any(run.get("script") == "sub" for run in cover_title_lines[1])
            )
        ),
        "TaskCoverTitleLineOne": rich_runs(cover_title_lines[0]),
        "TaskCoverTitleLineTwo": (
            rich_runs(cover_title_lines[1]) if len(cover_title_lines) == 2 else ""
        ),
        "StudentName": tex_escape(metadata["student_name"]),
        "StudentId": tex_escape(metadata["student_id"]),
        "StudentIdBreakable": student_id_breakable,
        "College": tex_escape(metadata["college"]),
        "Major": tex_escape(metadata["major"]),
        "ClassName": tex_escape(metadata["class_name"]),
        "Advisor": tex_escape(metadata["advisor"]),
        "BasicContent": render_blocks(
            sections["basic_content_and_requirements"],
            data_dir=data_dir,
            assets_dir=assets_dir,
        ),
        "ScheduleContent": render_schedule(sections["schedule"]),
        "RequiredMaterialsContent": render_blocks(
            sections["required_materials"],
            data_dir=data_dir,
            assets_dir=assets_dir,
        ),
        "RequiredMaterialsReferenceGap": (
            r"\vspace{1mm}" if sections["required_materials"] else ""
        ),
        "ReferencesContent": render_references(sections["references"]),
    }
    macros.update(topic_tex(sections["topic_information"]))
    lines = ["% Generated file. Edit the JSON source, not this file."]
    lines.extend(rf"\long\def\{name}{{{value}}}" for name, value in macros.items())
    return "\n".join(lines) + "\n"


REQUIRED_FONT_KEYS = [
    "STXingkai",
    "SimHei",
    "SimSun",
    "Times New Roman",
    "Times New Roman Bold",
    "Times New Roman Italic",
    "Times New Roman Bold Italic",
]


def render(
    data_path: Path,
    output_dir: Path,
    *,
    overwrite: bool,
    compile_pdf: bool,
) -> Path:
    script_dir = Path(__file__).resolve().parent
    model = _load_model(script_dir)
    data = model.validate_data(json.loads(data_path.read_text(encoding="utf-8")))
    layout = load_process_document_layout(script_dir.parent / "spec" / "layout.json")
    fixed = _read_object(script_dir.parent / "spec" / "fixed-content.json")
    cover = layout["cover"]
    cover_title_style = _style(layout, "cover_title_value")
    cover_title_em_mm = float(cover_title_style["size_pt"]) * 25.4 / 72.0
    cover_title_lines = split_cover_title_runs(
        data["metadata"]["title"],
        line_capacity=float(
            cover.get(
                "title_line_capacity_units",
                float(cover["title_underline_width_mm"]) / cover_title_em_mm,
            )
        ),
    )
    fonts = resolve_font_files(
        REQUIRED_FONT_KEYS,
        local_font_dir=REPOSITORY_DIR,
    )

    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(
            f"output directory is not empty; pass --overwrite: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    (output_dir / "task-book-data.tex").write_text(
        data_tex(
            data,
            data_dir=data_path.resolve().parent,
            assets_dir=assets_dir,
            cover_title_lines=cover_title_lines,
        ),
        encoding="utf-8",
    )
    (output_dir / "task-book-fixed.tex").write_text(
        fixed_tex(fixed), encoding="utf-8"
    )
    (output_dir / "task-book-fonts.tex").write_text(
        fonts_tex(fonts), encoding="utf-8"
    )
    (output_dir / "task-book-typography.tex").write_text(
        typography_tex(layout), encoding="utf-8"
    )
    copy_process_form_latex_support(output_dir)
    shutil.copy2(script_dir / "main.tex", output_dir / "main.tex")

    if compile_pdf:
        command = ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"]
        for _ in range(2):
            subprocess.run(command, cwd=output_dir, check=True)
    return output_dir / ("main.pdf" if compile_pdf else "main.tex")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--compile", action="store_true", dest="compile_pdf")
    parser.add_argument("--check-fonts", action="store_true")
    args = parser.parse_args()
    try:
        if args.check_fonts:
            script_dir = Path(__file__).resolve().parent
            fonts = resolve_font_files(
                REQUIRED_FONT_KEYS,
                local_font_dir=REPOSITORY_DIR,
            )
            for family, path in fonts.items():
                print(f"{family}: {path}")
            return 0
        if args.data is None or args.output_dir is None:
            parser.error("--data and --output-dir are required unless --check-fonts is used")
        output = render(
            args.data,
            args.output_dir,
            overwrite=args.overwrite,
            compile_pdf=args.compile_pdf,
        )
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
