#!/usr/bin/env python3
"""Run structural and rendered regression checks for the proposal prototype."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import pdfplumber
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image


def run(command: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.stdout


def bbox(chars: list[dict]) -> tuple[float, float, float, float]:
    return (
        min(float(char["x0"]) for char in chars),
        min(float(char["top"]) for char in chars),
        max(float(char["x1"]) for char in chars),
        max(float(char["bottom"]) for char in chars),
    )


def cell_chars(
    chars: list[dict],
    bounds: tuple[float, float, float, float],
    *,
    font: str,
    size: float,
) -> list[dict]:
    x0, top, x1, bottom = bounds
    return [
        char
        for char in chars
        if x0 <= (float(char["x0"]) + float(char["x1"])) / 2 <= x1
        and top <= (float(char["top"]) + float(char["bottom"])) / 2 <= bottom
        and font in char["fontname"]
        and round(float(char["size"]), 2) == size
    ]


def assert_centered(chars: list[dict], bounds: tuple[float, float, float, float]) -> None:
    assert chars
    x0, top, x1, bottom = bounds
    bx0, btop, bx1, bbottom = bbox(chars)
    horizontal_error = abs((bx0 + bx1) / 2 - (x0 + x1) / 2)
    vertical_error = abs((btop + bbottom) / 2 - (top + bottom) / 2)
    assert horizontal_error <= 1.7, (bounds, bbox(chars), horizontal_error)
    assert vertical_error <= 1.7, (bounds, bbox(chars), vertical_error)


def assert_vertically_centered(
    chars: list[dict], bounds: tuple[float, float, float, float]
) -> None:
    assert chars
    _, top, _, bottom = bounds
    _, btop, _, bbottom = bbox(chars)
    vertical_error = abs((btop + bbottom) / 2 - (top + bottom) / 2)
    assert vertical_error <= 1.7, (bounds, bbox(chars), vertical_error)


def clustered(values: list[float], *, tolerance: float = 1.0) -> list[float]:
    result: list[float] = []
    for value in sorted(values):
        if not result or value - result[-1] > tolerance:
            result.append(value)
    return result


def assert_rule_has_raster_ink(
    image: Image.Image,
    *,
    page_width: float,
    page_height: float,
    x0: float,
    x1: float,
    top: float,
) -> None:
    grayscale = image.convert("L")
    scale_x = grayscale.width / page_width
    scale_y = grayscale.height / page_height
    px0 = max(0, round(x0 * scale_x))
    px1 = min(grayscale.width, round(x1 * scale_x))
    py = round(top * scale_y)
    ratios = []
    for row in range(max(0, py - 3), min(grayscale.height, py + 4)):
        dark = sum(grayscale.getpixel((column, row)) < 160 for column in range(px0, px1))
        ratios.append(dark / max(1, px1 - px0))
    # A parsed PDF edge is not sufficient evidence: the corresponding raster
    # row must visibly contain the rule across almost the whole table width.
    assert ratios and max(ratios) >= 0.75


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pdf", action="store_true", help="skip XeLaTeX and CJK checks")
    args = parser.parse_args()

    proposal_dir = Path(__file__).resolve().parent
    project_dir = proposal_dir.parents[1]
    output_root = project_dir / "tmp" / "proposal-tests"
    output_root.mkdir(parents=True, exist_ok=True)

    latex_template = (proposal_dir / "latex" / "main.tex").read_text(encoding="utf-8")
    assert r"{\heitiBold\bfseries\zihao{-2}深圳技术大学本科毕业论文（设计）\par}" in latex_template
    assert r"\newcommand{\Label}[1]{{\heiti\zihao{-4}#1}}" in latex_template
    assert r"\newcommand{\SignatureText}[1]{{\songti\zihao{-4}#1}}" in latex_template
    assert r"\noindent 本课题研究方法、手段如下" not in latex_template
    assert r"\noindent 本课题研究步骤如下" not in latex_template
    assert r"\newcommand{\NestedOrderedItem}" in latex_template
    body_end = latex_template.index(r"\end{tcolorbox}")
    signature_table_start = latex_template.index(
        r"\noindent\begin{tabular}", body_end
    )
    between_body_and_signature = latex_template[body_end:signature_table_start]
    assert r"\end{adjustwidth}" not in between_body_and_signature
    assert r"\begin{center}" not in between_body_and_signature

    for name in ("short", "normal", "long", "layout_stress"):
        fixture = proposal_dir / "fixtures" / f"{name}.json"
        fixture_data = json.loads(fixture.read_text(encoding="utf-8"))
        assert fixture_data["schema_version"] == "0.2"
        assert "methods_and_means" in fixture_data["sections"]
        assert "research_steps" in fixture_data["sections"]
        assert "methods_and_steps" not in fixture_data["sections"]
        docx_output = output_root / f"{name}.docx"
        run(
            [
                sys.executable,
                str(proposal_dir / "word" / "render.py"),
                "--data",
                str(fixture),
                "--output",
                str(docx_output),
                "--overwrite",
            ],
            cwd=project_dir,
        )
        document = Document(docx_output)
        assert len(document.tables) == 1
        table = document.tables[0]
        assert len(table.rows) == 9 and len(table.columns) == 7
        assert "学生签名" in table.rows[7].cells[0].text
        assert "指导教师意见" in table.rows[8].cells[0].text
        assert "学院领导意见" in table.rows[8].cells[0].text
        assert not table.rows[5].cells[0].paragraphs[0].paragraph_format.page_break_before
        assert "本课题研究方法、手段如下" in table.rows[5].cells[0].text
        assert "本课题研究步骤如下" in table.rows[5].cells[0].text
        method_paragraphs = table.rows[5].cells[0].paragraphs[1:]
        assert method_paragraphs
        assert all(
            paragraph.paragraph_format.first_line_indent is not None
            and paragraph.paragraph_format.first_line_indent.pt == 21
            for paragraph in method_paragraphs
        )
        if name == "long":
            assert "第一阶段完成" in table.rows[5].cells[0].text
            assert "1、第一阶段完成" not in table.rows[5].cells[0].text
        assert table.rows[3].cells[0].paragraphs[1].paragraph_format.line_spacing == 1
        title_runs = table.rows[0].cells[1].paragraphs[0].runs
        assert title_runs and all(run.font.size.pt == 10.5 for run in title_runs)
        if name == "normal":
            assert any(run.text == "2" and run.font.subscript for run in title_runs)
            assert any(run.text == "3" and run.font.subscript for run in title_runs)
            assert any(run.text == "4" and run.font.subscript for run in title_runs)
            significance_runs = [
                run
                for paragraph in table.rows[3].cells[0].paragraphs
                for run in paragraph.runs
            ]
            assert any(run.text == "[1]" and run.font.superscript for run in significance_runs)
        for row_index, cell_index in ((0, 0), (1, 0), (1, 2), (1, 5), (2, 0), (2, 2)):
            cell = table.rows[row_index].cells[cell_index]
            assert cell.vertical_alignment == WD_CELL_VERTICAL_ALIGNMENT.CENTER
            assert all(
                paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER
                for paragraph in cell.paragraphs
            )
        for row_index, cell_index in ((0, 1), (1, 6), (2, 1)):
            cell = table.rows[row_index].cells[cell_index]
            assert cell.vertical_alignment == WD_CELL_VERTICAL_ALIGNMENT.CENTER
            assert cell.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.LEFT
        for row_index, cell_index in ((1, 1), (1, 3), (2, 4)):
            cell = table.rows[row_index].cells[cell_index]
            assert cell.vertical_alignment == WD_CELL_VERTICAL_ALIGNMENT.CENTER
            assert cell.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
        if name == "normal":
            nested_paragraphs = [
                paragraph
                for paragraph in method_paragraphs
                if paragraph.text.startswith(("（1）", "（2）", "（3）"))
            ]
            assert [paragraph.text[:3] for paragraph in nested_paragraphs] == [
                "（1）",
                "（2）",
                "（3）",
            ]
            assert all(
                paragraph.paragraph_format.left_indent is not None
                and paragraph.paragraph_format.left_indent.pt == 10.5
                for paragraph in nested_paragraphs
            )
            continuation = next(
                paragraph
                for paragraph in method_paragraphs
                if paragraph.text.startswith("通过统一数据")
            )
            assert continuation.paragraph_format.left_indent is None
            reference_runs = [
                run
                for paragraph in table.rows[6].cells[0].paragraphs
                for run in paragraph.runs
            ]
            assert any(run.text == "3" and run.font.subscript for run in reference_runs)
            assert any(run.text == "4" and run.font.subscript for run in reference_runs)

        if args.skip_pdf:
            continue

        latex_dir = output_root / f"latex-{name}"
        latex_compile_output = run(
            [
                sys.executable,
                str(proposal_dir / "latex" / "render.py"),
                "--data",
                str(fixture),
                "--output-dir",
                str(latex_dir),
                "--overwrite",
                "--compile",
            ],
            cwd=project_dir,
        )
        assert "Overfull" not in latex_compile_output
        assert "Missing character" not in latex_compile_output
        data_tex = (latex_dir / "proposal-data.tex").read_text(encoding="utf-8")
        fonts_tex = (latex_dir / "proposal-fonts.tex").read_text(encoding="utf-8")
        assert "ProposalAdaptiveLayout" not in data_tex
        assert r"\long\def\MethodsAndMeans" in data_tex
        assert r"\long\def\ResearchSteps" in data_tex
        assert "AutoFakeBold=3" in fonts_tex
        if name == "normal":
            assert r"\long\def\ProposalTitle" in data_tex
            assert r"H\textsubscript{2}O\textsubscript{2}" in data_tex
            assert r"g-C\textsubscript{3}N\textsubscript{4}" in data_tex
            assert r"\textsubscript{3}" in data_tex
            assert r"\textsubscript{4}" in data_tex
            assert r"\textsuperscript{[1]}" in data_tex
            for marker in ("（1）", "（2）", "（3）"):
                assert rf"\NestedOrderedItem{{{marker}}}" in data_tex
        if name == "long":
            assert "第一阶段完成" in data_tex
            assert "1、第一阶段完成" not in data_tex

        info = run(["pdfinfo", str(latex_dir / "main.pdf")], cwd=project_dir)
        match = re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE)
        assert match is not None
        pages = int(match.group(1))
        assert 2 <= pages <= 8
        fonts = run(["pdffonts", str(latex_dir / "main.pdf")], cwd=project_dir)
        assert "SimSun" in fonts
        assert "SimHei" in fonts
        assert "TimesNewRoman" in fonts
        with pdfplumber.open(latex_dir / "main.pdf") as pdf:
            page_chars = [list(page.chars) for page in pdf.pages]
            page_words = [page.extract_words() for page in pdf.pages]
            chars = [
                char
                for current_page_chars in page_chars
                for char in current_page_chars
                if char.get("text", "").strip()
            ]
            first_page_chars = page_chars[0]
            first_page_lines = list(pdf.pages[0].lines)
            first_page_edges = list(pdf.pages[0].edges)
            page_edges = [list(page.edges) for page in pdf.pages]
            page_dimensions = [(float(page.width), float(page.height)) for page in pdf.pages]
        simsun_sizes = {
            round(float(char["size"]), 2)
            for char in chars
            if "SimSun" in char["fontname"]
        }
        simhei_sizes = {
            round(float(char["size"]), 2)
            for char in chars
            if "SimHei" in char["fontname"]
        }
        assert all(
            any(name in char["fontname"] for name in ("SimSun", "SimHei", "TimesNewRoman"))
            for char in chars
        )
        assert 10.50 in simsun_sizes and 12.00 in simsun_sizes
        assert 12.00 in simhei_sizes and 18.00 in simhei_sizes
        horizontal_candidates = [
            line
            for line in first_page_edges
            if abs(float(line["bottom"]) - float(line["top"])) < 0.1
            and float(line["top"]) < 400
        ]
        horizontal = [
            top
            for top in clustered(
                [round(float(line["top"]), 2) for line in horizontal_candidates]
            )
            if (
                max(
                    float(line["x1"])
                    for line in horizontal_candidates
                    if abs(float(line["top"]) - top) <= 1.0
                )
                - min(
                    float(line["x0"])
                    for line in horizontal_candidates
                    if abs(float(line["top"]) - top) <= 1.0
                )
                > 400
            )
        ]
        assert len(horizontal) >= 4
        rows = horizontal[:4]
        vertical = sorted(
            {
                round(float(line["x0"]), 2)
                for line in first_page_edges
                if abs(float(line["x1"]) - float(line["x0"])) < 0.1
                and float(line["top"]) < rows[-1] - 0.1
                and float(line["bottom"]) > rows[0] + 0.1
            }
        )
        assert len(vertical) == 8
        cols = vertical

        label_cells = (
            (cols[0], rows[0], cols[1], rows[1]),
            (cols[0], rows[1], cols[1], rows[2]),
            (cols[2], rows[1], cols[3], rows[2]),
            (cols[5], rows[1], cols[6], rows[2]),
            (cols[0], rows[2], cols[1], rows[3]),
            (cols[2], rows[2], cols[4], rows[3]),
        )
        for bounds in label_cells:
            assert_centered(
                cell_chars(first_page_chars, bounds, font="SimHei", size=12.00),
                bounds,
            )
        centered_data_cells = (
            ((cols[1], rows[1], cols[2], rows[2]), "SimSun"),
            ((cols[3], rows[1], cols[5], rows[2]), "TimesNewRoman"),
            ((cols[4], rows[2], cols[7], rows[3]), "SimSun"),
        )
        for bounds, font in centered_data_cells:
            assert_centered(
                cell_chars(first_page_chars, bounds, font=font, size=10.50),
                bounds,
            )
        left_data_cells = (
            (cols[1], rows[0], cols[7], rows[1]),
            (cols[6], rows[1], cols[7], rows[2]),
            (cols[1], rows[2], cols[2], rows[3]),
        )
        for bounds in left_data_cells:
            selected = cell_chars(first_page_chars, bounds, font="SimSun", size=10.50)
            assert_vertically_centered(selected, bounds)
            # A left-aligned cell must retain the 2 mm internal inset instead
            # of placing glyphs directly against the border.
            assert min(float(char["x0"]) for char in selected) - bounds[0] >= 4.5

        if name == "short":
            # Short majors are centered; long majors are covered by the
            # left-aligned multi-line layout_stress fixture below.
            assert_centered(
                cell_chars(
                    first_page_chars,
                    left_data_cells[1],
                    font="SimSun",
                    size=10.50,
                ),
                left_data_cells[1],
            )

        if name == "layout_stress":
            assert abs(rows[0] - 134.64) <= 1.0
            assert abs(cols[0] - 84.60) <= 1.0
            assert abs(cols[-1] - 504.70) <= 1.0
            metadata_vertical_bottom = max(
                float(line["bottom"])
                for line in first_page_lines
                if abs(float(line["x1"]) - float(line["x0"])) < 0.1
                and float(line["top"]) < rows[-1]
            )
            assert abs(metadata_vertical_bottom - rows[-1]) <= 0.3
            assert all(
                abs(float(line["linewidth"]) - 0.48) <= 0.01
                for line in first_page_lines
                if float(line["top"]) < rows[-1] + 0.1
            )

            for bounds in left_data_cells:
                selected = cell_chars(first_page_chars, bounds, font="SimSun", size=10.50)
                starts = []
                for top in sorted({round(float(char["top"]), 1) for char in selected}):
                    starts.append(
                        min(
                            float(char["x0"])
                            for char in selected
                            if round(float(char["top"]), 1) == top
                        )
                    )
                assert len(starts) >= 2
                assert max(starts) - min(starts) <= 0.8
                assert min(starts) - bounds[0] >= 4.5
                assert min(starts) - bounds[0] <= 9.0

            extracted = run(
                ["pdftotext", "-layout", str(latex_dir / "main.pdf"), "-"],
                cwd=project_dir,
            )
            assert "ENDREF-A" in extracted and "ENDREF-B" in extracted
            reference_lines = extracted.split("参考文献：", 1)[1].split("学生签名", 1)[0]
            assert len([line for line in reference_lines.splitlines() if line.strip()]) >= 8
        if name == "long":
            raster_dir = latex_dir / "raster-180"
            raster_dir.mkdir(parents=True, exist_ok=True)
            run(
                [
                    "pdftocairo",
                    "-png",
                    "-r",
                    "180",
                    str(latex_dir / "main.pdf"),
                    str(raster_dir / "page"),
                ],
                cwd=project_dir,
            )
            break_rule_checks = 0
            separator_checks = 0
            for page_index, (edges, dimensions) in enumerate(
                zip(page_edges, page_dimensions, strict=True), start=1
            ):
                page_width, page_height = dimensions
                with Image.open(raster_dir / f"page-{page_index}.png") as image:
                    boundary_edges = [
                        edge
                        for edge in edges
                        if abs(float(edge["bottom"]) - float(edge["top"])) < 0.1
                        and float(edge["x1"]) - float(edge["x0"]) > 400
                        and (
                            float(edge["top"]) < 100
                            or float(edge["top"]) > page_height - 100
                        )
                    ]
                    for top in clustered(
                        [float(edge["top"]) for edge in boundary_edges]
                    ):
                        edge = max(
                            (
                                candidate
                                for candidate in boundary_edges
                                if abs(float(candidate["top"]) - top) <= 1.0
                            ),
                            key=lambda candidate: float(candidate["x1"])
                            - float(candidate["x0"]),
                        )
                        assert_rule_has_raster_ink(
                            image,
                            page_width=page_width,
                            page_height=page_height,
                            x0=float(edge["x0"]),
                            x1=float(edge["x1"]),
                            top=float(edge["top"]),
                        )
                        break_rule_checks += 1

                    for edge in edges:
                        top = float(edge["top"])
                        if not (
                            abs(float(edge["bottom"]) - top) < 0.1
                            and float(edge["x1"]) - float(edge["x0"]) > 400
                            and abs(float(edge.get("linewidth", 0)) - 0.48) <= 0.01
                            and 100 < top < page_height - 100
                        ):
                            continue
                        crossing_sides = [
                            float(side["x0"])
                            for side in edges
                            if abs(float(side["x1"]) - float(side["x0"])) < 0.1
                            and float(side["top"]) <= top
                            and float(side["bottom"]) >= top
                            and float(side["bottom"]) - float(side["top"]) > 20
                        ]
                        if len(crossing_sides) < 2:
                            continue
                        assert float(edge["x0"]) - min(crossing_sides) <= 0.6
                        assert max(crossing_sides) - float(edge["x1"]) <= 0.6
                        assert_rule_has_raster_ink(
                            image,
                            page_width=page_width,
                            page_height=page_height,
                            x0=min(crossing_sides),
                            x1=max(crossing_sides),
                            top=top,
                        )
                        separator_checks += 1
            assert break_rule_checks >= 2
            assert separator_checks >= 2
        if name == "normal":
            all_words = [word for words in page_words for word in words]
            methods_label = next(
                word for word in all_words if word["text"] == "研究方法、手段及步骤："
            )
            methods_intro = next(
                word for word in all_words if word["text"] == "本课题研究方法、手段如下："
            )
            steps_intro = next(
                word for word in all_words if word["text"] == "本课题研究步骤如下："
            )
            continuation_word = next(
                word for word in all_words if word["text"].startswith("通过统一数据")
            )
            nested_markers = [
                word
                for word in all_words
                if word["text"] in {"（1）", "（2）", "（3）"}
            ]
            assert 19.0 <= float(methods_intro["x0"]) - float(methods_label["x0"]) <= 23.0
            assert abs(float(steps_intro["x0"]) - float(methods_intro["x0"])) <= 0.3
            assert abs(float(continuation_word["x0"]) - float(methods_intro["x0"])) <= 0.3
            assert len(nested_markers) == 3
            assert all(
                3.0 <= float(marker["x0"]) - float(methods_intro["x0"]) <= 7.0
                for marker in nested_markers
            )

            signature_page_index = next(
                index
                for index, words in enumerate(page_words)
                if any("学生签名" in word["text"] for word in words)
            )
            signature_page_chars = page_chars[signature_page_index]
            signature_page_edges = page_edges[signature_page_index]
            signature_label_top = min(
                float(char["top"])
                for char in signature_page_chars
                if char["text"] == "学"
                and "SimHei" in char["fontname"]
                and round(float(char["size"]), 2) == 12.00
            )
            body_bottom_candidates = [
                float(edge["top"])
                for edge in signature_page_edges
                if abs(float(edge["bottom"]) - float(edge["top"])) < 0.1
                and float(edge["x1"]) - float(edge["x0"]) > 400
                and abs(float(edge.get("linewidth", 0)) - 0.40) <= 0.01
                and float(edge["top"]) < signature_label_top
            ]
            if body_bottom_candidates:
                body_bottom = max(body_bottom_candidates)
                signature_top = min(
                    float(edge["top"])
                    for edge in signature_page_edges
                    if abs(float(edge["bottom"]) - float(edge["top"])) < 0.1
                    and float(edge["x1"]) - float(edge["x0"]) > 400
                    and abs(float(edge.get("linewidth", 0)) - 0.48) <= 0.01
                    and body_bottom <= float(edge["top"]) < signature_label_top
                )
                # If the body and handwritten section share a page, they must
                # also share one boundary without a visible interruption.
                assert signature_top - body_bottom <= 0.8

            signature_runs = [
                char
                for char in chars
                if char["text"] == "签"
                and "SimSun" in char["fontname"]
                and round(float(char["size"]), 2) == 12.00
            ]
            assert len(signature_runs) == 2
            assert all(357 <= float(char["x0"]) <= 362 for char in signature_runs)
            date_year_runs = [
                char
                for char in chars
                if char["text"] == "年"
                and "SimSun" in char["fontname"]
                and round(float(char["size"]), 2) == 12.00
            ]
            assert len(date_year_runs) == 2
            assert all(403 <= float(char["x0"]) <= 408 for char in date_year_runs)
        run(
            [
                sys.executable,
                str(project_dir / "scripts" / "validate_cjk_render.py"),
                str(latex_dir / "main.pdf"),
            ],
            cwd=project_dir,
        )

    print("proposal regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
