"""Validate and normalize the shared Word/LaTeX task-book input."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any


TEMPLATES_DIR = Path(__file__).resolve().parents[2]
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

from common.python.content import (  # noqa: E402
    ContentDataError as DataError,
    display_width,
    normalize_content_block,
    normalize_paragraph,
    prepare_figure_content,
    require_object,
    require_text,
    runs_text,
)
from common.python.typography import load_document_layout  # noqa: E402


SCHEMA_VERSION = "0.1"
LAYOUT = load_document_layout(Path(__file__).resolve().parents[1] / "spec" / "layout.json")
LIST_MAX_DEPTH = LAYOUT["paragraphs"]["list_max_depth"]
TITLE_DISPLAY_WIDTH_LIMIT = 80.0
GRADUATION_YEAR_MIN = 2000
GRADUATION_YEAR_MAX = 2100

METADATA_LIMITS = {
    "student_name": 20,
    "student_id": 30,
    "college": 50,
    "major": 50,
    "class_name": 30,
    "advisor": 30,
}

ADVISOR_TITLE_PATTERN = re.compile(
    r"(?:老师|导师|教授|副教授|讲师|研究员|副研究员|工程师|高级工程师|博士|硕士)"
    r"(?:\s*[）)])?\s*$"
)
TOPIC_NATURES = {"graduation_design", "graduation_thesis"}
SOURCE_TYPES = {"research_project", "practice_project", "self_proposed"}
PROJECT_LEVELS = {"national", "provincial_ministerial", "other"}
SELF_PROPOSED_BY = {"teacher", "student", "teacher_student_joint"}


def _require_exact_fields(
    value: dict[str, Any],
    path: str,
    *,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    missing = required - set(value)
    if missing:
        raise DataError(f"missing fields in {path}: {sorted(missing)}")
    unknown = set(value) - required - optional
    if unknown:
        raise DataError(f"unknown fields in {path}: {sorted(unknown)}")


def _require_enum(value: Any, path: str, allowed: set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise DataError(f"{path} must be one of {sorted(allowed)}")
    return value


def _normalize_blocks(
    value: Any,
    path: str,
    *,
    max_items: int,
    min_items: int = 1,
    max_length: int = 5000,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not min_items <= len(value) <= max_items:
        raise DataError(
            f"{path} must contain {min_items} to {max_items} content blocks"
        )
    return [
        normalize_content_block(
            block,
            f"{path}[{index}]",
            max_length,
            max_list_depth=LIST_MAX_DEPTH,
        )
        for index, block in enumerate(value)
    ]


def _normalize_schedule(value: Any) -> list[dict[str, Any]]:
    path = "sections.schedule"
    if not isinstance(value, list) or not 1 <= len(value) <= 60:
        raise DataError(f"{path} must contain 1 to 60 entries")
    clean: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(value):
        entry_path = f"{path}[{index}]"
        entry = require_object(raw_entry, entry_path)
        _require_exact_fields(
            entry,
            entry_path,
            required={"period", "content"},
        )
        clean.append(
            {
                "period": require_text(entry["period"], f"{entry_path}.period", 50),
                "content": normalize_paragraph(
                    entry["content"], f"{entry_path}.content", 1500
                ),
            }
        )
    return clean


def _normalize_references(value: Any) -> list[list[dict[str, Any]]]:
    path = "sections.references"
    if not isinstance(value, list) or not 1 <= len(value) <= 100:
        raise DataError(f"{path} must contain 1 to 100 entries")
    return [
        normalize_paragraph(item, f"{path}[{index}]", 1500)
        for index, item in enumerate(value)
    ]


def _normalize_topic_information(value: Any) -> dict[str, Any]:
    path = "sections.topic_information"
    topic = require_object(value, path)
    _require_exact_fields(topic, path, required={"nature", "source"})
    nature = _require_enum(topic["nature"], f"{path}.nature", TOPIC_NATURES)

    source_path = f"{path}.source"
    source = require_object(topic["source"], source_path)
    if "type" not in source:
        raise DataError(f"missing fields in {source_path}: ['type']")
    source_type = _require_enum(source["type"], f"{source_path}.type", SOURCE_TYPES)

    if source_type == "practice_project":
        _require_exact_fields(source, source_path, required={"type"})
        clean_source: dict[str, Any] = {"type": source_type}
    elif source_type == "self_proposed":
        _require_exact_fields(
            source,
            source_path,
            required={"type", "self_proposed_by"},
        )
        clean_source = {
            "type": source_type,
            "self_proposed_by": _require_enum(
                source["self_proposed_by"],
                f"{source_path}.self_proposed_by",
                SELF_PROPOSED_BY,
            ),
        }
    else:
        _require_exact_fields(
            source,
            source_path,
            required={"type", "research_project"},
        )
        project_path = f"{source_path}.research_project"
        project = require_object(source["research_project"], project_path)
        _require_exact_fields(
            project,
            project_path,
            required={"level", "project_number"},
            optional={"other_level"},
        )
        level = _require_enum(project["level"], f"{project_path}.level", PROJECT_LEVELS)
        clean_project = {
            "level": level,
            "project_number": require_text(
                project["project_number"], f"{project_path}.project_number", 50
            ),
        }
        if level == "other":
            clean_project["other_level"] = require_text(
                project.get("other_level"), f"{project_path}.other_level", 50
            )
        elif "other_level" in project:
            raise DataError(
                f"{project_path}.other_level is allowed only when level is 'other'"
            )
        clean_source = {"type": source_type, "research_project": clean_project}

    return {"nature": nature, "source": clean_source}


def validate_data(raw: Any) -> dict[str, Any]:
    """Return one deterministic normalized model for both output renderers."""

    data = require_object(raw, "root")
    _require_exact_fields(
        data,
        "root",
        required={"schema_version", "metadata", "sections"},
    )
    if data["schema_version"] != SCHEMA_VERSION:
        raise DataError(f"schema_version must be {SCHEMA_VERSION!r}")

    metadata = require_object(data["metadata"], "metadata")
    _require_exact_fields(
        metadata,
        "metadata",
        required=set(METADATA_LIMITS) | {"graduation_year", "title"},
    )
    graduation_year = metadata["graduation_year"]
    if (
        isinstance(graduation_year, bool)
        or not isinstance(graduation_year, int)
        or not GRADUATION_YEAR_MIN <= graduation_year <= GRADUATION_YEAR_MAX
    ):
        raise DataError(
            "metadata.graduation_year must be an integer from "
            f"{GRADUATION_YEAR_MIN} to {GRADUATION_YEAR_MAX}"
        )
    title = normalize_paragraph(metadata["title"], "metadata.title", 100)
    if display_width(runs_text(title)) > TITLE_DISPLAY_WIDTH_LIMIT:
        raise DataError(
            "metadata.title exceeds the official cover/table capacity "
            f"(limit {TITLE_DISPLAY_WIDTH_LIMIT:g} display units)"
        )
    clean_metadata = {
        "graduation_year": graduation_year,
        "title": title,
        **{
            key: require_text(metadata[key], f"metadata.{key}", limit)
            for key, limit in METADATA_LIMITS.items()
        },
    }
    if ADVISOR_TITLE_PATTERN.search(clean_metadata["advisor"]):
        raise DataError("metadata.advisor must contain the name only, without a title")

    sections = require_object(data["sections"], "sections")
    _require_exact_fields(
        sections,
        "sections",
        required={
            "basic_content_and_requirements",
            "schedule",
            "required_materials",
            "references",
            "topic_information",
        },
    )
    clean_sections = {
        "basic_content_and_requirements": _normalize_blocks(
            sections["basic_content_and_requirements"],
            "sections.basic_content_and_requirements",
            max_items=80,
        ),
        "schedule": _normalize_schedule(sections["schedule"]),
        "required_materials": _normalize_blocks(
            sections["required_materials"],
            "sections.required_materials",
            max_items=50,
            min_items=0,
        ),
        "references": _normalize_references(sections["references"]),
        "topic_information": _normalize_topic_information(
            sections["topic_information"]
        ),
    }
    prepare_figure_content(
        [
            clean_sections["basic_content_and_requirements"],
            clean_sections["required_materials"],
        ]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "metadata": clean_metadata,
        "sections": clean_sections,
    }
