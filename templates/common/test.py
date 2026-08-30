#!/usr/bin/env python3
"""Regression checks for the reusable process-document template primitives."""

from __future__ import annotations

import json
import sys
from pathlib import Path

COMMON_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = COMMON_DIR.parent
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

from common.python.content import (  # noqa: E402
    ContentDataError,
    normalize_paragraph,
    split_numbered_subitems,
)
from common.python.typography import (  # noqa: E402
    load_document_layout,
    load_font_policy,
)


def main() -> int:
    policy = load_font_policy()
    assert policy["fallback_allowed"] is False
    assert policy["roles"]["cjk_body"]["word_family"] == "宋体"
    assert policy["roles"]["cjk_label"]["word_family"] == "黑体"

    sizes = json.loads(
        (COMMON_DIR / "typography" / "chinese-sizes.json").read_text(
            encoding="utf-8"
        )
    )["sizes"]
    assert sizes["小二"] == {"pt": 18.0, "latex_zihao": "-2"}
    assert sizes["小四"] == {"pt": 12.0, "latex_zihao": "-4"}
    assert sizes["五号"] == {"pt": 10.5, "latex_zihao": "5"}

    proposal_layout = load_document_layout(
        TEMPLATES_DIR / "proposal" / "spec" / "layout.json"
    )
    assert proposal_layout["typography"]["title"]["size_pt"] == 18.0
    assert proposal_layout["typography"]["title"]["cjk_word_family"] == "黑体"
    assert proposal_layout["typography"]["body"]["size_pt"] == 10.5
    assert proposal_layout["typography"]["body"]["cjk_word_family"] == "宋体"

    rich = normalize_paragraph(
        {
            "type": "paragraph",
            "runs": [
                {"text": "H"},
                {"text": "2", "script": "sub"},
                {"text": "O"},
                {"text": "[1]", "script": "super", "bold": True},
            ],
        },
        "fixture.rich",
        100,
    )
    assert rich[1]["script"] == "sub"
    assert rich[3]["script"] == "super" and rich[3]["bold"] is True
    assert all(isinstance(run["italic"], bool) for run in rich)

    try:
        normalize_paragraph(
            {"runs": [{"text": "x", "script": "raised"}]},
            "fixture.invalid",
            100,
        )
    except ContentDataError:
        pass
    else:
        raise AssertionError("an unknown script value must be rejected")

    legacy = normalize_paragraph(
        {
            "runs": [
                {"text": "对比分析法。"},
                {"text": "（1）传统机器学习；（2）经典 CNN；"},
                {"text": "（3）高光谱模型", "italic": True},
                {"text": "\n通过统一数据完成比较。"},
            ]
        },
        "fixture.legacy_list",
        200,
    )
    split = split_numbered_subitems(legacy)
    assert split is not None
    lead, subitems, continuations = split
    assert "".join(run["text"] for run in lead) == "对比分析法。"
    assert [marker for marker, _ in subitems] == ["（1）", "（2）", "（3）"]
    assert subitems[-1][1][-1]["italic"] is True
    assert "".join(run["text"] for run in continuations[0]).startswith(
        "通过统一数据"
    )

    schema_path = COMMON_DIR / "schema" / "content-block.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert {"run", "richParagraph", "orderedList", "contentBlock"} <= set(
        schema["$defs"]
    )

    proposal_schema = json.loads(
        (TEMPLATES_DIR / "proposal" / "schema" / "proposal.schema.json").read_text(
            encoding="utf-8"
        )
    )
    paragraph_ref = proposal_schema["$defs"]["paragraph"]["$ref"]
    rich_ref = proposal_schema["$defs"]["richParagraph"]["$ref"]
    for reference in (paragraph_ref, rich_ref):
        relative_path = reference.split("#", 1)[0]
        assert (
            TEMPLATES_DIR / "proposal" / "schema" / relative_path
        ).resolve().is_file()

    print("common template regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
