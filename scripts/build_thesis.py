#!/usr/bin/env python3
"""跨平台论文编译入口，只使用 Python 标准库，不需要桌面工作台。"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-fonts', action='store_true', help='仅检查并保存本机字体配置')
    parser.add_argument('--font-dir', type=Path, help='合法字体所在文件夹，允许含空格')
    args = parser.parse_args()
    # 使用当前 Python 运行字体检查；路径作为参数传入，不拼接 shell 命令。
    command = [sys.executable, str(ROOT / 'scripts/check_fonts.py')]
    if args.font_dir:
        command += ['--font-dir', str(args.font_dir.expanduser().resolve())]
    try:
        subprocess.run(command, cwd=ROOT, check=True)
        if args.check_fonts:
            return 0
        flags = ['-no-shell-escape', '-interaction=nonstopmode', '-file-line-error', '-halt-on-error']
        if shutil.which('latexmk'):
            subprocess.run(['latexmk', '-xelatex', *flags, 'sztuthesis_main.tex'], cwd=ROOT, check=True)
        else:
            # 没有 latexmk 时使用标准四步链；任何一步失败立即停止。
            for name in ('xelatex', 'bibtex'):
                if not shutil.which(name):
                    raise RuntimeError(f'未找到 {name}，请安装 TeX Live/MacTeX 并检查 PATH。')
            xelatex = ['xelatex', *flags, 'sztuthesis_main.tex']
            for step in (xelatex, ['bibtex', 'sztuthesis_main'], xelatex, xelatex):
                subprocess.run(step, cwd=ROOT, check=True)
        print('编译完成：sztuthesis_main.pdf。请继续核对内容、引用和逐页版式。')
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'编译未完成：{exc}\n请查看上方首个错误；已有 PDF 可能是旧结果。', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
