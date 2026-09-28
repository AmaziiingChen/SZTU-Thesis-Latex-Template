#!/usr/bin/env python3
"""Render the SZTU midterm LaTeX bundle from the shared JSON input."""

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

TEMPLATES_DIR = Path(__file__).resolve().parents[2]
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

from common.python.font_files import (  # noqa: E402
    cjk_emphasis_options,
    resolve_font_files,
    tex_font_parts,
)
from common.python.content import figure_caption_runs, resolve_list_marker, runs_text  # noqa: E402
from common.python.equation import latex_display, latex_math  # noqa: E402
from common.python.process_form import (  # noqa: E402
    copy_process_form_latex_support,
    load_process_document_layout,
    process_form_latex_tokens,
)


CJK_CHARACTER = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
CJK_TRAILING_PUNCTUATION = frozenset("，。；：！？、,.!?;:）)]】》〉」』”’…")
LAYOUT = load_process_document_layout(
    Path(__file__).resolve().parents[1] / "spec" / "layout.json"
)
LIST_MAX_DEPTH = LAYOUT["paragraphs"]["list_max_depth"]
UNORDERED_LIST_MARKERS = LAYOUT["paragraphs"]["unordered_list_markers"]


def _load_word_renderer(script_dir: Path):
    renderer_path = script_dir.parent / "word" / "render.py"
    spec = importlib.util.spec_from_file_location("midterm_word_renderer", renderer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load shared validator: {renderer_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fonts_tex(fonts: dict[str, Path]) -> str:
    form_title_dir, form_title = tex_font_parts(fonts["FZXiaoBiaoSong"])
    simsun_dir, simsun = tex_font_parts(fonts["SimSun"])
    times_dir, times = tex_font_parts(fonts["Times New Roman"])
    times_bold_dir, times_bold = tex_font_parts(fonts["Times New Roman Bold"])
    times_italic_dir, times_italic = tex_font_parts(fonts["Times New Roman Italic"])
    times_bold_italic_dir, times_bold_italic = tex_font_parts(
        fonts["Times New Roman Bold Italic"]
    )
    if len({times_dir, times_bold_dir, times_italic_dir, times_bold_italic_dir}) != 1:
        raise ValueError("all Times New Roman style files must be in the same directory")
    simsun_options = cjk_emphasis_options(simsun_dir)
    return "\n".join(
        [
            "% Generated file. Exact official fonts; missing fonts are fatal.",
            rf"\setCJKmainfont[{simsun_options}]{{{simsun}}}",
            rf"\newCJKfontfamily\songti[{simsun_options}]{{{simsun}}}",
            rf"\newCJKfontfamily\songtiBold[{simsun_options}]{{{simsun}}}",
            rf"\newCJKfontfamily\formtitle[Path={{{form_title_dir}}}]{{{form_title}}}",
            rf"\setmainfont[Path={{{times_dir}}},BoldFont={{{times_bold}}},ItalicFont={{{times_italic}}},BoldItalicFont={{{times_bold_italic}}}]{{{times}}}",
            "",
        ]
    )


def typography_tex(layout: dict) -> str:
    typography = layout["typography"]
    paragraphs = layout["paragraphs"]
    page = layout["page"]
    table = layout["table"]
    signature = layout["signature"]
    row_heights = layout["row_min_heights_mm"]
    section_heights = layout["section_min_heights_mm"]
    latex_pagination = layout["latex_pagination"]
    image = layout["image"]
    padding = float(table["horizontal_padding_mm"])
    columns = table["column_widths_mm"]
    rule_mm = float(table["border_pt"]) * 25.4 / 72.27
    column_rule_share_mm = 5 * rule_mm / 4
    title_content_min_height = float(table["title_row_content_min_height_mm"])
    if abs(
        title_content_min_height
        + 2 * float(table["title_vertical_padding_mm"])
        - float(row_heights["metadata"])
    ) > 0.01:
        raise ValueError("title row content height and padding must equal the metadata row minimum")
    return "\n".join(
        [
            "% Generated file. Shared size map plus midterm-specific layout tokens.",
            rf"\newcommand{{\SZTUTitleSize}}{{\zihao{{{typography['title']['latex_zihao']}}}}}",
            rf"\newcommand{{\SZTULabelSize}}{{\zihao{{{typography['label']['latex_zihao']}}}}}",
            rf"\newcommand{{\SZTUDataSize}}{{\zihao{{{typography['data']['latex_zihao']}}}}}",
            rf"\newcommand{{\SZTUBodySize}}{{\zihao{{{typography['body']['latex_zihao']}}}}}",
            rf"\newcommand{{\SZTUTeacherHeaderSize}}{{\zihao{{{typography['teacher_header']['latex_zihao']}}}}}",
            rf"\newcommand{{\SZTUTeacherBodySize}}{{\zihao{{{typography['teacher_body']['latex_zihao']}}}}}",
            rf"\newcommand{{\SZTUSignatureSize}}{{\zihao{{{typography['signature']['latex_zihao']}}}}}",
            rf"\newcommand{{\SZTUPageTopMargin}}{{{page['top_margin_mm']:g}mm}}",
            rf"\newcommand{{\SZTUPageBottomMargin}}{{{page['bottom_margin_mm']:g}mm}}",
            rf"\newcommand{{\SZTUPageLeftMargin}}{{{page['left_margin_mm']:g}mm}}",
            rf"\newcommand{{\SZTUPageRightMargin}}{{{page['right_margin_mm']:g}mm}}",
            rf"\newcommand{{\SZTUTableWidth}}{{{table['width_mm']:g}mm}}",
            rf"\newcommand{{\SZTUColOne}}{{{columns[0]:g}mm}}",
            rf"\newcommand{{\SZTUColTwo}}{{{columns[1]:g}mm}}",
            rf"\newcommand{{\SZTUColThree}}{{{columns[2]:g}mm}}",
            rf"\newcommand{{\SZTUColFour}}{{{columns[3]:g}mm}}",
            rf"\newcommand{{\SZTUColOneContent}}{{{columns[0] - 2 * padding - column_rule_share_mm:g}mm}}",
            rf"\newcommand{{\SZTUColTwoContent}}{{{columns[1] - 2 * padding - column_rule_share_mm:g}mm}}",
            rf"\newcommand{{\SZTUColThreeContent}}{{{columns[2] - 2 * padding - column_rule_share_mm:g}mm}}",
            rf"\newcommand{{\SZTUColFourContent}}{{{columns[3] - 2 * padding - column_rule_share_mm:g}mm}}",
            rf"\newcommand{{\SZTUTableContentWidth}}{{{table['width_mm'] - 2 * padding - 2 * rule_mm - 0.001:g}mm}}",
            rf"\newcommand{{\SZTUTitleContentWidth}}{{{sum(columns[1:]) - 2 * padding - 2 * rule_mm:g}mm}}",
            rf"\newcommand{{\SZTUTitleVerticalPadding}}{{{table['title_vertical_padding_mm']:g}mm}}",
            rf"\newcommand{{\SZTUTitleContentMinHeight}}{{{title_content_min_height:g}mm}}",
            *process_form_latex_tokens(layout),
            rf"\newcommand{{\SZTUResearchHeadingGap}}{{{paragraphs['research_heading_space_before_pt']:g}pt}}",
            rf"\newcommand{{\SZTUFirstLineIndent}}{{{paragraphs['first_line_indent_em']:g}em}}",
            rf"\newcommand{{\SZTUOutlineLevelIndent}}{{{paragraphs['outline_level_indent_em']:g}em}}",
            rf"\newcommand{{\SZTUOutlineHangingIndent}}{{{paragraphs['outline_hanging_indent_em']:g}em}}",
            rf"\newcommand{{\SZTUListLevelIndent}}{{{paragraphs['list_level_indent_em']:g}em}}",
            rf"\newcommand{{\SZTUListHangingIndent}}{{{paragraphs['list_hanging_indent_em']:g}em}}",
            rf"\newcommand{{\SZTUListMarkerGap}}{{{paragraphs['list_marker_gap_em']:g}em}}",
            rf"\newcommand{{\SZTUMetadataRowHeight}}{{{row_heights['metadata']:g}mm}}",
            rf"\newcommand{{\SZTUTeacherHeaderHeight}}{{{row_heights['teacher_header']:g}mm}}",
            rf"\newcommand{{\SZTUTeacherFirstHeight}}{{{row_heights['teacher_option_first']:g}mm}}",
            rf"\newcommand{{\SZTUTeacherRowHeight}}{{{row_heights['teacher_option']:g}mm}}",
            rf"\newcommand{{\SZTUProgressMinHeight}}{{{section_heights['progress']:g}mm}}",
            rf"\newcommand{{\SZTUTeacherOpinionHeight}}{{{latex_pagination['teacher_opinion_height_mm']:g}mm}}",
            rf"\newcommand{{\SZTUReviewOpinionHeight}}{{{latex_pagination['review_group_opinion_height_mm']:g}mm}}",
            rf"\newcommand{{\SZTUSignatureRightInset}}{{{signature['right_inset_mm']:g}mm}}",
            rf"\newcommand{{\SZTUTeacherSignatureBlank}}{{{signature['teacher_blank_width_mm']:g}mm}}",
            rf"\newcommand{{\SZTUReviewSignatureBlank}}{{{signature['review_blank_width_mm']:g}mm}}",
            rf"\newcommand{{\SZTUImageMaxHeight}}{{{image['max_height_mm']:g}mm}}",
            "",
        ]
    )


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
    }
    return "".join(replacements.get(char, char) for char in text)


def _render_rich_run(run: dict, text: str) -> str:
    value = tex_escape(text)
    if run["script"] == "sub":
        value = rf"\textsubscript{{{value}}}"
    elif run["script"] == "super":
        value = rf"\textsuperscript{{{value}}}"
    if run["italic"]:
        value = rf"\textit{{{value}}}"
    if run["bold"]:
        value = rf"\textbf{{{value}}}"
    return value


def _cjk_widow_target(runs: list[dict]) -> tuple[int, int] | None:
    """Locate the final CJK glyph when it should stay with its preceding glyph."""
    flat = "".join(run.get("text", "\uFFFC") for run in runs)
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
        next_cursor = cursor + len(run.get("text", "\uFFFC"))
        if cursor <= index < next_cursor:
            return run_index, index - cursor
        cursor = next_cursor
    raise AssertionError("CJK widow target escaped normalized runs")


def rich_runs(runs: list[dict]) -> str:
    rendered = []
    widow_target = _cjk_widow_target(runs)
    for run_index, run in enumerate(runs):
        if run.get("type") == "inline_equation":
            rendered.append(f"${latex_math(run['expression'])}$")
            continue
        if widow_target is not None and run_index == widow_target[0]:
            split_at = widow_target[1]
            if split_at:
                rendered.append(_render_rich_run(run, run["text"][:split_at]))
            rendered.append(r"\nobreak{}")
            rendered.append(_render_rich_run(run, run["text"][split_at:]))
            continue
        value = _render_rich_run(run, run["text"])
        rendered.append(value)
    return "".join(rendered)


def _safe_asset_name(source: Path) -> str:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    suffix = source.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".pdf"}:
        raise ValueError(f"LaTeX image must be PNG, JPEG, or PDF: {source}")
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
    blocks: list[dict],
    *,
    data_dir: Path,
    assets_dir: Path,
) -> str:
    rendered = []
    for block in blocks:
        if block["type"] == "paragraph":
            rendered.append(rf"\MidtermParagraph{{{rich_runs(block['runs'])}}}")
        elif block["type"] in {"ordered_list", "unordered_list"}:
            rendered.append(render_list_block(block))
        elif block["type"] == "image":
            source = _resolve_image(block["path"], data_dir)
            asset_name = _safe_asset_name(source)
            assets_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, assets_dir / asset_name)
            caption = rich_runs(figure_caption_runs(block))
            rendered.append(
                rf"\MidtermFigure{{assets/{tex_escape(asset_name)}}}"
                rf"{{{block['width_mm']:g}mm}}{{{caption}}}"
            )
        elif block["type"] == "data_table":
            rendered.append(render_data_table(block))
        elif block["type"] == "figure_group":
            rendered.append(
                render_figure_group(
                    block,
                    data_dir=data_dir,
                    assets_dir=assets_dir,
                )
            )
        elif block["type"] == "equation":
            rendered.append(render_equation(block))
        else:
            raise AssertionError(f"unsupported normalized block: {block['type']}")
    return "\n".join(rendered)


