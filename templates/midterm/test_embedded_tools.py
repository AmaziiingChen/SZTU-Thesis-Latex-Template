#!/usr/bin/env python3
"""Regression for editor-inserted tables and multi-row figures, including PDF overflow."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path(__file__).resolve().parent
OUTPUT = ROOT / 'tmp' / 'embedded-tools-regression'


def main():
    fixture = json.loads((TEMPLATE / 'fixtures/embedded-tools.json').read_text())
    for block in fixture['sections']['progress']:
        if isinstance(block, dict) and block.get('type') == 'figure_group':
            for item in block['items']:
                item['path'] = str(TEMPLATE / 'fixtures' / item['path'])
    stress = copy.deepcopy(fixture)
    stress['sections']['main_research_content'] = [
        {**stress['sections']['main_research_content'][1], 'rows': [
            {'cells': [f'ROW-{index:02d}', f'{index}.25']} for index in range(40)
        ]}
    ]
    stress['sections']['progress'][1]['columns'] = 1
    for name, data in [('normal', fixture), ('long', stress)]:
        folder = OUTPUT / name
        folder.mkdir(parents=True, exist_ok=True)
        source = folder / 'input.json'
        source.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        result = subprocess.run([sys.executable, str(TEMPLATE / 'render.py'), '--data', str(source), '--output-dir', str(folder), '--format', 'all', '--compile', '--overwrite'], capture_output=True, text=True)
        (folder / 'render.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stderr
        pdf = folder / 'latex/main.pdf'
        with pdfplumber.open(pdf) as doc:
            text = '\n'.join(page.extract_text() or '' for page in doc.pages)
            assert '组合图排版测试' in text
            for page in doc.pages:
                for char in page.chars:
                    assert char['top'] >= 0 and char['bottom'] <= page.height, (name, page.page_number, char)
            if name == 'long':
                for index in range(40):
                    assert f'ROW-{index:02d}' in text
        subprocess.run([sys.executable, str(ROOT/'scripts/validate_cjk_render.py'), str(pdf)], check=True)
        source_tex = (folder / 'latex/midterm-data.tex').read_text()
        assert 'hline{1,2,Z}' in source_tex
        if name == 'long':
            assert source_tex.count('hline{1,2,Z}') == 5
        print(f'{name}: embedded tools Word/PDF regression passed')


if __name__ == '__main__':
    main()
