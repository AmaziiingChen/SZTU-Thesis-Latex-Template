#!/usr/bin/env python3
"""Render a structured thesis with the calibrated SZTU LaTeX template."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOKEN = re.compile(r"\{\{(fig|eq|cite):([A-Za-z0-9_:.+/-]{1,200})\}\}")
SAFE_KEY = re.compile(r"[A-Za-z0-9_:.+/-]{1,200}")
SAFE_ASSET = re.compile(r"[a-f0-9]{64}\.(?:png|jpg)")
MATH_COMMANDS = frozenset("frac dfrac tfrac sqrt sum prod int iint iiint lim sin cos tan cot sec csc log ln exp min max sup inf alpha beta gamma delta epsilon varepsilon theta vartheta lambda mu nu xi pi rho sigma tau phi varphi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Phi Psi Omega cdot times div pm mp leq geq neq approx equiv infty partial nabla text mathrm mathbf mathit operatorname left right overline underline hat bar vec dot ddot tilde widehat widetilde mathcal mathbb mathsf to in notin subset subseteq cup cap forall exists cdots ldots vdots dots quad qquad , ; : !".split())
TEX_ESCAPES = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "%": r"\%", "$": r"\$", "#": r"\#", "&": r"\&", "_": r"\_", "^": r"\textasciicircum{}", "~": r"\textasciitilde{}"}


def escape(value: str) -> str:
    return "".join(TEX_ESCAPES.get(char, char) for char in value)


def math_source(value: str) -> str:
    if not value.strip() or any(char in value for char in ("%", "#", "$", "&", "\x00")):
        raise ValueError("公式包含不支持的数学语法。")
    if value.count("{") != value.count("}"):
        raise ValueError("公式花括号不成对。")
    for token in re.findall(r"\\([A-Za-z]+|.)", value):
        if token not in MATH_COMMANDS:
            raise ValueError(f"公式命令不受支持：{token}")
    return value


def reference_text(value: str, targets: dict[str, set[str]]) -> str:
    remainder = TOKEN.sub("", value)
    if any(f"{{{{{kind}:" in remainder for kind in ("fig", "eq", "cite")):
        raise ValueError("引用标记格式无效。")
    result = []
    offset = 0
    for match in TOKEN.finditer(value):
        kind, key = match.groups()
        if key not in targets[kind]:
            raise ValueError(f"引用目标不存在：{kind}:{key}")
        result.append(escape(value[offset:match.start()]))
        result.append({"fig": rf"\ref{{fig:{key}}}", "eq": rf"\eqref{{eq:{key}}}", "cite": rf"\cite{{{key}}}"}[kind])
        offset = match.end()
    result.append(escape(value[offset:]))
    return "".join(result)


def paragraph(value: str | dict, targets: dict[str, set[str]]) -> str:
    if isinstance(value, str):
        return reference_text(value, targets)
    parts = []
    for run in value["runs"]:
        text = reference_text(run["text"], targets)
        if run.get("script") == "sub":
            text = rf"\textsubscript{{{text}}}"
        elif run.get("script") == "super":
            text = rf"\textsuperscript{{{text}}}"
        if run.get("italic"):
            text = rf"\textit{{{text}}}"
        if run.get("bold"):
            text = rf"\textbf{{{text}}}"
        parts.append(text)
    return "".join(parts)


def asset(path_text: str, assets_root: Path, output: Path) -> str:
    source = Path(path_text)
    if not source.is_absolute() or not SAFE_ASSET.fullmatch(source.name) or source.parent != assets_root or source.is_symlink() or not source.is_file():
        raise ValueError("图片不属于当前工作区的托管资源。")
    target = output / "assets" / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return f"assets/{source.name}"


def blocks(values: list, targets: dict[str, set[str]], assets_root: Path, output: Path, depth: int = 0) -> str:
    rendered = []
    for block in values:
        if isinstance(block, str) or block.get("type", "paragraph") == "paragraph":
            rendered.append(paragraph(block, targets) + "\n\n")
        elif block["type"] in ("ordered_list", "unordered_list"):
            kind = "enumerate" if block["type"] == "ordered_list" else "itemize"
            items = []
            for item in block["items"]:
                items.append(r"\item " + paragraph(item["content"], targets))
                if item.get("children"):
                    items.append(blocks([item["children"]], targets, assets_root, output, depth + 1))
            rendered.append(rf"\begin{{{kind}}}" + "\n" + "\n".join(items) + "\n" + rf"\end{{{kind}}}")
        elif block["type"] == "equation":
            rendered.append(r"\begin{equation}" + "\n" + math_source(block["latex"]) + "\n" + rf"\label{{eq:{block['id']}}}" + "\n" + r"\end{equation}")
        elif block["type"] == "image":
            name = asset(block["path"], assets_root, output)
            caption = paragraph(block.get("caption") or block["alt"], targets)
            source_key = block.get("source_citation_key")
            if source_key and source_key not in targets["cite"]:
                raise ValueError("图片来源引用的文献不存在。")
            source = rf"\cite{{{source_key}}}" if source_key else ""
            rendered.append(r"\begin{figure}[htbp]" + "\n" + rf"\centering\includegraphics[width={block.get('width_mm', 120):g}mm]{{{name}}}" + "\n" + rf"\caption{{{caption}{source}}}" + (rf"\label{{fig:{block['id']}}}" if block.get("id") else "") + "\n" + r"\end{figure}")
        elif block["type"] == "figure_group":
            source_key = block.get("source_citation_key")
            if source_key and source_key not in targets["cite"]:
                raise ValueError("组合图来源引用的文献不存在。")
            columns = min(block.get("columns", 2), len(block["items"]))
            width = 0.96 / columns
            rows = []
            for index, item in enumerate(block["items"]):
                name = asset(item["path"], assets_root, output)
                rows.append(rf"\begin{{minipage}}[t]{{{width:.3f}\linewidth}}\centering\includegraphics[width=\linewidth,height=55mm,keepaspectratio]{{{name}}}" + (rf"\par {paragraph(item['caption'], targets)}" if item.get("caption") else "") + r"\end{minipage}")
                rows.append(r"\par " if (index + 1) % columns == 0 else r"\hfill ")
            caption = paragraph(block["caption"], targets) + (rf"\cite{{{source_key}}}" if source_key else "")
            rendered.append(r"\begin{figure}[htbp]\centering " + "\n".join(rows) + rf"\caption{{{caption}}}" + (rf"\label{{fig:{block['id']}}}" if block.get("id") else "") + r"\end{figure}")
        elif block["type"] == "data_table":
            cols = len(block["columns"])
            style = block.get("style", "three_line")
            spec = "|" + "|".join("l" for _ in range(cols)) + "|" if style == "grid" else "l" * cols
            top, mid, bottom = (r"\hline", r"\hline", r"\hline") if style == "grid" else (r"\toprule", r"\midrule", r"\bottomrule")
            header = " & ".join(paragraph(c["header"], targets) for c in block["columns"])
            rows = [" & ".join(paragraph(cell, targets) for cell in row["cells"]) + r" \\" for row in block["rows"]]
            caption = paragraph(block.get("caption") or "表格", targets)
            rendered.append("\n".join([
                rf"\begin{{longtable}}{{{spec}}}\caption{{{caption}}}\\",
                top, header + r" \\", mid, r"\endfirsthead",
                rf"\multicolumn{{{cols}}}{{c}}{{续表 \thetable}}\\",
                top, header + r" \\", mid, r"\endhead",
                bottom, r"\endfoot", bottom, r"\endlastfoot",
                *rows, r"\end{longtable}",
            ]))
        else:
            raise ValueError("论文包含尚不支持的内容块。")
    return "\n".join(rendered)


def render(data: dict, output: Path, assets_root: Path, compile_pdf: bool) -> None:
    thesis = data["thesis"]
    metadata = data["metadata"]
    keys = set(re.findall(r"@[A-Za-z]+\s*[{(]\s*([A-Za-z0-9_:.+/-]+)\s*,", thesis["referencesBibtex"]))
    targets = {"fig": set(), "eq": set(), "cite": keys}
    for chapter in thesis["chapters"]:
        for block in chapter["body"]:
            if isinstance(block, dict) and block.get("type") == "equation":
                targets["eq"].add(block["id"])
            if isinstance(block, dict) and block.get("type") in ("image", "figure_group") and block.get("id"):
                targets["fig"].add(block["id"])
    for name in ("SZTUthesis.cls", "sztuthesis_main.tex", "gbt7714.sty", "gbt7714-numerical.bst", "STXingkai.ttf", "STXinwei.ttf", "STZhongsong.ttf"):
        shutil.copyfile(ROOT / name, output / name)
    for name in ("images/school_title.pdf", "scripts/check_fonts.py", "templates/common/__init__.py", "templates/common/python/__init__.py", "templates/common/python/font_files.py", "templates/common/python/typography.py", "templates/common/typography/font-policy-2026.json"):
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    (output / "content").mkdir(exist_ok=True)
    submitted = date.fromisoformat(thesis["submissionDate"])
    info = {"titlecn": paragraph(metadata["title"], targets), "titleen": escape(thesis["englishTitle"]), "priormajor": escape(metadata["major"]), "author": escape(metadata["student_name"]), "supervisor": escape(metadata["advisor"]), "supervisortitle": escape(metadata.get("advisor_title", "")), "department": escape(metadata["college"]), "studentid": escape(metadata["student_id"]), "clcnumber": "", "schoolcode": "14655", "udc": "", "academiccategory": ""}
    (output / "content/info.tex").write_text("\n".join(rf"\{name}{{{value}}}" for name, value in info.items()) + rf"\thesisdate{{year={submitted.year},month={submitted.month},day={submitted.day}}}" + "\n\\newif\\ifblindreview\n\\blindreviewfalse\n", encoding="utf-8")
    abstracts = (("abstractcn", "keywordscn", "categorycn", "摘要", "keywordsCn", "abstractCn"), ("abstracten", "keywordsen", "categoryen", "Abstract", "keywordsEn", "abstractEn"))
    for env, keyword_macro, category_macro, heading, keyword_key, body_key in abstracts:
        value = "\\phantomsection\n" + rf"\addcontentsline{{toc}}{{section}}{{{heading}}}" + "\n" + rf"\{keyword_macro}{{{escape(thesis[keyword_key])}}}" + "\n" + rf"\{category_macro}{{}}" + "\n" + rf"\begin{{{env}}}" + "\n" + blocks(thesis[body_key], targets, assets_root, output) + "\n" + rf"\end{{{env}}}" + "\n"
        (output / f"content/{env}.tex").write_text(value, encoding="utf-8")
    body = []
    for chapter in thesis["chapters"]:
        command = {1: "section", 2: "subsection", 3: "subsubsection"}[chapter["level"]]
        body.append(rf"\{command}{{{escape(chapter['title'])}}}")
        body.append(blocks(chapter["body"], targets, assets_root, output))
    (output / "content/content.tex").write_text("\n\n".join(body) + "\n", encoding="utf-8")
    (output / "content/additional.tex").write_text(r"\begin{thankscontent}" + "\n" + blocks(thesis["acknowledgements"], targets, assets_root, output) + "\n" + r"\end{thankscontent}" + "\n", encoding="utf-8")
    appendix = blocks(thesis["appendix"], targets, assets_root, output)
    (output / "content/appendix_example.tex").write_text((r"\clearpage\section*{附录}\addcontentsline{toc}{section}{附录}" + "\n" + appendix) if appendix.strip() else "", encoding="utf-8")
    bibliography = thesis["referencesBibtex"]
    for token in re.findall(r"\\([A-Za-z]+|.)", bibliography):
        if token not in {"&", "%", "#", "_", "{", "}", "url", "doi", "LaTeX", "TeX", "textit", "emph", "textbf", "textendash", "textemdash", "alpha", "beta", "gamma", "delta"}:
            raise ValueError(f"文献包含不支持的 LaTeX 命令：{token}")
    (output / "thesis-references.bib").write_text(bibliography, encoding="utf-8")
    (output / "main.tex").write_text((output / "sztuthesis_main.tex").read_text(encoding="utf-8"), encoding="utf-8")
    if compile_pdf:
        subprocess.run([sys.executable, "scripts/check_fonts.py"], cwd=output, check=True)
        subprocess.run(["latexmk", "-no-shell-escape", "-interaction=nonstopmode", "-file-line-error", "-halt-on-error", "-xelatex", "main.tex"], cwd=output, check=True)
        log = (output / "main.log").read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?:Reference .* undefined|Citation .* undefined|There were undefined|Missing character:|Overfull \\hbox)", log):
            raise ValueError("最终 PDF 仍有未解析引用、缺字或越界内容。")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--assets-root", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.overwrite:
        parser.error("output directory is not empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        render(json.loads(args.data.read_text(encoding="utf-8")), args.output_dir, args.assets_root.resolve(), args.compile)
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"thesis render failed: {exc}", file=sys.stderr)
        return 2
    print(args.output_dir / ("main.pdf" if args.compile else "main.tex"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