def render_equation(block: dict) -> str:
    config = LAYOUT["equation"]
    return (
        rf"\par\vspace{{{config['space_before_pt']:g}pt}}"
        f"{latex_display(block['expression'], block.get('equation_label'))}"
        rf"\vspace{{{config['space_after_pt']:g}pt}}\par"
    )


def render_data_table(block: dict) -> str:
    fragment_size = int(LAYOUT["embedded_table"]["rows_per_fragment"])
    if len(block["rows"]) > fragment_size:
        separator = rf"\par\vspace{{{LAYOUT['embedded_table']['fragment_gap_pt']:g}pt}}" + "\n"
        return separator.join(
            render_data_table({
                **block,
                "rows": block["rows"][start:start + fragment_size],
                "caption_runs": block["caption_runs"] if start + fragment_size >= len(block["rows"]) else None,
            })
            for start in range(0, len(block["rows"]), fragment_size)
        )
    alignments = {"left": "l", "center": "c", "right": "r"}
    colspec = "".join(
        rf"X[{column['width_weight']:g},{alignments[column['alignment']]},m]"
        for column in block["columns"]
    )
    header = " & ".join(
        rf"\textbf{{{rich_runs(column['header_runs'])}}}"
        for column in block["columns"]
    )
    rows = [
        " & ".join(rich_runs(cell) for cell in row)
        for row in block["rows"]
    ]
    row_break = r" \\" + "\n"
    body = row_break.join([header, *rows])
    caption = (
        rf"\par\vspace{{3pt}}\Body{{{rich_runs(block['caption_runs'])}}}\par"
        if block["caption_runs"]
        else ""
    )
    border = float(LAYOUT["embedded_table"]["border_pt"])
    rules = (f"hline{{1,2,Z}}={{{border:g}pt}}" if block.get("style", "grid") == "three_line" else f"hlines={{{border:g}pt}},vlines={{{border:g}pt}}")
    options = (
        f"width=\\linewidth,colspec={{{colspec}}},"
        "columns={colsep=1.2mm},rows={valign=m,rowsep=1.2mm},"
        + rules
    )
    return (
        r"\par\noindent\begin{minipage}{\linewidth}\centering" "\n"
        rf"\begin{{tblr}}{{{options}}}"
        "\n"
        f"{body}{row_break}"
        r"\end{tblr}" "\n"
        f"{caption}"
        r"\end{minipage}\par"
    )


