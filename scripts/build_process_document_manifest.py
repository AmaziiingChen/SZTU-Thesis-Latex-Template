#!/usr/bin/env python3
"""Build an anonymous local diagnostic manifest for process-document PDFs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "templates"
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

from common.python.import_diagnostics import (  # noqa: E402
    ImportDiagnosticError,
    build_process_document_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect proposal/task-book/midterm PDFs and write a path-free, "
            "identifier-free manifest."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Private JSON with a documents array of source_key/document_type/path.",
    )
    parser.add_argument(
        "--salt-file",
        type=Path,
        required=True,
        help="Private file containing at least 16 bytes; never copied to output.",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        documents = payload["documents"]
        if not isinstance(documents, list):
            raise ImportDiagnosticError("input documents must be an array")
        salt = args.salt_file.read_bytes().strip()
        manifest = build_process_document_manifest(documents, salt=salt)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, KeyError, json.JSONDecodeError, ImportDiagnosticError) as exc:
        print(f"manifest generation failed: {exc}", file=sys.stderr)
        return 2
    print(
        f"wrote {manifest['summary']['document_count']} document diagnostics "
        f"with {manifest['summary']['issue_count']} issue(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
