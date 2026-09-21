#!/usr/bin/env python3
"""Compile and regression-test the calibrated undergraduate thesis template."""

from __future__ import annotations

import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - dependency error path
    raise SystemExit("ERROR: Pillow is required (import PIL failed).") from exc


ROOT = Path(__file__).resolve().parents[2]
THESIS_DIR = Path(__file__).resolve().parent
BUILD_ROOT = ROOT / "tmp" / "thesis-tests"
MAIN_TEX = ROOT / "sztuthesis_main.tex"
STRESS_TEX = THESIS_DIR / "fixtures" / "bibliography-stress.tex"
HEADER_PREFIX = "深圳技术大学本科毕业论文—"


@dataclass(frozen=True)
class CaseArtifacts:
    directory: Path
    jobname: str
    pdf: Path
    log: Path
    aux: Path
    toc: Path
    bbl: Path
    blg: Path
    fls: Path
    compile_output: str


def require_command(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"required command not found: {name}")
    return path


def run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path = ROOT,
) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}"
        )
    return result.stdout


def font_environment() -> dict[str, str]:
    env = dict(os.environ)
    if sys.platform == "darwin":
        candidates = [
            Path.home() / "Library/Fonts",
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
            Path("/System/Library/Fonts/Supplemental"),
            Path("/Applications/Microsoft Word.app/Contents/Resources/DFonts"),
            Path("/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts"),
        ]
        existing = [str(path) for path in candidates if path.is_dir()]
        if env.get("OSFONTDIR"):
            existing.append(env["OSFONTDIR"])
        env["OSFONTDIR"] = os.pathsep.join(existing)
    return env


def compile_case(tex: Path, case_name: str) -> CaseArtifacts:
    """Compile into a unique, freshly created directory and jobname."""
    directory = BUILD_ROOT / case_name
    if directory.is_dir():
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)
    jobname = f"{case_name}-regression"
    latexmk = require_command("latexmk")
    relative_tex = tex.relative_to(ROOT)
    compile_output = run(
        [
            latexmk,
            "-xelatex",
            "-interaction=nonstopmode",
            "-file-line-error",
            "-halt-on-error",
            f"-jobname={jobname}",
            f"-outdir={directory}",
            str(relative_tex),
        ],
        env=font_environment(),
    )
    artifacts = CaseArtifacts(
        directory=directory,
        jobname=jobname,
        pdf=directory / f"{jobname}.pdf",
        log=directory / f"{jobname}.log",
        aux=directory / f"{jobname}.aux",
        toc=directory / f"{jobname}.toc",
        bbl=directory / f"{jobname}.bbl",
        blg=directory / f"{jobname}.blg",
        fls=directory / f"{jobname}.fls",
        compile_output=compile_output,
    )
    for artifact in (
        artifacts.pdf,
        artifacts.log,
        artifacts.aux,
        artifacts.bbl,
        artifacts.blg,
        artifacts.fls,
    ):
        assert artifact.is_file(), artifact
    assert_isolated_bibliography(artifacts)
    return artifacts


def assert_isolated_bibliography(artifacts: CaseArtifacts) -> None:
    """The cold build must read its own BBL, never a root-level stale BBL."""
    inputs: set[Path] = set()
    for line in artifacts.fls.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("INPUT ") or not line.endswith(".bbl"):
            continue
        path = Path(line.removeprefix("INPUT "))
        if not path.is_absolute():
            path = ROOT / path
        inputs.add(path.resolve())
    assert inputs == {artifacts.bbl.resolve()}, inputs
    assert (ROOT / "sztuthesis_main.bbl").resolve() not in inputs


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def extracted_pages(pdf: Path) -> list[str]:
    text = run([require_command("pdftotext"), "-layout", str(pdf), "-"])
    return [page for page in text.split("\f") if page.strip()]


def page_index(pages: list[str], marker: str) -> int:
    matches = [index for index, page in enumerate(pages) if marker in page]
    assert len(matches) == 1, (marker, matches)
    return matches[0]


def normalized_page_index(pages: list[str], marker: str) -> int:
    matches = [index for index, page in enumerate(pages) if marker in normalize(page)]
    assert len(matches) == 1, (marker, matches)
    return matches[0]


def render_page(pdf: Path, page_number: int, target: Path) -> Path:
    run(
        [
            require_command("pdftocairo"),
            "-png",
            "-singlefile",
            "-r",
            "180",
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            str(pdf),
            str(target),
        ]
    )
    return target.with_suffix(".png")


