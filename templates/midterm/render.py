#!/usr/bin/env python3
"""Generate the SZTU midterm Word and/or LaTeX artifacts from one JSON file."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


MIDTERM_DIR = Path(__file__).resolve().parent


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load renderer: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render(
    data_path: Path,
    output_dir: Path,
    *,
    output_format: str,
    overwrite: bool,
    compile_pdf: bool,
) -> list[Path]:
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(
            f"output directory is not empty; pass --overwrite: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    word_renderer = _load_module(MIDTERM_DIR / "word" / "render.py", "midterm_word")
    latex_renderer = _load_module(MIDTERM_DIR / "latex" / "render.py", "midterm_latex")

    # Validate once before either renderer writes output. Each renderer still validates
    # independently so direct invocation remains safe.
    word_renderer.validate_data(json.loads(data_path.read_text(encoding="utf-8")))

    if output_format in {"all", "word"}:
        outputs.append(
            word_renderer.render(
                MIDTERM_DIR / "word" / "official-template.docx",
                data_path,
                output_dir / "midterm.docx",
                overwrite=overwrite,
            )
        )
    if output_format in {"all", "latex"}:
        outputs.append(
            latex_renderer.render(
                data_path,
                output_dir / "latex",
                overwrite=overwrite,
                compile_pdf=compile_pdf,
            )
        )
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--format",
        choices=("all", "word", "latex"),
        default="all",
        dest="output_format",
    )
    parser.add_argument("--compile", action="store_true", dest="compile_pdf")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.compile_pdf and args.output_format == "word":
        parser.error("--compile is only valid for all or latex output")
    try:
        outputs = render(
            args.data,
            args.output_dir,
            output_format=args.output_format,
            overwrite=args.overwrite,
            compile_pdf=args.compile_pdf,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
