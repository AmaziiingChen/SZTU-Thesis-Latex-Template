#!/usr/bin/env python3
"""Render the proposal LaTeX bundle from the same JSON used by Word."""

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

from common.python.content import (  # noqa: E402
    figure_caption_runs,
    has_explicit_numbering,
    split_numbered_subitems,
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
from common.python.equation import latex_display  # noqa: E402


LAYOUT = load_process_document_layout(
    Path(__file__).resolve().parents[1] / "spec" / "layout.json"
)
LIST_MAX_DEPTH = LAYOUT["paragraphs"]["list_max_depth"]
UNORDERED_LIST_MARKERS = LAYOUT["paragraphs"]["unordered_list_markers"]


def _load_word_renderer(script_dir: Path):
    renderer_path = script_dir.parent / "word" / "render.py"
    spec = importlib.util.spec_from_file_location("proposal_word_renderer", renderer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load shared validator: {renderer_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fonts_tex(fonts: dict[str, Path]) -> str:
    simsun_dir, simsun = tex_font_parts(fonts["SimSun"])
    simhei_dir, simhei = tex_font_parts(fonts["SimHei"])
    times_dir, times = tex_font_parts(fonts["Times New Roman"])
    times_bold_dir, times_bold = tex_font_parts(fonts["Times New Roman Bold"])
    times_italic_dir, times_italic = tex_font_parts(fonts["Times New Roman Italic"])
    times_bold_italic_dir, times_bold_italic = tex_font_parts(
        fonts["Times New Roman Bold Italic"]
    )
    if len({times_dir, times_bold_dir, times_italic_dir, times_bold_italic_dir}) != 1:
        raise ValueError("all Times New Roman style files must be in the same directory")
    simsun_options = cjk_emphasis_options(simsun_dir)
    simhei_options = cjk_emphasis_options(simhei_dir)
    return "\n".join(
        [
            "% Generated file. Exact official fonts; do not replace with fallback fonts.",
            rf"\setCJKmainfont[{simsun_options}]{{{simsun}}}",
            rf"\setCJKsansfont[{simhei_options}]{{{simhei}}}",
            rf"\newCJKfontfamily\songti[{simsun_options}]{{{simsun}}}",
            rf"\newCJKfontfamily\heiti[{simhei_options}]{{{simhei}}}",
            rf"\newCJKfontfamily\heitiBold[{simhei_options}]{{{simhei}}}",
            rf"\setmainfont[Path={{{times_dir}}},BoldFont={{{times_bold}}},ItalicFont={{{times_italic}}},BoldItalicFont={{{times_bold_italic}}}]{{{times}}}",
            "",
        ]
    )


def typography_tex(layout: dict) -> str:
    typography = layout["typography"]
    paragraphs = layout["paragraphs"]
    page = layout["page"]
    table = layout["table"]
    signatures = layout["signature_regions"]
    return "\n".join(
        [
            "% Generated file. Shared size map plus proposal-specific layout tokens.",
            rf"\newcommand{{\SZTUTitleSize}}{{\zihao{{{typography['title']['latex_zihao']}}}}}",
            rf"\newcommand{{\SZTULabelSize}}{{\zihao{{{typography['label']['latex_zihao']}}}}}",
            rf"\newcommand{{\SZTUBodySize}}{{\zihao{{{typography['body']['latex_zihao']}}}}}",
            rf"\newcommand{{\SZTUSignatureSize}}{{\zihao{{{typography['signature']['latex_zihao']}}}}}",
            rf"\newcommand{{\SZTUPageTopMargin}}{{{page['top_margin_mm']:g}mm}}",
            rf"\newcommand{{\SZTUPageBottomMargin}}{{{page['bottom_margin_mm']:g}mm}}",
            rf"\newcommand{{\SZTUPageLeftMargin}}{{{page['left_margin_mm']:g}mm}}",
            rf"\newcommand{{\SZTUPageRightMargin}}{{{page['right_margin_mm']:g}mm}}",
            *process_form_latex_tokens(layout),
            rf"\newcommand{{\SZTUFirstLineIndent}}{{{paragraphs['first_line_indent_em']:g}em}}",
            rf"\newcommand{{\SZTUNestedListLeftIndent}}{{{paragraphs['nested_list_left_indent_em']:g}em}}",
            rf"\newcommand{{\SZTUListLevelIndent}}{{{paragraphs['list_level_indent_em']:g}em}}",
            rf"\newcommand{{\SZTUListHangingIndent}}{{{paragraphs['list_hanging_indent_em']:g}em}}",
            rf"\newcommand{{\SZTUImageMaxHeight}}{{{layout['image']['max_height_mm']:g}mm}}",
            rf"\newcommand{{\SZTUStudentSignatureHeight}}{{{signatures['student_min_height_mm']:g}mm}}",
            rf"\newcommand{{\SZTUReviewSignatureHeight}}{{{signatures['review_min_height_mm']:g}mm}}",
            rf"\newcommand{{\SZTUSignatureSlotWidth}}{{{signatures['signature_slot_width_mm']:g}mm}}",
            rf"\newcommand{{\SZTUTeacherOpinionRegionHeight}}{{{signatures['teacher_opinion_region_height_mm']:g}mm}}",
            rf"\newcommand{{\SZTUOpinionTransitionGap}}{{{signatures['opinion_transition_gap_mm']:g}mm}}",
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


def rich_runs(runs: list[dict]) -> str:
    rendered = []
    for run in runs:
        value = tex_escape(run["text"])
        if run["script"] == "sub":
            value = rf"\textsubscript{{{value}}}"
        elif run["script"] == "super":
            value = rf"\textsuperscript{{{value}}}"
        if run["italic"]:
            value = rf"\textit{{{value}}}"
        if run["bold"]:
            value = rf"\textbf{{{value}}}"
        rendered.append(value)
    return "".join(rendered)


def paragraphs(items: list[list[dict]], *, indent: bool = True) -> str:
    prefix = "" if indent else r"\noindent "
    return ("\\par\n" + prefix).join(prefix + rich_runs(item) for item in items)


def _list_marker(block: dict, item: dict, index: int, depth: int) -> str:
    if block["type"] == "ordered_list":
        return item["marker"] or f"{index}、"
    return UNORDERED_LIST_MARKERS[depth - 1]


def render_list_block(block: dict, *, depth: int = 1) -> str:
    if not 1 <= depth <= LIST_MAX_DEPTH:
        raise AssertionError(f"normalized list depth escaped bounds: {depth}")
    rendered = []
    for index, item in enumerate(block["items"], start=1):
        marker = tex_escape(_list_marker(block, item, index, depth))
        rendered.append(
            rf"\ProposalListItem{{{depth}}}{{{marker}}}{{{rich_runs(item['runs'])}}}"
        )
        if item["children"]:
            rendered.append(render_list_block(item["children"], depth=depth + 1))
    return "\n".join(rendered)


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


def render_data_table(block: dict) -> str:
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
        rf"\par\vspace{{3pt}}\Info{{{rich_runs(block['caption_runs'])}}}\par"
        if block["caption_runs"]
        else ""
    )
    config = LAYOUT["embedded_table"]
    options = (
        f"width=\\linewidth,colspec={{{colspec}}},"
        f"columns={{colsep={float(config['cell_padding_mm']):g}mm}},"
        f"rows={{valign=m,rowsep={float(config['cell_padding_mm']):g}mm}},"
        f"hlines={{{float(config['border_pt']):g}pt}},"
        f"vlines={{{float(config['border_pt']):g}pt}}"
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
    block: dict,
    *,
    data_dir: Path,
    assets_dir: Path,
) -> str:
    count = len(block["items"])
    gap_fraction = float(LAYOUT["figure_group"]["column_gap_mm"]) / float(
        LAYOUT["figure_group"]["width_mm"]
    )
    width_fraction = (1.0 - gap_fraction * (count - 1)) / count
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
            rf"{float(LAYOUT['figure_group']['max_item_height_mm']):g}mm,keepaspectratio]"
            rf"{{assets/{tex_escape(asset_name)}}}\par"
            rf"\vspace{{2pt}}\Info{{{subcaption}}}\par\end{{minipage}}"
        )
    caption = rich_runs(figure_caption_runs(block))
    return (
        r"\par\noindent\begin{minipage}{\linewidth}\centering" "\n"
        + r"\hfill".join(items)
        + "\n"
        + rf"\vspace{{3pt}}\Info{{{caption}}}\par"
        + r"\end{minipage}\par"
    )


def render_image(
    block: dict,
    *,
    data_dir: Path,
    assets_dir: Path,
) -> str:
    source = _resolve_image(block["path"], data_dir)
    asset_name = _safe_asset_name(source)
    assets_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, assets_dir / asset_name)
    caption = rich_runs(figure_caption_runs(block))
    return (
        rf"\ProposalFigure{{assets/{tex_escape(asset_name)}}}"
        rf"{{{block['width_mm']:g}mm}}{{{caption}}}"
    )


def render_text_blocks(
    items: list[dict],
    *,
    data_dir: Path,
    assets_dir: Path,
) -> str:
    rendered = []
    for block in items:
        if block["type"] == "paragraph":
            rendered.append(rf"\ProposalParagraph{{{rich_runs(block['runs'])}}}")
        elif block["type"] in {"ordered_list", "unordered_list"}:
            rendered.append(render_list_block(block))
        elif block["type"] == "image":
            rendered.append(
                render_image(block, data_dir=data_dir, assets_dir=assets_dir)
            )
        elif block["type"] == "data_table":
            rendered.append(render_data_table(block))
        elif block["type"] == "figure_group":
            rendered.append(
                render_figure_group(block, data_dir=data_dir, assets_dir=assets_dir)
            )
        elif block["type"] == "equation":
            config = LAYOUT["equation"]
            rendered.append(
                rf"\par\vspace{{{config['space_before_pt']:g}pt}}"
                f"{latex_display(block['expression'], block.get('equation_label'))}"
                rf"\vspace{{{config['space_after_pt']:g}pt}}\par"
            )
        else:
            raise AssertionError(f"unsupported normalized block: {block['type']}")
    return "\n".join(rendered)


def numbered_paragraphs(items: list[list[dict]]) -> str:
    rendered_items = []
    for index, item in enumerate(items, start=1):
        split_item = split_numbered_subitems(item)
        lead = split_item[0] if split_item else item
        rendered = rich_runs(lead) if has_explicit_numbering(lead) else rf"{index}、{rich_runs(lead)}"
        if split_item:
            _, subitems, continuations = split_item
            rendered += "\n" + "\n".join(
                rf"\NestedOrderedItem{{{tex_escape(marker)}}}{{{rich_runs(subitem)}}}"
                for marker, subitem in subitems
            )
            if continuations:
                rendered += "\\par\n" + "\\par\n".join(
                    rich_runs(continuation) for continuation in continuations
                )
        rendered_items.append(rendered)
    return "\\par\n".join(rendered_items)


def render_method_blocks(
    items: list[dict],
    *,
    data_dir: Path,
    assets_dir: Path,
) -> str:
    if all(item["type"] == "paragraph" for item in items):
        return numbered_paragraphs([item["runs"] for item in items])
    return render_text_blocks(items, data_dir=data_dir, assets_dir=assets_dir)


def data_tex(data: dict, *, data_dir: Path, assets_dir: Path) -> str:
    metadata = data["metadata"]
    sections = data["sections"]
    macros = {
        "ProposalTitle": rich_runs(metadata["title"]),
        "StudentName": tex_escape(metadata["student_name"]),
        "StudentId": tex_escape(metadata["student_id"]),
        "Major": tex_escape(metadata["major"]),
        "College": tex_escape(metadata["college"]),
        "Advisor": tex_escape(metadata["advisor"]),
        "SignificanceAndStatus": paragraphs(sections["significance_and_status"]),
        "ResearchContent": render_text_blocks(
            sections["research_content"], data_dir=data_dir, assets_dir=assets_dir
        ),
        "MethodsAndMeans": render_method_blocks(
            sections["methods_and_means"], data_dir=data_dir, assets_dir=assets_dir
        ),
        "ResearchSteps": render_method_blocks(
            sections["research_steps"], data_dir=data_dir, assets_dir=assets_dir
        ),
        "ReferencesContent": paragraphs(sections["references"], indent=False),
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
    (output_dir / "proposal-data.tex").write_text(
        data_tex(
            data,
            data_dir=data_path.resolve().parent,
            assets_dir=assets_dir,
        ),
        encoding="utf-8",
    )
    (output_dir / "proposal-fonts.tex").write_text(fonts_tex(fonts), encoding="utf-8")
    (output_dir / "proposal-typography.tex").write_text(
        typography_tex(layout), encoding="utf-8"
    )
    copy_process_form_latex_support(output_dir)
    shutil.copy2(script_dir / "main.tex", output_dir / "main.tex")

    if compile_pdf:
        command = [
            "xelatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "main.tex",
        ]
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
