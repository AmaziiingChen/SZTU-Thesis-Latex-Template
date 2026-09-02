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
    normalize_content_block,
    normalize_paragraph,
    split_numbered_subitems,
)
from common.python.font_files import cjk_emphasis_options  # noqa: E402
from common.python.outline_numbering import (  # noqa: E402
    chinese_number,
    number_outline_levels,
    style_max_depth,
)
from common.python.process_form import (  # noqa: E402
    LATEX_SUPPORT_NAME,
    load_process_document_layout,
    process_form_latex_tokens,
)
from common.python.typography import (  # noqa: E402
    load_font_policy,
)


def main() -> int:
    policy = load_font_policy()
    assert policy["fallback_allowed"] is False
    assert policy["roles"]["cjk_body"]["word_family"] == "宋体"
    assert policy["roles"]["cjk_label"]["word_family"] == "黑体"
    emphasis_options = cjk_emphasis_options("/fonts/")
    assert emphasis_options == (
        "Path={/fonts/},AutoFakeBold=3,AutoFakeSlant=0.2"
    )
    assert [chinese_number(value) for value in (1, 10, 11, 20, 101)] == [
        "一",
        "十",
        "十一",
        "二十",
        "一百零一",
    ]
    hierarchy = [1, 2, 3, 4, 1, 2]
    assert number_outline_levels(hierarchy, "chinese_hierarchy") == [
        "一、",
        "（一）",
        "1.",
        "(1)",
        "二、",
        "（一）",
    ]
    assert number_outline_levels([1, 2, 3, 4, 5], "chapter_hierarchy") == [
        "第一章",
        "一、",
        "（一）",
        "1.",
        "(1)",
    ]
    assert number_outline_levels(
        [1, 2, 3, 4, 5, 6], "chapter_section_hierarchy"
    ) == ["第一章", "第一节", "一、", "（一）", "1.", "(1)"]
    assert number_outline_levels(
        [1, 2, 3, 4, 5, 6], "part_chapter_section_hierarchy"
    ) == ["第一篇", "第一章", "第一节", "一、", "（一）", "1."]
    assert number_outline_levels([1, 2, 3, 2, 3], "decimal_hierarchy") == [
        "1.",
        "1.1",
        "1.1.1",
        "1.2",
        "1.2.1",
    ]
    assert style_max_depth("chinese_hierarchy") == 4
    assert style_max_depth("chapter_section_hierarchy") == 6

    sizes = json.loads(
        (COMMON_DIR / "typography" / "chinese-sizes.json").read_text(
            encoding="utf-8"
        )
    )["sizes"]
    assert sizes["小二"] == {"pt": 18.0, "latex_zihao": "-2"}
    assert sizes["小四"] == {"pt": 12.0, "latex_zihao": "-4"}
    assert sizes["五号"] == {"pt": 10.5, "latex_zihao": "5"}

    proposal_layout = load_process_document_layout(
        TEMPLATES_DIR / "proposal" / "spec" / "layout.json"
    )
    assert proposal_layout["typography"]["title"]["size_pt"] == 18.0
    assert proposal_layout["typography"]["title"]["cjk_word_family"] == "黑体"
    assert proposal_layout["typography"]["body"]["size_pt"] == 10.5
    assert proposal_layout["typography"]["body"]["cjk_word_family"] == "宋体"
    layouts = {
        name: load_process_document_layout(
            TEMPLATES_DIR / name / "spec" / "layout.json"
        )
        for name in ("proposal", "task-book", "midterm")
    }
    for layout in layouts.values():
        tokens = "\n".join(process_form_latex_tokens(layout))
        assert r"\newcommand{\SZTUFormRuleWidth}" in tokens
        assert r"\newcommand{\SZTUFlowVerticalPadding}" in tokens
        assert r"\newcommand{\SZTUSectionTitleContentGap}" in tokens
    latex_support = (COMMON_DIR / "latex" / LATEX_SUPPORT_NAME).read_text(
        encoding="utf-8"
    )
    assert "sztuformflow/.style" in latex_support
    assert r"\newcommand{\SZTUFormTightJoin}" in latex_support

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

    pasted_fixture = json.loads(
        (COMMON_DIR / "fixtures" / "pasted-scientific-text.json").read_text(
            encoding="utf-8"
        )
    )
    pasted_scientific_text = normalize_paragraph(
        pasted_fixture["source"],
        "fixture.pasted_scientific_text",
        100,
    )
    assert pasted_scientific_text == [
        {"text": "g-C", "script": "normal", "italic": False, "bold": False},
        {"text": "3", "script": "sub", "italic": False, "bold": False},
        {"text": "N", "script": "normal", "italic": False, "bold": False},
        {"text": "4", "script": "sub", "italic": False, "bold": False},
        {"text": " / CO", "script": "normal", "italic": False, "bold": False},
        {"text": "2", "script": "sub", "italic": False, "bold": False},
        {"text": " / R", "script": "normal", "italic": False, "bold": False},
        {"text": "2", "script": "super", "italic": False, "bold": False},
        {"text": " / 10", "script": "normal", "italic": False, "bold": False},
        {"text": "−3", "script": "super", "italic": False, "bold": False},
        {"text": " mol·L", "script": "normal", "italic": False, "bold": False},
        {"text": "−1", "script": "super", "italic": False, "bold": False},
        {"text": " / 550 °C", "script": "normal", "italic": False, "bold": False},
    ]

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

    nested = normalize_content_block(
        {
            "type": "unordered_list",
            "items": [
                {
                    "content": "一级",
                    "children": {
                        "type": "ordered_list",
                        "items": [
                            {
                                "marker": "（1）",
                                "content": {"runs": [{"text": "二级", "bold": True}]},
                                "children": {
                                    "type": "unordered_list",
                                    "items": [
                                        {
                                            "content": "三级",
                                            "children": {
                                                "type": "ordered_list",
                                                "items": [{"content": "四级"}],
                                            },
                                        }
                                    ],
                                },
                            }
                        ],
                    },
                }
            ],
        },
        "fixture.nested",
        100,
    )
    assert nested["type"] == "unordered_list"
    level_two = nested["items"][0]["children"]
    assert level_two["type"] == "ordered_list"
    assert level_two["items"][0]["marker"] == "（1）"
    assert level_two["items"][0]["runs"][0]["bold"] is True
    level_four = level_two["items"][0]["children"]["items"][0]["children"]
    assert level_four["items"][0]["children"] is None

    data_table = normalize_content_block(
        {
            "type": "data_table",
            "columns": [
                {"header": "指标", "width_weight": 2, "alignment": "left"},
                {"header": "结果", "alignment": "center"},
            ],
            "rows": [
                {"cells": ["准确率", {"runs": [{"text": "98.6", "bold": True}, {"text": "%"}]}]},
                {"cells": ["误差", "0.12"]},
            ],
            "caption": "匿名实验结果",
        },
        "fixture.data_table",
        200,
    )
    assert data_table["type"] == "data_table"
    assert [column["width_weight"] for column in data_table["columns"]] == [2.0, 1.0]
    assert data_table["rows"][0][1][0]["bold"] is True
    assert data_table["caption_runs"][0]["text"] == "匿名实验结果"

    figure_group = normalize_content_block(
        {
            "type": "figure_group",
            "id": "fig-group001",
            "chapter": 2,
            "items": [
                {"path": "a.png", "alt": "方法一结果", "caption": "方法一"},
                {"path": "b.png", "alt": "方法二结果", "caption": "方法二"},
            ],
            "caption": "两种方法结果对比",
        },
        "fixture.figure_group",
        200,
    )
    assert figure_group["type"] == "figure_group"
    assert [item["subfigure_label"] for item in figure_group["items"]] == ["（a）", "（b）"]
    assert figure_group["caption_runs"][0]["text"] == "两种方法结果对比"

    equation = normalize_content_block(
        {
            "type": "equation",
            "expression": {
                "type": "row",
                "items": [
                    {"type": "text", "value": "η="},
                    {
                        "type": "fraction",
                        "numerator": {
                            "type": "subscript",
                            "base": {"type": "text", "value": "C"},
                            "sub": {"type": "text", "value": "out"},
                        },
                        "denominator": {
                            "type": "subscript",
                            "base": {"type": "text", "value": "C"},
                            "sub": {"type": "text", "value": "in"},
                        },
                    },
                    {
                        "type": "square_root",
                        "body": {
                            "type": "superscript",
                            "base": {"type": "text", "value": "x"},
                            "super": {"type": "text", "value": "2"},
                        },
                    },
                ],
            },
            "alt": "效率等于浓度比值与平方根项之和",
        },
        "fixture.equation",
        200,
    )
    assert equation["type"] == "equation"
    assert equation["expression"]["items"][1]["type"] == "fraction"
    assert equation["expression"]["items"][2]["body"]["type"] == "superscript"

    try:
        normalize_content_block(
            {
                "type": "equation",
                "expression": {"type": "text", "value": r"\\input{private}"},
                "alt": "非法公式",
            },
            "fixture.unsafe_equation",
            200,
        )
    except ContentDataError as exc:
        assert "unsupported math characters" in str(exc)
    else:
        raise AssertionError("raw TeX commands must be rejected")

    legacy_ordered = normalize_content_block(
        {"type": "ordered_list", "items": [{"content": "旧列表"}]},
        "fixture.legacy_ordered",
        100,
    )
    assert legacy_ordered["type"] == "ordered_list"
    assert legacy_ordered["items"][0]["children"] is None

    too_deep = {"type": "ordered_list", "items": [{"content": "第五级"}]}
    for level in range(4, 0, -1):
        too_deep = {
            "type": "unordered_list" if level % 2 else "ordered_list",
            "items": [{"content": f"第{level}级", "children": too_deep}],
        }
    try:
        normalize_content_block(too_deep, "fixture.too_deep", 100)
    except ContentDataError as exc:
        assert "maximum list depth of 4" in str(exc)
    else:
        raise AssertionError("a fifth nested list level must be rejected")

    try:
        normalize_content_block(
            {
                "type": "unordered_list",
                "items": [{"marker": "-", "content": "非法标记"}],
            },
            "fixture.unordered_marker",
            100,
        )
    except ContentDataError:
        pass
    else:
        raise AssertionError("unordered lists must reject explicit markers")

    schema_path = COMMON_DIR / "schema" / "content-block.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert {
        "run",
        "richParagraph",
        "orderedList",
        "unorderedList",
        "listLevel4",
        "textContentBlock",
        "contentBlock",
        "mathExpression",
        "equation",
    } <= set(schema["$defs"])
    assert "children" not in schema["$defs"]["listLevel4"]["properties"]["items"]["items"]["properties"]

    proposal_schema = json.loads(
        (TEMPLATES_DIR / "proposal" / "schema" / "proposal.schema.json").read_text(
            encoding="utf-8"
        )
    )
    paragraph_ref = proposal_schema["$defs"]["paragraph"]["$ref"]
    rich_ref = proposal_schema["$defs"]["richParagraph"]["$ref"]
    text_content_ref = proposal_schema["$defs"]["textContentBlock"]["$ref"]
    for reference in (paragraph_ref, rich_ref, text_content_ref):
        relative_path = reference.split("#", 1)[0]
        assert (
            TEMPLATES_DIR / "proposal" / "schema" / relative_path
        ).resolve().is_file()

    print("common template regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
