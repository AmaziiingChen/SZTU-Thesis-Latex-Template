#!/usr/bin/env python3
"""Create copy-ready Markdown from MinerU results without Markdown tables.

Results remain in output/mineru/private and are intentionally excluded from Git.
The script only transforms locally downloaded MinerU output; it never calls a
remote service and never moves or changes the source documents.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = ROOT / "output/mineru/private"
TABLE_DIVIDER = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
IMAGE_LINE = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$")


def table_to_lines(block: list[str]) -> list[str]:
    rows = []
    for line in block:
        if TABLE_DIVIDER.match(line):
            continue
        values = [part.strip() for part in line.strip().strip("|").split("|")]
        if any(values):
            rows.append(values)
    if not rows:
        return []
    if len(rows[0]) == 2:
        return [f"**{row[0]}**：{row[1]}" if len(row) > 1 else row[0] for row in rows]
    header, *body = rows
    return [
        "- " + "；".join(f"{key}：{value}" for key, value in zip(header, row) if value)
        for row in body
    ]


def normalize_markdown(source: str) -> str:
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output: list[str] = []
    table: list[str] = []
    image_omitted = False

    def flush_table() -> None:
        nonlocal table
        if table:
            output.extend(table_to_lines(table))
            table = []

    for raw in lines:
        line = raw.rstrip()
        if line.lstrip().startswith("|"):
            table.append(line)
            continue
        flush_table()
        if IMAGE_LINE.match(line):
            image_omitted = True
            continue
        output.append(line)
    flush_table()

    text = "\n".join(output)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if image_omitted:
        text += "\n\n> 图片已从可复制文本中省略；原始 MinerU 结果目录保留对应图片。"
    return text + "\n"


def main() -> int:
    manifest_path = RESULT_ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, str]]] = {}
    generated = 0
    for record in manifest["files"]:
        if record.get("state") != "done" or not record.get("result_dir"):
            continue
        result_dir = Path(record["result_dir"])
        source = result_dir / "full.md"
        if not source.exists():
            continue
        target = result_dir / "copy-ready.md"
        target.write_text(normalize_markdown(source.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
        grouped.setdefault(record["document_type"], []).append(
            {"source": record["source"], "copy_ready": str(target.relative_to(RESULT_ROOT))}
        )
        generated += 1

    index = ["# MinerU 可复制 Markdown 索引", "", "本目录为本地私有 OCR 结果；每一份 `copy-ready.md` 均不含 Markdown 表格语法。"]
    for document_type in sorted(grouped):
        index.extend(["", f"## {document_type}", ""])
        for item in sorted(grouped[document_type], key=lambda value: value["source"]):
            index.append(f"- `{item['source']}` → `{item['copy_ready']}`")
    (RESULT_ROOT / "COPY_READY_INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(json.dumps({"generated": generated, "index": "COPY_READY_INDEX.md"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
