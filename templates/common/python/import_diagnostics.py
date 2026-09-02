"""Privacy-bounded diagnostics for proposal/task-book/midterm PDF batches."""

from __future__ import annotations

import hashlib
import hmac
import logging
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

DOCUMENT_TYPES = ("proposal", "task-book", "midterm")
MANIFEST_VERSION = "1.0"


class ImportDiagnosticError(ValueError):
    """Raised when a manifest request itself is unsafe or malformed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_page_images(page: Any) -> int:
    try:
        return len(page.images)
    except Exception:  # noqa: BLE001 - malformed image objects are local evidence.
        # Image enumeration is secondary evidence. A malformed image must not turn a
        # readable text PDF into a batch-level failure.
        return 0


def inspect_pdf(path: str | Path) -> dict[str, Any]:
    """Return structural PDF evidence without retaining extracted text."""

    pdf_path = Path(path)
    evidence: dict[str, Any] = {
        "sha256": "",
        "page_count": 0,
        "text_char_count": 0,
        "page_image_count": 0,
        "parser": "pypdf",
        "evidence_status": "parse_failed",
    }
    try:
        evidence["sha256"] = _sha256_file(pdf_path)
    except OSError:
        evidence["parser"] = "filesystem"
        return evidence

    try:
        from pypdf import PdfReader

        parser_logger = logging.getLogger("pypdf")
        previous_level = parser_logger.level
        parser_logger.setLevel(logging.ERROR)
        try:
            reader = PdfReader(pdf_path, strict=False)
            if reader.is_encrypted and not reader.decrypt(""):
                evidence["evidence_status"] = "encrypted"
                return evidence

            pages = list(reader.pages)
            evidence["page_count"] = len(pages)
            text_char_count = 0
            image_count = 0
            for page in pages:
                extracted = page.extract_text() or ""
                text_char_count += sum(not char.isspace() for char in extracted)
                image_count += _count_page_images(page)
            evidence["text_char_count"] = text_char_count
            evidence["page_image_count"] = image_count
            if text_char_count:
                evidence["evidence_status"] = "text_layer"
            elif image_count:
                evidence["evidence_status"] = "scan_only"
            else:
                evidence["evidence_status"] = "no_text_evidence"
        finally:
            parser_logger.setLevel(previous_level)
    except Exception:  # noqa: BLE001 - parser failures must be isolated per file.
        # Do not serialize exception messages: parsers often include private paths.
        evidence["evidence_status"] = "parse_failed"
    return evidence


def _require_salt(salt: bytes) -> None:
    if not isinstance(salt, bytes) or len(salt) < 16:
        raise ImportDiagnosticError("manifest salt must contain at least 16 bytes")


def _anonymous_id(salt: bytes, namespace: str, value: str) -> str:
    digest = hmac.new(
        salt,
        f"{namespace}\0{value}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return digest[:24]


def _validate_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    status = evidence.get("evidence_status")
    allowed_statuses = {
        "text_layer",
        "scan_only",
        "no_text_evidence",
        "encrypted",
        "parse_failed",
    }
    if status not in allowed_statuses:
        raise ImportDiagnosticError(f"unknown PDF evidence status: {status!r}")
    sha256 = evidence.get("sha256", "")
    if sha256 and (
        not isinstance(sha256, str)
        or len(sha256) != 64
        or any(char not in "0123456789abcdef" for char in sha256.lower())
    ):
        raise ImportDiagnosticError(
            "document sha256 must be empty or 64 hex characters"
        )
    return {
        "sha256": sha256.lower(),
        "page_count": max(0, int(evidence.get("page_count", 0))),
        "text_char_count": max(0, int(evidence.get("text_char_count", 0))),
        "page_image_count": max(0, int(evidence.get("page_image_count", 0))),
        "parser": str(evidence.get("parser", "unknown")),
        "evidence_status": status,
    }


def build_process_document_manifest(
    records: Iterable[Mapping[str, Any]],
    *,
    salt: bytes,
    inspector: Callable[[str | Path], Mapping[str, Any]] = inspect_pdf,
) -> dict[str, Any]:
    """Return a deterministic manifest without retaining source identifiers."""

    _require_salt(salt)
    prepared: list[dict[str, Any]] = []
    for position, record in enumerate(records):
        source_key = record.get("source_key")
        document_type = record.get("document_type")
        path = record.get("path")
        if not isinstance(source_key, str) or not source_key.strip():
            raise ImportDiagnosticError(
                f"record {position} requires a non-empty source_key"
            )
        if not isinstance(document_type, str) or not document_type.strip():
            raise ImportDiagnosticError(
                f"record {position} requires a non-empty document_type"
            )
        if not isinstance(path, (str, Path)):
            raise ImportDiagnosticError(f"record {position} requires a path")
        normalized_path = str(Path(path).expanduser().resolve(strict=False))
        evidence = _validate_evidence(inspector(path))
        prepared.append(
            {
                "source_key": source_key,
                "document_type": document_type,
                "private_path": normalized_path,
                "evidence": evidence,
            }
        )

    prepared.sort(
        key=lambda item: (
            item["source_key"],
            item["document_type"],
            item["private_path"],
        )
    )
    source_keys = sorted(
        {
            item["source_key"]
            for item in prepared
            if item["document_type"] in DOCUMENT_TYPES
        }
    )
    bundle_ids = {
        key: _anonymous_id(salt, "bundle", key)
        for key in source_keys
    }

    documents: list[dict[str, Any]] = []
    internal_documents: list[dict[str, Any]] = []
    for position, item in enumerate(prepared):
        private_identity = (
            f"{item['source_key']}\0{item['document_type']}\0"
            f"{item['private_path']}\0{position}"
        )
        document_id = _anonymous_id(salt, "document", private_identity)
        safe_document_type = (
            item["document_type"]
            if item["document_type"] in DOCUMENT_TYPES
            else "unsupported"
        )
        output = {
            "document_id": document_id,
            "bundle_id": bundle_ids.get(item["source_key"]),
            "document_type": safe_document_type,
            **item["evidence"],
        }
        documents.append(output)
        internal_documents.append({**item, **output})

    issues: list[dict[str, Any]] = []
    supported_by_bundle: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for item in internal_documents:
        document_type = item["document_type"]
        if document_type not in DOCUMENT_TYPES:
            issues.append(
                {
                    "code": "UNSUPPORTED_DOCUMENT_TYPE",
                    "document_id": item["document_id"],
                    "supplied_type_id": _anonymous_id(
                        salt, "unsupported-document-type", document_type
                    ),
                }
            )
            continue
        supported_by_bundle[item["bundle_id"]][document_type].append(item)

        status_code = {
            "scan_only": "OCR_REQUIRED",
            "no_text_evidence": "MANUAL_REVIEW_REQUIRED",
            "encrypted": "PASSWORD_REQUIRED",
            "parse_failed": "PDF_PARSE_FAILED",
        }.get(item["evidence_status"])
        if status_code:
            issues.append(
                {
                    "code": status_code,
                    "bundle_id": item["bundle_id"],
                    "document_id": item["document_id"],
                    "document_type": document_type,
                }
            )

    bundles: list[dict[str, Any]] = []
    for bundle_id in sorted(supported_by_bundle):
        by_type = supported_by_bundle[bundle_id]
        missing = [name for name in DOCUMENT_TYPES if not by_type.get(name)]
        collisions = [name for name in DOCUMENT_TYPES if len(by_type.get(name, [])) > 1]
        for document_type in missing:
            issues.append(
                {
                    "code": "MISSING_DOCUMENT",
                    "bundle_id": bundle_id,
                    "document_type": document_type,
                }
            )
        for document_type in collisions:
            issues.append(
                {
                    "code": "SAME_TYPE_COLLISION",
                    "bundle_id": bundle_id,
                    "document_type": document_type,
                    "document_ids": sorted(
                        item["document_id"] for item in by_type[document_type]
                    ),
                }
            )
        bundles.append(
            {
                "bundle_id": bundle_id,
                "document_counts": {
                    name: len(by_type.get(name, [])) for name in DOCUMENT_TYPES
                },
                "complete": not missing and not collisions,
            }
        )

    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in internal_documents:
        if item["document_type"] in DOCUMENT_TYPES and item["sha256"]:
            by_hash[item["sha256"]].append(item)
    for sha256, items in sorted(by_hash.items()):
        if len({item["document_type"] for item in items}) > 1:
            issues.append(
                {
                    "code": "CROSS_TYPE_BYTE_DUPLICATE",
                    "sha256": sha256,
                    "document_ids": sorted(item["document_id"] for item in items),
                    "document_types": sorted(
                        {item["document_type"] for item in items}
                    ),
                }
            )

    issues.sort(
        key=lambda issue: (
            issue["code"],
            str(issue.get("bundle_id", "")),
            str(issue.get("document_type", "")),
            str(issue.get("document_id", "")),
        )
    )
    status_counts: dict[str, int] = defaultdict(int)
    for document in documents:
        status_counts[document["evidence_status"]] += 1
    return {
        "manifest_version": MANIFEST_VERSION,
        "expected_document_types": list(DOCUMENT_TYPES),
        "summary": {
            "bundle_count": len(bundles),
            "document_count": len(documents),
            "complete_bundle_count": sum(bundle["complete"] for bundle in bundles),
            "issue_count": len(issues),
            "evidence_status_counts": dict(sorted(status_counts.items())),
        },
        "bundles": bundles,
        "documents": documents,
        "issues": issues,
    }