def has_header_rule(image_path: Path) -> bool:
    """Detect the long horizontal rule in the top quarter of an A4 page."""
    with Image.open(image_path) as source:
        image = source.convert("L")
        left = round(image.width * 31.7 / 210.0)
        right = image.width - left
        top = round(image.height * 10.0 / 297.0)
        bottom = round(image.height * 45.0 / 297.0)
        width = right - left
        for y in range(top, bottom):
            dark = sum(image.getpixel((x, y)) < 100 for x in range(left, right))
            if dark / width >= 0.70:
                return True
    return False


def assert_pdf_a4(pdf: Path) -> None:
    info = run([require_command("pdfinfo"), str(pdf)])
    assert re.search(r"Page size:\s+595(?:\.\d+)? x 841(?:\.\d+)? pts \(A4\)", info), info


def assert_required_fonts(pdf: Path, required: tuple[str, ...]) -> None:
    output = run([require_command("pdffonts"), str(pdf)])
    compact = output.replace(" ", "")
    for family in required:
        assert family in compact, f"required embedded font missing: {family}"
    matching_lines = [
        line
        for line in output.splitlines()
        if any(family in line.replace(" ", "") for family in required)
    ]
    assert matching_lines
    for line in matching_lines:
        columns = line.split()
        assert columns[-5:-2] == ["yes", "yes", "yes"], line


def assert_clean_build(artifacts: CaseArtifacts) -> None:
    log = artifacts.log.read_text(encoding="utf-8", errors="replace")
    persistent_forbidden = (
        "Overfull \\hbox",
        "Underfull \\hbox",
        "Missing character",
        "LaTeX Font Warning",
        "xdvipdfmx:warning",
    )
    final_forbidden = persistent_forbidden + (
        "There were undefined references",
        "There were undefined citations",
        "Citation `",
        "Reference `",
    )
    # The first XeLaTeX pass legitimately sees unresolved citations. Layout/font/PDF-driver
    # defects must never appear in any pass, and the final log must be fully resolved.
    for marker in persistent_forbidden:
        assert marker not in artifacts.compile_output, marker
    for marker in final_forbidden:
        assert marker not in log, marker
    blg = artifacts.blg.read_text(encoding="utf-8", errors="replace")
    assert "Warning--" not in blg


def assert_cjk_gate(pdf: Path) -> None:
    run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_cjk_render.py"),
            str(pdf),
            "--dpi",
            "180",
        ]
    )


def strip_tex_comments(source: str) -> str:
    stripped: list[str] = []
    for line in source.splitlines():
        cut = len(line)
        for index, character in enumerate(line):
            if character != "%":
                continue
            slash_count = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                slash_count += 1
                cursor -= 1
            if slash_count % 2 == 0:
                cut = index
                break
        stripped.append(line[:cut])
    return "\n".join(stripped)


def command_brace_arguments(source: str, command: str) -> list[str]:
    """Return balanced mandatory brace arguments for a simple TeX command."""
    arguments: list[str] = []
    cursor = 0
    while True:
        start = source.find(command, cursor)
        if start < 0:
            return arguments
        position = start + len(command)
        while position < len(source) and source[position].isspace():
            position += 1
        if position < len(source) and source[position] == "[":
            optional_depth = 1
            position += 1
            while position < len(source) and optional_depth:
                if source[position] == "[":
                    optional_depth += 1
                elif source[position] == "]":
                    optional_depth -= 1
                position += 1
            while position < len(source) and source[position].isspace():
                position += 1
        if position >= len(source) or source[position] != "{":
            cursor = position
            continue
        depth = 1
        end = position + 1
        while end < len(source) and depth:
            if source[end] == "{" and source[end - 1] != "\\":
                depth += 1
            elif source[end] == "}" and source[end - 1] != "\\":
                depth -= 1
            end += 1
        assert depth == 0, f"unbalanced {command} at offset {start}"
        arguments.append(source[position + 1 : end - 1])
        cursor = end


def assert_caption_contract(layout: dict[str, object]) -> None:
    source = strip_tex_comments(
        (ROOT / "content" / "content.tex").read_text(encoding="utf-8")
    )
    captions = [caption.strip() for caption in command_brace_arguments(source, "\\caption")]
    assert captions
    forbidden = set(layout["captions"]["forbidden_terminal_punctuation"])
    for caption in captions:
        if not caption:
            continue
        terminal = caption.rstrip()
        while terminal.endswith("}"):
            terminal = terminal[:-1].rstrip()
        assert terminal and terminal[-1] not in forbidden, caption


def aux_label_number(aux: str, label: str) -> str:
    match = re.search(rf"\\newlabel\{{{re.escape(label)}\}}\{{\{{([^}}]+)\}}", aux)
    assert match, label
    return match.group(1)


