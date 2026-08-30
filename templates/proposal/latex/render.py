#!/usr/bin/env python3
"""Render the proposal LaTeX bundle from the same JSON used by Word."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[2]
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

from common.python.content import (  # noqa: E402
    has_explicit_numbering,
    split_numbered_subitems,
)
from common.python.font_files import (  # noqa: E402
    resolve_font_files,
    tex_font_parts,
)
from common.python.typography import load_document_layout  # noqa: E402


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
    return "\n".join(
        [
            "% Generated file. Exact official fonts; do not replace with fallback fonts.",
            rf"\setCJKmainfont[Path={{{simsun_dir}}}]{{{simsun}}}",
            rf"\setCJKsansfont[Path={{{simhei_dir}}}]{{{simhei}}}",
            rf"\newCJKfontfamily\songti[Path={{{simsun_dir}}}]{{{simsun}}}",
            rf"\newCJKfontfamily\heiti[Path={{{simhei_dir}}}]{{{simhei}}}",
            rf"\newCJKfontfamily\heitiBold[Path={{{simhei_dir}}},AutoFakeBold=3]{{{simhei}}}",
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
    padding = float(table["horizontal_padding_mm"])
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
            rf"\newcommand{{\SZTUFormRuleWidth}}{{{table['border_pt']:g}pt}}",
            rf"\newcommand{{\SZTUCellHorizontalPadding}}{{{padding:g}mm}}",
            rf"\newcommand{{\SZTUCellHorizontalPaddingDouble}}{{{2 * padding:g}mm}}",
            rf"\newcommand{{\SZTUFirstLineIndent}}{{{paragraphs['first_line_indent_em']:g}em}}",
            rf"\newcommand{{\SZTUNestedListLeftIndent}}{{{paragraphs['nested_list_left_indent_em']:g}em}}",
            rf"\newcommand{{\SZTUStudentSignatureHeight}}{{{signatures['student_min_height_mm']:g}mm}}",
            rf"\newcommand{{\SZTUReviewSignatureHeight}}{{{signatures['review_min_height_mm']:g}mm}}",
            rf"\newcommand{{\SZTUSignatureSlotWidth}}{{{signatures['signature_slot_width_mm']:g}mm}}",
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


def data_tex(data: dict) -> str:
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
        "ResearchContent": paragraphs(sections["research_content"]),
        "MethodsAndMeans": numbered_paragraphs(sections["methods_and_means"]),
        "ResearchSteps": numbered_paragraphs(sections["research_steps"]),
        "ReferencesContent": paragraphs(sections["references"], indent=False),
    }
    lines = ["% Generated file. Edit the JSON source, not this file."]
    lines.extend(f"\\long\\def\\{name}{{{value}}}" for name, value in macros.items())
    return "\n".join(lines) + "\n"


def render(data_path: Path, output_dir: Path, *, overwrite: bool, compile_pdf: bool) -> Path:
    script_dir = Path(__file__).resolve().parent
    shared = _load_word_renderer(script_dir)
    data = shared.validate_data(json.loads(data_path.read_text(encoding="utf-8")))
    layout = load_document_layout(script_dir.parent / "spec" / "layout.json")
    fonts = resolve_font_files(
        layout["required_font_files"],
        local_font_dir=script_dir.parent / "fonts.local",
    )

    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"output directory is not empty; pass --overwrite: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "proposal-data.tex").write_text(
        data_tex(data), encoding="utf-8"
    )
    (output_dir / "proposal-fonts.tex").write_text(fonts_tex(fonts), encoding="utf-8")
    (output_dir / "proposal-typography.tex").write_text(
        typography_tex(layout), encoding="utf-8"
    )
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
            layout = load_document_layout(script_dir.parent / "spec" / "layout.json")
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
