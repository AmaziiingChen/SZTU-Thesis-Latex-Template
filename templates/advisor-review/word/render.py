#!/usr/bin/env python3
from pathlib import Path
import sys
TEMPLATES_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TEMPLATES_DIR))
from common.python.assessment_word import word_cli
from common.python.assessment_word import render as _render
def render(template, data_path, output, *, overwrite=False):
    return _render("advisor-review", template, data_path, output, overwrite=overwrite)

if __name__ == "__main__":
    raise SystemExit(word_cli("advisor-review", Path(__file__).resolve().parents[1]))