def assert_main_case(layout: dict[str, object]) -> CaseArtifacts:
    source = MAIN_TEX.read_text(encoding="utf-8")
    class_source = (ROOT / "SZTUthesis.cls").read_text(encoding="utf-8")
    style_source = (ROOT / "gbt7714.sty").read_text(encoding="utf-8")
    bst_source = (ROOT / "gbt7714-numerical.bst").read_text(encoding="utf-8")
    assert "citecolor=black" in source
    assert "hypertexnames=false" in source
    assert "\\renewcommand{\\theequation}{\\thesection-\\arabic{equation}}" in source
    assert "\\renewcommand{\\contentsname}{\\hfill \\heiti \\zihao{-2} 目录\\hfill}" in source
    assert "Required font SimSun is missing" in class_source
    assert "Required font SimHei is missing" in class_source
    assert "Required font KaiTi is missing" in class_source
    assert "Required font Times New Roman is missing" in class_source
    assert "深圳技术大学本科毕业论文—\\titlecnSingleLine" in class_source
    assert "\\renewcommand{\\headrulewidth}{0.75pt}" in class_source
    assert "\\RequirePackage[sort&compress]{gbt7714}" in class_source
    assert "\\newcommand{\\setreference}[1][thesis-references]" in class_source
    assert "\\setlength{\\bibsep}{0pt}" in class_source
    assert "\\renewcommand{\\bibnumfmt}[1]" in class_source
    assert "\\renewcommand{\\bibfont}" in class_source
    assert "\\let\\url\\nolinkurl" in class_source
    assert "GB/T 7714—2015" in style_source
    assert "GB/T 7714—2015" in bst_source
    assert_caption_contract(layout)

    artifacts = compile_case(MAIN_TEX, "main")
    assert_clean_build(artifacts)
    assert_pdf_a4(artifacts.pdf)
    assert_required_fonts(
        artifacts.pdf,
        ("SimSun", "SimHei", "KaiTi", "STZhongsong", "TimesNewRoman"),
    )

    pages = extracted_pages(artifacts.pdf)
    chinese_index = page_index(pages, "【摘要】")
    english_index = page_index(pages, "【Abstract】")
    body_matches = [
        index
        for index, page in enumerate(pages)
        if "1.引言" in normalize(page)
        and HEADER_PREFIX in page
        and re.search(r"第\s*1\s*页\s*共\s*\d+\s*页", page)
    ]
    assert len(body_matches) == 1, body_matches
    body_index = body_matches[0]
    chinese = pages[chinese_index]
    english = pages[english_index]
    body = pages[body_index]
    assert "【关键词】" in chinese
    assert "【Key words】" in english
    assert HEADER_PREFIX not in chinese
    assert HEADER_PREFIX in english
    assert HEADER_PREFIX in body
    assert normalize(chinese).endswith("I")
    assert normalize(english).endswith("II")
    assert re.search(r"第\s*1\s*页\s*共\s*\d+\s*页", body)
    assert "，共" not in body

    toc_text = artifacts.toc.read_text(encoding="utf-8", errors="replace")
    assert re.search(r"\\contentsline \{section\}\{摘要\}\{I\}", toc_text)
    assert re.search(r"\\contentsline \{section\}\{Abstract\}\{II\}", toc_text)
    assert "【摘要】" not in toc_text
    assert "【Abstract】" not in toc_text
    toc_page = next(page for page in pages if "目录" in page and "Abstract" in page)
    assert "【摘要】" not in toc_page
    assert "【Abstract】" not in toc_page
    assert "目 录" not in toc_page

    aux = artifacts.aux.read_text(encoding="utf-8", errors="replace")
    assert aux_label_number(aux, "E.chapter-two") == "2-1"
    assert aux_label_number(aux, "E.example") == "4-1"
    extracted = "\n".join(pages)
    assert "(2-1)" in extracted
    assert "(4-1)" in extracted
    assert "(2.1)" not in extracted
    assert "(4.1)" not in extracted

    chinese_png = render_page(
        artifacts.pdf, chinese_index + 1, artifacts.directory / "chinese-abstract"
    )
    english_png = render_page(
        artifacts.pdf, english_index + 1, artifacts.directory / "english-abstract"
    )
    assert not has_header_rule(chinese_png), "Chinese abstract must not have a header rule"
    assert has_header_rule(english_png), "English abstract must have a header rule"
    assert_cjk_gate(artifacts.pdf)
    return artifacts


def bbl_keys(bbl: str) -> list[str]:
    return re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", bbl)


