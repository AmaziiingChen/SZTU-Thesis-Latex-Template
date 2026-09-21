#!/usr/bin/env python3
"""Check thesis fonts and save a local XeLaTeX configuration for CLI/editors."""
from __future__ import annotations
import argparse
import os
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'templates'))
from common.python.font_files import discover_font_files, tex_font_parts
from common.python.typography import load_font_policy

FONTS = {
    'SimSun': ('cjkmain', '宋体'), 'SimHei': ('cjksans', '黑体'),
    'KaiTi': ('cjkkai', '楷体'), 'STZhongsong': ('zhongsong', '华文中宋'),
    'Times New Roman': ('times', '西文常规'),
    'Times New Roman Bold': ('timesbold', '西文粗体'),
    'Times New Roman Italic': ('timesitalic', '西文斜体'),
    'Times New Roman Bold Italic': ('timesbolditalic', '西文粗斜体'),
}


def write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding='utf-8') == content:
        return
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            name = stream.name
            stream.write(content)
        os.replace(name, path)
    finally:
        if name and Path(name).exists():
            Path(name).unlink()


def check(directory: Path | None, *, save: bool) -> int:
    config = ROOT / 'sztu-fonts.local.tex'
    preference = ROOT / 'sztu-fonts.local.json'
    if directory is None and not os.environ.get('SZTU_FONT_DIR') and preference.exists():
        try:
            saved = json.loads(preference.read_text(encoding='utf-8')).get('font_dir')
            if saved:
                remembered = Path(saved)
                if remembered.is_dir():
                    directory = remembered
                else:
                    print(f'原字体目录已不存在：{remembered}；正在重新自动查找。')
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            print(f'本机字体设置无法读取：{exc}。请用 --font-dir 重新指定目录。', file=sys.stderr)
            return 2
    if directory is not None and not directory.is_dir():
        print(f'字体文件夹不存在：{directory}\n请检查路径，含空格的路径请加引号。', file=sys.stderr)
        return 2
    try:
        fonts, missing = discover_font_files(list(FONTS), local_font_dir=directory)
        # Legacy root files remain a last resort, below explicit and system roots.
        definitions = load_font_policy()['font_files']
        for key in FONTS.keys() - fonts.keys():
            for name in definitions[key]['candidates']:
                candidate = ROOT / name
                if candidate.is_file():
                    fonts[key] = candidate.resolve()
                    break
        missing = [item for item in missing if item.split(' (', 1)[0] not in fonts]
        for key, (_, label) in FONTS.items():
            print(f"{'已找到' if key in fonts else '缺失'}  {label} / {key}" + (f'\n        {fonts[key]}' if key in fonts else ''))
        if missing:
            print('\n尚不能编译：请安装上述缺失字体，或指定已有字体所在文件夹：\n'
                  '  python3 scripts/check_fonts.py --font-dir "/你的字体文件夹"\n'
                  '也可以把字体放到项目的 fonts.local/ 后重试。\n'
                  'Mac 可用“字体册”安装；Windows 可右键字体文件安装。\n'
                  '已有 PDF 和本机配置保持不变；本次没有生成新 PDF。', file=sys.stderr)
            return 1
        engine = shutil.which('xelatex')
        if not engine:
            print('字体已找到，但缺少 xelatex，尚未验证可加载。请安装 TeX Live/MacTeX 并将其加入 PATH。', file=sys.stderr)
            return 1
        paths = {}
        for key, path in fonts.items():
            tex_font_parts(path)  # Reject TeX metacharacters before writing executable TeX.
            value = path.as_posix()
            if any(c in value for c in ('\\', '$', '&', '^', '~', '\n', '\r')):
                raise ValueError(f'字体路径含 TeX 不支持的字符，请移到普通目录：{path}')
            paths[key] = value
        with tempfile.TemporaryDirectory(prefix='sztu-font-check-') as temp:
            folder = Path(temp)
            probe = '\\documentclass{article}\n\\usepackage{fontspec}\n\\begin{document}\n'
            probe += '\n'.join(r'{\fontspec[Path={' + tex_font_parts(Path(path))[0] + '}]{' + Path(path).name + '}A}' for path in paths.values())
            probe += '\n\\end{document}\n'
            (folder / 'fonts.tex').write_text(probe, encoding='utf-8')
            result = subprocess.run([engine, '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error', 'fonts.tex'], cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90)
            if result.returncode:
                logdir = ROOT / 'tmp/font-check'; logdir.mkdir(parents=True, exist_ok=True)
                (logdir / 'latest.log').write_text(result.stdout, encoding='utf-8')
                print(f'字体文件存在，但 XeLaTeX 加载失败。请检查文件是否有效。详情：{logdir / "latest.log"}', file=sys.stderr)
                return 1
        if save:
            lines = ['% Generated local font paths. Do not commit; rerun scripts/check_fonts.py on a new computer.']
            for key, value in paths.items():
                directory_part, filename = tex_font_parts(Path(value))
                suffix = FONTS[key][0]
                lines += [r'\def\sztu@font@' + suffix + '{' + filename + '}',
                          r'\def\sztu@path@' + suffix + '{' + directory_part + '}']
            lines += [r'\sztu@configuredtrue']
            # Preserve timestamps when unchanged so latexmk stays incremental.
            write_if_changed(config, '\n'.join(lines) + '\n')
            write_if_changed(preference, json.dumps({'font_dir': str(directory) if directory else None}, ensure_ascii=False) + '\n')
            print(f'\n字体检查通过，已保存本机配置：{config.name}\n可运行 bash build.sh，或在 Texifier/TeXstudio 中选择 XeLaTeX 编译。')
        else:
            print('\n字体检查通过（未修改本机配置）。')
        print('Word/WPS 仍需能识别相应的已安装字体；此检查不代表文档版式已验收。')
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f'字体检查未通过：{exc}\n请检查字体路径后重试；已有 PDF 保持不变。', file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-dir', type=lambda s: Path(s).expanduser().resolve(), help='已有字体所在目录；成功后保存解析结果供编辑器使用')
    parser.add_argument('--no-save', action='store_true', help='仅检查，不保存本机配置')
    args = parser.parse_args()
    return check(args.font_dir, save=not args.no_save)

if __name__ == '__main__':
    raise SystemExit(main())
