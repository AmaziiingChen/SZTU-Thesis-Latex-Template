#!/usr/bin/env python3
from pathlib import Path
import sys
TEMPLATES_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TEMPLATES_DIR))
from common.python.assessment_latex import latex_cli
from common.python.assessment_latex import render_bundle as _render
def render_bundle(data_path, output_dir, *, overwrite=False, compile_pdf=False):
    return _render("reviewer-review", data_path, output_dir, overwrite=overwrite, compile_pdf=compile_pdf)

if __name__ == "__main__":
    raise SystemExit(latex_cli("reviewer-review", Path(__file__).resolve().parents[1]))
