#!/usr/bin/env python3
"""Fail when a PDF text layer contains CJK words whose glyph areas render blank."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - dependency error path
    raise SystemExit("ERROR: Pillow is required (import PIL failed).") from exc


CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
TRAILING_NUMBER_RE = re.compile(r"-(\d+)\.png$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare CJK word boxes in a PDF text layer with a fresh raster render. "
            "This catches missing-glyph/font-substitution renders before visual review."
        )
    )
    parser.add_argument("pdf", type=Path, help="PDF to validate")
    parser.add_argument("--dpi", type=int, default=180, help="render DPI (default: 180)")
    parser.add_argument(
        "--min-cjk-words",
        type=int,
        default=8,
        help="minimum CJK words required for a meaningful gate (default: 8)",
    )
    parser.add_argument(
        "--min-visible-rate",
        type=float,
        default=0.80,
        help="minimum fraction of CJK word boxes containing visible ink (default: 0.80)",
    )
    parser.add_argument(
        "--min-ink-ratio",
        type=float,
        default=0.006,
        help="minimum dark-pixel ratio for a word box to count as visible (default: 0.006)",
    )
    return parser.parse_args()


def require_command(name: str) -> str:
    path = shutil.which(name)
    if not path:
        print(f"ERROR: required command not found: {name}", file=sys.stderr)
        raise SystemExit(2)
    return path


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        print(f"ERROR: command failed: {' '.join(command)}", file=sys.stderr)
        if details:
            print(details, file=sys.stderr)
        raise SystemExit(2)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def rendered_pages(render_dir: Path) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for path in render_dir.glob("page-*.png"):
        match = TRAILING_NUMBER_RE.search(path.name)
        if match:
            result[int(match.group(1))] = path
    return result


def ink_ratio(image: Image.Image, box: tuple[int, int, int, int]) -> float:
    crop = image.crop(box).convert("L")
    if crop.width == 0 or crop.height == 0:
        return 0.0
    histogram = crop.histogram()
    dark_pixels = sum(histogram[:245])
    return dark_pixels / (crop.width * crop.height)


def main() -> int:
    args = parse_args()
    pdf = args.pdf.resolve()
    if not pdf.is_file():
        print(f"ERROR: PDF not found: {pdf}", file=sys.stderr)
        return 2
    if args.dpi < 150:
        print("ERROR: --dpi must be at least 150 for the CJK glyph gate.", file=sys.stderr)
        return 2
    if not 0 < args.min_visible_rate <= 1:
        print("ERROR: --min-visible-rate must be in (0, 1].", file=sys.stderr)
        return 2

    pdftotext = require_command("pdftotext")
    pdftocairo = require_command("pdftocairo")

    with tempfile.TemporaryDirectory(prefix="cjk-render-gate-") as temp_name:
        temp_dir = Path(temp_name)
        bbox_path = temp_dir / "bbox.html"
        render_dir = temp_dir / "render"
        render_dir.mkdir()

        run([pdftotext, "-bbox-layout", str(pdf), str(bbox_path)])
        run([pdftocairo, "-png", "-r", str(args.dpi), str(pdf), str(render_dir / "page")])

        try:
            root = ET.parse(bbox_path).getroot()
        except (ET.ParseError, OSError) as exc:
            print(f"ERROR: could not parse pdftotext bbox output: {exc}", file=sys.stderr)
            return 2

        pages = [element for element in root.iter() if local_name(element.tag) == "page"]
        images = rendered_pages(render_dir)
        total = 0
        visible = 0
        blank_samples: list[str] = []

        for page_number, page in enumerate(pages, start=1):
            image_path = images.get(page_number)
            if not image_path:
                print(f"ERROR: missing raster page {page_number}", file=sys.stderr)
                return 2
            page_width = float(page.attrib["width"])
            page_height = float(page.attrib["height"])
            with Image.open(image_path) as image:
                scale_x = image.width / page_width
                scale_y = image.height / page_height
                for word in page.iter():
                    if local_name(word.tag) != "word":
                        continue
                    text = "".join(word.itertext()).strip()
                    if not CJK_RE.search(text):
                        continue
                    x_min = max(0, int(float(word.attrib["xMin"]) * scale_x) - 1)
                    y_min = max(0, int(float(word.attrib["yMin"]) * scale_y) - 1)
                    x_max = min(image.width, int(float(word.attrib["xMax"]) * scale_x) + 2)
                    y_max = min(image.height, int(float(word.attrib["yMax"]) * scale_y) + 2)
                    if x_max - x_min < 2 or y_max - y_min < 2:
                        continue
                    total += 1
                    ratio = ink_ratio(image, (x_min, y_min, x_max, y_max))
                    if ratio >= args.min_ink_ratio:
                        visible += 1
                    elif len(blank_samples) < 8:
                        blank_samples.append(f"p{page_number}:{text[:16]}")

        if total < args.min_cjk_words:
            print(
                f"INCONCLUSIVE: found only {total} CJK word boxes; "
                f"at least {args.min_cjk_words} are required.",
                file=sys.stderr,
            )
            return 2

        visible_rate = visible / total
        print(
            f"CJK render gate: pages={len(pages)} words={total} "
            f"visible={visible} blank={total - visible} rate={visible_rate:.1%}"
        )
        if visible_rate < args.min_visible_rate:
            if blank_samples:
                print("Blank CJK samples: " + ", ".join(blank_samples), file=sys.stderr)
            print(
                "FAIL: the PDF text layer contains Chinese, but too many corresponding "
                "raster regions are blank. Stop visual QA and fix fonts/rendering.",
                file=sys.stderr,
            )
            return 1

        print("PASS: Chinese glyph regions are visibly rendered; full-page QA may continue.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