def render_figure_group(
    block: dict,
    *,
    data_dir: Path,
    assets_dir: Path,
) -> str:
    count = len(block["items"])
    columns = min(block.get("columns", count), count)
    width_fraction = (1.0 - 0.025 * (columns - 1)) / columns
    items = []
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
            rf"{LAYOUT['figure_group']['max_item_height_mm']:g}mm,keepaspectratio]"
            rf"{{assets/{tex_escape(asset_name)}}}\par"
            rf"\vspace{{2pt}}\Body{{{subcaption}}}\par\end{{minipage}}"
        )
    caption = rich_runs(figure_caption_runs(block))
    rows = []
    for start in range(0, count, columns):
        last_row = start + columns >= count
        rows.append(
            r"\par\noindent\begin{minipage}{\linewidth}\centering" + "\n"
            + r"\hfill".join(items[start:start + columns])
            + (rf"\par\vspace{{3pt}}\Body{{{caption}}}\par" if last_row else "")
            + r"\end{minipage}\par"
        )
    return (rf"\vspace{{{LAYOUT['figure_group']['row_gap_mm']:g}mm}}" + "\n").join(rows)


def render_list_block(block: dict, *, depth: int = 1) -> str:
    if not 1 <= depth <= LIST_MAX_DEPTH:
        raise AssertionError(f"normalized list depth escaped bounds: {depth}")
    rendered = []
    for index, item in enumerate(block["items"], start=1):
        marker = tex_escape(
            resolve_list_marker(
                block["type"], item["marker"], index, depth, UNORDERED_LIST_MARKERS
            )
        )
        rendered.append(
            rf"\MidtermListItem{{{depth}}}{{{marker}}}{{{rich_runs(item['runs'])}}}"
        )
        if item["children"]:
            rendered.append(render_list_block(item["children"], depth=depth + 1))
    return "\n".join(rendered)


