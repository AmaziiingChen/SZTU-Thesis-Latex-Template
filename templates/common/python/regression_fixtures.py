"""Deterministic anonymous load expansion used only by template regressions."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class RegressionFixtureError(ValueError):
    """Raised when a page-range stress recipe cannot produce valid input."""


def load_page_range_recipes(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0" or not isinstance(
        payload.get("cases"), dict
    ):
        raise RegressionFixtureError("invalid page-range stress recipe")
    return payload["cases"]


def _paragraph_candidates(items: list[Any], section_name: str) -> list[Any]:
    candidates = [
        item
        for item in items
        if isinstance(item, str)
        or (
            isinstance(item, Mapping)
            and item.get("type") == "paragraph"
            and isinstance(item.get("runs"), list)
            and item["runs"]
        )
    ]
    if not candidates:
        raise RegressionFixtureError(
            f"section {section_name!r} has no repeatable paragraph"
        )
    return candidates


def _numbered_copy(item: Any, ordinal: int, text_multiplier: int) -> Any:
    prefix = f"第{ordinal:03d}组匿名分页压力内容。"
    copied = copy.deepcopy(item)
    if isinstance(copied, str):
        return prefix + "".join(copied for _ in range(text_multiplier))
    original_runs = copy.deepcopy(copied["runs"])
    copied["runs"] = [
        copy.deepcopy(run)
        for _ in range(text_multiplier)
        for run in original_runs
    ]
    first_run = copied["runs"][0]
    if not isinstance(first_run, dict) or not isinstance(first_run.get("text"), str):
        raise RegressionFixtureError("repeatable paragraph requires a leading text run")
    first_run["text"] = prefix + first_run["text"]
    return copied


def materialize_page_range_fixture(
    base_fixture: str | Path,
    recipe: Mapping[str, Any],
    output_path: str | Path,
) -> Path:
    """Expand anonymous content to recipe targets and write a normal schema input."""

    base_path = Path(base_fixture)
    data = json.loads(base_path.read_text(encoding="utf-8"))
    sections = data.get("sections")
    if not isinstance(sections, dict):
        raise RegressionFixtureError("base fixture requires a sections object")

    targets = recipe.get("section_targets", {})
    if not isinstance(targets, Mapping):
        raise RegressionFixtureError("section_targets must be an object")
    text_multiplier = int(recipe.get("copy_text_multiplier", 1))
    if not 1 <= text_multiplier <= 4:
        raise RegressionFixtureError("copy_text_multiplier must be between 1 and 4")
    for section_name, raw_target in targets.items():
        target = int(raw_target)
        items = sections.get(section_name)
        if not isinstance(items, list) or not items:
            raise RegressionFixtureError(
                f"base fixture section {section_name!r} must be a non-empty array"
            )
        if target < len(items):
            raise RegressionFixtureError(
                f"target for {section_name!r} cannot remove base content"
            )
        candidates = _paragraph_candidates(items, section_name)
        ordinal = 1
        while len(items) < target:
            items.append(
                _numbered_copy(
                    candidates[(ordinal - 1) % len(candidates)],
                    ordinal,
                    text_multiplier,
                )
            )
            ordinal += 1

    if "reference_target" in recipe:
        target = int(recipe["reference_target"])
        references = sections.get("references")
        if not isinstance(references, list):
            raise RegressionFixtureError("reference_target requires a references array")
        if target < len(references):
            raise RegressionFixtureError(
                "reference_target cannot remove base references"
            )
        while len(references) < target:
            number = len(references) + 1
            references.append(
                f"[{number}] 匿名测试作者. 第{number:03d}组过程文档分页、连续边框与"
                "固定签署空间回归研究[J]. 虚构文档工程学报, 2026, 1(1): 1-12."
            )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output
