#!/usr/bin/env python3
"""Render the proposal LaTeX bundle from the same JSON used by Word."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


FONT_SPECS = {
    "SimSun": ("SZTU_SIMSUN_FONT", ("simsun.ttf", "simsun.ttc")),
    "SimHei": ("SZTU_SIMHEI_FONT", ("simhei.ttf",)),
    "Times New Roman": (
        "SZTU_TIMES_REGULAR_FONT",
        ("Times New Roman.ttf", "times.ttf"),
    ),
    "Times New Roman Bold": (
        "SZTU_TIMES_BOLD_FONT",
        ("Times New Roman Bold.ttf", "timesbd.ttf"),
    ),
    "Times New Roman Italic": (
        "SZTU_TIMES_ITALIC_FONT",
        ("Times New Roman Italic.ttf", "timesi.ttf"),
    ),
    "Times New Roman Bold Italic": (
        "SZTU_TIMES_BOLD_ITALIC_FONT",
        ("Times New Roman Bold Italic.ttf", "timesbi.ttf"),
    ),
}


def _load_word_renderer(script_dir: Path):
    renderer_path = script_dir.parent / "word" / "render.py"
    spec = importlib.util.spec_from_file_location("proposal_word_renderer", renderer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load shared validator: {renderer_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _font_roots(script_dir: Path) -> list[Path]:
    roots = [script_dir.parent / "fonts.local"]
    extra = os.environ.get("SZTU_FONT_DIR")
    if extra:
        roots.extend(Path(item).expanduser() for item in extra.split(os.pathsep) if item)
    if sys.platform == "darwin":
        roots.extend(
            [
                Path.home() / "Library" / "Fonts",
                Path("/Library/Fonts"),
                Path("/System/Library/Fonts"),
                Path("/System/Library/Fonts/Supplemental"),
            ]
        )
    elif os.name == "nt":
        roots.append(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")
    else:
        roots.extend(
            [
                Path.home() / ".local" / "share" / "fonts",
                Path.home() / ".fonts",
                Path("/usr/local/share/fonts"),
                Path("/usr/share/fonts"),
            ]
        )
    unique: list[Path] = []
    for root in roots:
        resolved = root.expanduser()
        if resolved.is_dir() and resolved not in unique:
            unique.append(resolved)
    return unique


def resolve_font_files(script_dir: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for root in _font_roots(script_dir):
        for path in root.rglob("*"):
            if path.is_file():
                index.setdefault(path.name.casefold(), path.resolve())

    resolved: dict[str, Path] = {}
    missing: list[str] = []
    for family, (environment_key, candidates) in FONT_SPECS.items():
        override = os.environ.get(environment_key)
        if override:
            path = Path(override).expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError(f"{environment_key} does not point to a font file: {path}")
            resolved[family] = path
            continue
        path = next((index[name.casefold()] for name in candidates if name.casefold() in index), None)
        if path is None:
            missing.append(f"{family} ({'/'.join(candidates)})")
        else:
            resolved[family] = path
    if missing:
        raise FileNotFoundError(
            "required official fonts are missing; font substitution is forbidden: "
            + ", ".join(missing)
        )
    return resolved


def _font_parts(path: Path) -> tuple[str, str]:
    directory = path.parent.as_posix().rstrip("/") + "/"
    filename = path.name
    if any(character in directory + filename for character in ("{", "}", "%", "#")):
        raise ValueError(f"font path contains unsupported TeX characters: {path}")
    return directory, filename


def fonts_tex(fonts: dict[str, Path]) -> str:
    simsun_dir, simsun = _font_parts(fonts["SimSun"])
    simhei_dir, simhei = _font_parts(fonts["SimHei"])
    times_dir, times = _font_parts(fonts["Times New Roman"])
    times_bold_dir, times_bold = _font_parts(fonts["Times New Roman Bold"])
    times_italic_dir, times_italic = _font_parts(fonts["Times New Roman Italic"])
    times_bold_italic_dir, times_bold_italic = _font_parts(
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


def _has_explicit_numbering(runs: list[dict]) -> bool:
    text = "".join(run["text"] for run in runs).lstrip()
    return re.match(r"^(?:第[一二三四五六七八九十]+阶段|[（(]?\d+[）)、.])", text) is not None


def numbered_paragraphs(items: list[list[dict]], *, shared) -> str:
    rendered_items = []
    for index, item in enumerate(items, start=1):
        split_item = shared.split_numbered_subitems(item)
        lead = split_item[0] if split_item else item
        rendered = rich_runs(lead) if _has_explicit_numbering(lead) else rf"{index}、{rich_runs(lead)}"
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


def data_tex(data: dict, *, shared) -> str:
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
        "MethodsAndMeans": numbered_paragraphs(
            sections["methods_and_means"], shared=shared
        ),
        "ResearchSteps": numbered_paragraphs(sections["research_steps"], shared=shared),
        "ReferencesContent": paragraphs(sections["references"], indent=False),
    }
    lines = ["% Generated file. Edit the JSON source, not this file."]
    lines.extend(f"\\long\\def\\{name}{{{value}}}" for name, value in macros.items())
    return "\n".join(lines) + "\n"


def render(data_path: Path, output_dir: Path, *, overwrite: bool, compile_pdf: bool) -> Path:
    script_dir = Path(__file__).resolve().parent
    shared = _load_word_renderer(script_dir)
    data = shared.validate_data(json.loads(data_path.read_text(encoding="utf-8")))
    fonts = resolve_font_files(script_dir)

    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"output directory is not empty; pass --overwrite: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "proposal-data.tex").write_text(
        data_tex(data, shared=shared), encoding="utf-8"
    )
    (output_dir / "proposal-fonts.tex").write_text(fonts_tex(fonts), encoding="utf-8")
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
            fonts = resolve_font_files(Path(__file__).resolve().parent)
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
