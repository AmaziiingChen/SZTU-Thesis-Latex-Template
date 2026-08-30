"""Load shared font policy and resolve document-specific typography tokens."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


COMMON_DIR = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def load_font_policy() -> dict[str, Any]:
    policy = _load_json(COMMON_DIR / "typography" / "font-policy-2026.json")
    if policy.get("fallback_allowed") is not False:
        raise ValueError("official font policy must forbid fallback")
    return policy


def load_document_layout(path: Path) -> dict[str, Any]:
    layout = copy.deepcopy(_load_json(path))
    sizes = _load_json(COMMON_DIR / "typography" / "chinese-sizes.json")["sizes"]
    policy = load_font_policy()
    required_font_files: set[str] = set()
    for name, style in layout.get("typography", {}).items():
        size_name = style.get("size")
        cjk_role = style.get("cjk_font_role")
        latin_role = style.get("latin_font_role", "latin")
        if size_name not in sizes:
            raise ValueError(f"unknown Chinese size for typography.{name}: {size_name}")
        if cjk_role not in policy["roles"] or latin_role not in policy["roles"]:
            raise ValueError(f"unknown font role for typography.{name}")
        style["size_pt"] = float(sizes[size_name]["pt"])
        style["latex_zihao"] = str(sizes[size_name]["latex_zihao"])
        style["cjk_word_family"] = policy["roles"][cjk_role]["word_family"]
        style["cjk_latex_family"] = policy["roles"][cjk_role]["latex_family"]
        style["latin_word_family"] = policy["roles"][latin_role]["word_family"]
        style["latin_latex_family"] = policy["roles"][latin_role]["latex_family"]
        required_font_files.update(policy["roles"][cjk_role]["font_file_keys"])
        required_font_files.update(policy["roles"][latin_role]["font_file_keys"])
    layout["required_font_files"] = sorted(required_font_files)
    return layout