def bbox_lines(pdf: Path, output: Path) -> list[dict[str, object]]:
    run([require_command("pdftotext"), "-bbox-layout", str(pdf), str(output)])
    root = ET.parse(output).getroot()
    lines: list[dict[str, object]] = []
    for page_number, page in enumerate(root.findall(".//{*}page"), start=1):
        page_width = float(page.attrib["width"])
        for line in page.findall(".//{*}line"):
            words: list[dict[str, object]] = []
            for word in line.findall("./{*}word"):
                words.append(
                    {
                        "text": "".join(word.itertext()),
                        "x_min": float(word.attrib["xMin"]),
                        "x_max": float(word.attrib["xMax"]),
                        "y_min": float(word.attrib["yMin"]),
                        "y_max": float(word.attrib["yMax"]),
                    }
                )
            if words:
                lines.append(
                    {
                        "page": page_number,
                        "page_width": page_width,
                        "x_min": float(line.attrib["xMin"]),
                        "x_max": float(line.attrib["xMax"]),
                        "y_min": float(line.attrib["yMin"]),
                        "y_max": float(line.attrib["yMax"]),
                        "words": words,
                    }
                )
    return sorted(lines, key=lambda item: (item["page"], item["y_min"], item["x_min"]))


def word_index(line: dict[str, object], token: str) -> int | None:
    for index, word in enumerate(line["words"]):
        if word["text"] == token:
            return index
    return None


def assert_bibliography_geometry(
    artifacts: CaseArtifacts, reference_start_page: int
) -> None:
    lines = bbox_lines(artifacts.pdf, artifacts.directory / "bibliography-bbox.html")
    body_lines = [
        line
        for line in lines
        if line["page"] >= reference_start_page and 70.0 < line["y_min"] < 785.0
    ]

    first_index = next(
        index for index, line in enumerate(body_lines) if word_index(line, "[1]") is not None
    )
    second_index = next(
        index for index, line in enumerate(body_lines) if word_index(line, "[2]") is not None
    )
    first_line = body_lines[first_index]
    label_index = word_index(first_line, "[1]")
    assert label_index is not None
    label_word = first_line["words"][label_index]
    first_content_word = first_line["words"][label_index + 1]
    content_x = first_content_word["x_min"]
    continuation = body_lines[first_index + 1 : second_index]
    assert len(continuation) >= 2
    for line in continuation:
        assert abs(line["x_min"] - content_x) <= 0.6, (line["x_min"], content_x)

    first_item_lines = [first_line, *continuation]
    within_steps = [
        later["y_min"] - earlier["y_min"]
        for earlier, later in zip(first_item_lines, first_item_lines[1:])
        if earlier["page"] == later["page"]
    ]
    assert within_steps
    line_step = statistics.median(within_steps)
    assert 18.0 <= line_step <= 20.5, line_step
    second_line = body_lines[second_index]
    item_gap = second_line["y_min"] - first_item_lines[-1]["y_min"]
    assert item_gap <= line_step * 1.25, (item_gap, line_step)

    label_height = label_word["y_max"] - label_word["y_min"]
    content_height = first_content_word["y_max"] - first_content_word["y_min"]
    assert label_height >= content_height + 0.2, (label_height, content_height)

    page_width = first_line["page_width"]
    right_margin_pt = 31.7 * 72.0 / 25.4
    right_limit = page_width - right_margin_pt + 1.6
    for line in body_lines:
        for word in line["words"]:
            assert word["x_max"] <= right_limit, (
                word["text"],
                word["x_max"],
                right_limit,
            )

    ten_index = next(
        index for index, line in enumerate(body_lines) if word_index(line, "[10]") is not None
    )
    eleven_index = next(
        index for index, line in enumerate(body_lines) if word_index(line, "[11]") is not None
    )
    ten_line = body_lines[ten_index]
    ten_label_index = word_index(ten_line, "[10]")
    assert ten_label_index is not None
    ten_content_x = ten_line["words"][ten_label_index + 1]["x_min"]
    next_page_continuations = [
        line
        for line in body_lines[ten_index + 1 : eleven_index]
        if line["page"] > ten_line["page"]
    ]
    assert next_page_continuations
    assert abs(next_page_continuations[0]["x_min"] - ten_content_x) <= 0.6