def render_directory(items: list[dict]) -> str:
    rows = []
    for item in items:
        number = tex_escape(item["number"] + " ") if item["number"] else ""
        rows.append(
            rf"\MidtermOutlineItem{{{item['level']}}}{{{number}}}"
            rf"{{{rich_runs(item['title'])}}}"
        )
    return "\n".join(rows)


def data_tex(data: dict, *, data_dir: Path, assets_dir: Path) -> str:
    metadata = data["metadata"]
    sections = data["sections"]
    research_blocks = sections["main_research_content"]
    progress_blocks = sections["progress"]
    research_heading = r"\MidtermParagraph{主要研究内容：}"
    progress_heading = r"\Label{毕业论文（设计）工作进展情况（详述）：}\par"
    if sections["editable_headings"]:
        research_heading = ""
        progress_heading = ""
        if research_blocks[0]["type"] == "paragraph" and runs_text(research_blocks[0]["runs"]).strip().endswith(("：", ":")):
            research_heading = rf"\MidtermParagraph{{{rich_runs(research_blocks[0]['runs'])}}}"
            research_blocks = research_blocks[1:]
        if progress_blocks[0]["type"] == "paragraph" and runs_text(progress_blocks[0]["runs"]).strip().endswith(("：", ":")):
            progress_heading = rf"\Label{{{rich_runs(progress_blocks[0]['runs'])}}}\par"
            progress_blocks = progress_blocks[1:]
    year, month, day = (int(part) for part in metadata["check_date"].split("-"))
    macros = {
        "StudentName": tex_escape(metadata["student_name"]),
        "College": tex_escape(metadata["college"]),
        "Major": tex_escape(metadata["major"]),
        "ClassName": tex_escape(metadata["class_name"]),
        "Advisor": tex_escape(metadata["advisor"]),
        "CheckDate": f"{year} 年 {month} 月 {day} 日",
        "ThesisTitle": rich_runs(metadata["title"]),
        "DirectoryContent": render_directory(sections["directory"]),
        "ResearchHeading": research_heading,
        "ResearchContent": render_blocks(
            research_blocks,
            data_dir=data_dir,
            assets_dir=assets_dir,
        ),
        "ProgressHeading": progress_heading,
        "ProgressContent": render_blocks(
            progress_blocks,
            data_dir=data_dir,
            assets_dir=assets_dir,
        ),
    }
    lines = ["% Generated file. Edit the JSON source, not this file."]
    lines.extend(f"\\long\\def\\{name}{{{value}}}" for name, value in macros.items())
    return "\n".join(lines) + "\n"


def render(data_path: Path, output_dir: Path, *, overwrite: bool, compile_pdf: bool) -> Path:
    script_dir = Path(__file__).resolve().parent
    shared = _load_word_renderer(script_dir)
    data = shared.validate_data(json.loads(data_path.read_text(encoding="utf-8")))
    layout = load_process_document_layout(script_dir.parent / "spec" / "layout.json")
    fonts = resolve_font_files(
        layout["required_font_files"],
        local_font_dir=script_dir.parent / "fonts.local",
    )
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"output directory is not empty; pass --overwrite: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    (output_dir / "midterm-data.tex").write_text(
        data_tex(data, data_dir=data_path.resolve().parent, assets_dir=assets_dir),
        encoding="utf-8",
    )
    (output_dir / "midterm-fonts.tex").write_text(fonts_tex(fonts), encoding="utf-8")
    (output_dir / "midterm-typography.tex").write_text(
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
            layout = load_process_document_layout(
                script_dir.parent / "spec" / "layout.json"
            )
            fonts = resolve_font_files(
                layout["required_font_files"],
                local_font_dir=script_dir.parent / "fonts.local",
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
