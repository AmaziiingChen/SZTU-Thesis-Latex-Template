#!/usr/bin/env python3
"""Fail when a PDF text layer contains CJK text whose page areas render blank.

Every external call is chosen so that a non-ASCII working directory is safe:

* page images are written by ``pdftoppm`` (``_wfopen`` on Windows, so it accepts
  a Chinese user name or a localized ``%TEMP%``); ``pdftocairo`` writes through a
  bare ``fopen`` and must not be used for such paths;
* ``pdftotext`` never writes a file: its output is read from stdout, because the
  file path it writes is also opened with a bare ``fopen``;
* ``-bbox-layout`` is optional. The Xpdf 4.x ``pdftotext`` that ships with some
  offline runtimes rejects it, so the gate falls back to a page-level ink check
  instead of failing the export.
"""

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
CJK_WORD_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
TRAILING_NUMBER_RE = re.compile(r"-(\d+)\.png$")


class ToolFailure(RuntimeError):
    """A required external tool exited with a non-zero status."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare CJK text in a PDF with a fresh raster render. This catches "
            "missing-glyph/font-substitution renders before visual review."
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


def decode_output(value: bytes) -> str:
    """Decode child-process output without depending on the Windows ANSI code page."""
    return value.decode("utf-8", errors="replace")


def run(command: list[str]) -> bytes:
    """Run an external tool and return its raw stdout.

    Output is captured as bytes: on Windows the parent process may use a legacy
    ANSI code page (for example GBK), while the PDF tools emit UTF-8.
    """
    completed = subprocess.run(command, capture_output=True, check=False)
    if completed.returncode != 0:
        details = decode_output(completed.stderr).strip() or decode_output(
            completed.stdout
        ).strip()
        raise ToolFailure(f"{' '.join(command)}\n{details}".strip())
    return completed.stdout


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


def bbox_pages(pdftotext: str, pdf: Path) -> list[ET.Element] | None:
    """Return the ``<page>`` elements, or None when the tool lacks -bbox-layout."""
    try:
        xml = run([pdftotext, "-enc", "UTF-8", "-bbox-layout", str(pdf), "-"])
    except ToolFailure:
        return None
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None
    return [element for element in root.iter() if local_name(element.tag) == "page"]


def measure_bbox(
    pages: list[ET.Element],
    images: dict[int, Path],
    args: argparse.Namespace,
) -> tuple[int, int, list[str]] | None:
    total = 0
    visible = 0
    blank_samples: list[str] = []
    for page_number, page in enumerate(pages, start=1):
        image_path = images.get(page_number)
        if not image_path:
            print(f"ERROR: missing raster page {page_number}", file=sys.stderr)
            return None
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
                if ink_ratio(image, (x_min, y_min, x_max, y_max)) >= args.min_ink_ratio:
                    visible += 1
                elif len(blank_samples) < 8:
                    blank_samples.append(f"p{page_number}:{text[:16]}")
    return total, visible, blank_samples


def measure_pages(
    pdftotext: str,
    pdf: Path,
    images: dict[int, Path],
    args: argparse.Namespace,
) -> tuple[int, int, list[str]]:
    """Page-level fallback for tools without -bbox-layout."""
    text = decode_output(run([pdftotext, "-enc", "UTF-8", str(pdf), "-"]))
    page_texts = text.split("\f")
    while page_texts and not page_texts[-1].strip():
        page_texts.pop()
    total = 0
    visible = 0
    blank_samples: list[str] = []
    for page_number, page_text in enumerate(page_texts, start=1):
        words = CJK_WORD_RE.findall(page_text)
        if not words:
            continue
        total += len(words)
        image_path = images.get(page_number)
        if not image_path:
            print(f"ERROR: missing raster page {page_number}", file=sys.stderr)
            raise SystemExit(2)
        with Image.open(image_path) as image:
            if ink_ratio(image, (0, 0, image.width, image.height)) >= args.min_ink_ratio:
                visible += len(words)
            elif len(blank_samples) < 8:
                blank_samples.append(f"p{page_number}:{words[0][:16]}")
    return total, visible, blank_samples


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
    pdftoppm = require_command("pdftoppm")

    with tempfile.TemporaryDirectory(prefix="cjk-render-gate-") as temp_name:
        render_dir = Path(temp_name) / "render"
        render_dir.mkdir()
        try:
            run([pdftoppm, "-png", "-r", str(args.dpi), str(pdf), str(render_dir / "page")])
        except ToolFailure as failure:
            print(f"ERROR: command failed: {failure}", file=sys.stderr)
            return 2
        images = rendered_pages(render_dir)

        pages = bbox_pages(pdftotext, pdf)
        if pages is not None:
            measured = measure_bbox(pages, images, args)
            if measured is None:
                return 2
            total, visible, blank_samples = measured
            page_count = len(pages)
            print("CJK render gate: mode=word-boxes")
        else:
            print(
                "WARNING: pdftotext has no -bbox-layout support; "
                "falling back to the page-level ink check.",
                file=sys.stderr,
            )
            total, visible, blank_samples = measure_pages(pdftotext, pdf, images, args)
            page_count = len(images)
            print("CJK render gate: mode=page-ink")

        if total < args.min_cjk_words:
            print(
                f"INCONCLUSIVE: found only {total} CJK words; "
                f"at least {args.min_cjk_words} are required.",
                file=sys.stderr,
            )
            return 2

        visible_rate = visible / total
        print(
            f"CJK render gate: pages={page_count} words={total} "
            f"visible={visible} blank={total - visible} rate={visible_rate:.1%}"
        )
        if visible_rate < args.min_visible_rate:
            if blank_samples:
                print("Blank CJK samples: " + ", ".join(blank_samples), file=sys.stderr)
            print(
                "FAIL: the PDF text layer contains Chinese, but too many corresponding "
                "areas are blank. Stop visual QA and fix fonts/rendering.",
                file=sys.stderr,
            )
            return 1

        print("PASS: Chinese glyph regions are visibly rendered; full-page QA may continue.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
