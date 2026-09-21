#!/usr/bin/env python3
"""Assert title clearance in generated DOCX and PDF samples (no private data).
Run after rendering title-two-lines fixtures to tmp/title-padding/<name>/.
"""
import json
from pathlib import Path
import pdfplumber
from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[2]
for name, row_index in (("proposal", 0), ("midterm", 3)):
    spec = json.loads((ROOT / "templates" / name / "spec/layout.json").read_text())
    expected = round(spec["table"]["title_vertical_padding_mm"] / 25.4 * 1440)
    sample = ROOT / "tmp/title-padding" / name
    doc = Document(sample / f"{name}.docx")
    cell = doc.tables[0].rows[row_index].cells[1]
    for side in ("top", "bottom"):
        margin = cell._tc.find(f"{qn('w:tcPr')}/{qn('w:tcMar')}/{qn('w:' + side)}")
        assert int(margin.get(qn("w:w"))) == expected
    with pdfplumber.open(sample / "latex/main.pdf") as pdf:
        page = pdf.pages[0]
        bounds = page.find_tables()[0].rows[row_index].cells[1]
        chars = [c for c in page.chars if bounds[0] < c["x0"] < bounds[2] and bounds[1] < c["top"] < bounds[3]]
        assert len(set(round(c["top"], 1) for c in chars)) == 2, "Fixture must exercise two lines"
        top = min(c["top"] for c in chars) - bounds[1]
        bottom = bounds[3] - max(c["bottom"] for c in chars)
        # Glyph bounds vary slightly from line boxes. Require visible clearance,
        # not just the presence of the layout token in generated source.
        assert min(top, bottom) >= 3.8, (name, top, bottom)
        assert abs(top - bottom) < 1.0, (name, top, bottom)
        print(f"{name}: DOCX insets valid; PDF clearance {top:.2f}/{bottom:.2f} pt")