def assert_stress_case(layout: dict[str, object]) -> CaseArtifacts:
    artifacts = compile_case(STRESS_TEX, "bibliography-stress")
    assert_clean_build(artifacts)
    assert_pdf_a4(artifacts.pdf)
    assert_required_fonts(
        artifacts.pdf, ("SimSun", "SimHei", "KaiTi", "TimesNewRoman")
    )

    expected_keys = [
        "synthetic-article-cn",
        "synthetic-book-en",
        "synthetic-thesis-cn",
        "synthetic-patent-cn",
        "synthetic-standard-cn",
        "synthetic-conference-en",
        "synthetic-long-article-en",
        "synthetic-online-cn",
        "synthetic-report-en",
        "synthetic-dataset-en",
        "synthetic-database-cn",
        "synthetic-dissertation-en",
        "synthetic-proceedings-cn",
        "synthetic-online-en",
    ]
    bbl = artifacts.bbl.read_text(encoding="utf-8", errors="replace")
    assert bbl_keys(bbl) == expected_keys
    assert len(expected_keys) >= layout["references"]["minimum_entries"]
    for marker in (
        "[J/OL]",
        "[M]",
        "[D]",
        "[P]",
        "[S]",
        "[C/OL]",
        "[EB/OL]",
        "[R/OL]",
        "[DS/OL]",
        "[DB/OL]",
        "[C]",
    ):
        assert marker in bbl, marker
    assert "10.0000/" in bbl
    assert "example.invalid" in bbl

    pages = extracted_pages(artifacts.pdf)
    assert len(pages) == 3, len(pages)
    body = normalize(pages[0])
    assert "[1-3]" in body
    assert "[1,3,5]" in body
    assert body.count("[1]") >= 1
    reference_indexes = [
        index
        for index, page in enumerate(pages)
        if re.search(r"(?m)^\s*参考文献\s*$", page)
    ]
    assert reference_indexes == [1], reference_indexes
    reference_start = reference_indexes[0]
    assert "[10]" in pages[reference_start]
    assert "[14]" in pages[-1]
    assert len(pages) - reference_start >= 2
    for page in pages[reference_start:]:
        assert HEADER_PREFIX in page
        assert re.search(r"第\s*\d+\s*页\s*共\s*\d+\s*页", page)

    assert_bibliography_geometry(artifacts, reference_start + 1)
    for page_number in range(reference_start + 1, len(pages) + 1):
        render_page(
            artifacts.pdf,
            page_number,
            artifacts.directory / f"reference-page-{page_number}",
        )
    assert_cjk_gate(artifacts.pdf)
    return artifacts


def main() -> int:
    layout = json.loads((THESIS_DIR / "spec/layout.json").read_text(encoding="utf-8"))
    assert layout["page"] == {
        "width_mm": 210.0,
        "height_mm": 297.0,
        "top_margin_mm": 25.4,
        "bottom_margin_mm": 25.4,
        "left_margin_mm": 31.7,
        "right_margin_mm": 31.7,
        "header_distance_mm": 15.0,
        "footer_distance_mm": 17.5,
    }
    assert layout["fonts"]["fallback_allowed"] is False
    assert layout["header"]["chinese_abstract_visible"] is False
    assert layout["header"]["chinese_abstract_rule_visible"] is False
    assert layout["header"]["english_abstract_visible"] is True
    assert layout["header"]["english_abstract_rule_visible"] is True
    assert layout["headings"]["toc_title"] == "目录"
    assert layout["headings"]["chapter_number_suffix"] == "."
    assert layout["abstracts"]["body_labels"] == [
        "【摘要】",
        "【关键词】",
        "【Abstract】",
        "【Key words】",
    ]
    assert layout["abstracts"]["toc_labels"] == ["摘要", "Abstract"]
    assert layout["abstracts"]["toc_labels_bracketed"] is False
    assert layout["numbering"]["equation_pattern"] == "{chapter}-{item}"
    assert layout["captions"]["terminal_punctuation_allowed"] is False
    references = layout["references"]
    assert references["standard"] == "GB/T 7714-2015"
    assert references["style"] == "numerical"
    assert references["sort_order"] == "first_citation"
    assert references["item_spacing_pt"] == 0.0
    assert references["hanging_indent_mode"] == "align_continuation_with_entry_text"
    assert references["line_spacing"] == 1.5
    assert references["citation_position"] == "superscript"
    assert references["citation_color"] == "000000"
    assert references["minimum_entries"] == 10
    assert references["minimum_foreign_entries"] == 2

    main_case = assert_main_case(layout)
    stress_case = assert_stress_case(layout)
    print(
        "PASS: calibrated thesis template "
        f"({len(extracted_pages(main_case.pdf))} pages) and bibliography stress fixture "
        f"({len(extracted_pages(stress_case.pdf))} pages)"
    )
    print(f"  main: {main_case.pdf}")
    print(f"  bibliography: {stress_case.pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
