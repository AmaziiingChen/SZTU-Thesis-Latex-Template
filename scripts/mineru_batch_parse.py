#!/usr/bin/env python3
"""Submit private process-document PDFs to MinerU and collect Markdown/JSON.

The API token is read only from MINERU_API_TOKEN.  This script never writes it
to the manifest or to console output.  It deliberately gives MinerU anonymous
remote names and data IDs, while the local private manifest keeps the mapping
needed to restore each result to its source document.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests


API_ROOT = "https://mineru.net/api/v4"
DEFAULT_ROOTS = {
    "midterm": "references/private/midterm",
    "proposal": "references/private/proposals",
    "task-book": "references/private/task-books",
}
SUPPORTED_SUFFIXES = {".pdf", ".doc", ".docx"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def discover_files(repo_root: Path, roots: dict[str, str], output_dir: Path) -> list[dict[str, Any]]:
    output_root = output_dir.resolve()
    records: list[dict[str, Any]] = []
    for document_type, configured_root in roots.items():
        root = (repo_root / configured_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"source directory does not exist: {root}")
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            resolved = path.resolve()
            if output_root in resolved.parents:
                continue
            digest = sha256_file(resolved)
            suffix = resolved.suffix.lower()
            identifier = f"{document_type}-{digest[:24]}"
            records.append(
                {
                    "data_id": identifier,
                    "document_type": document_type,
                    "source": str(resolved.relative_to(repo_root)),
                    "sha256": digest,
                    "bytes": resolved.stat().st_size,
                    "remote_name": f"{document_type}-{digest[:24]}{suffix}",
                    "selected": False,
                    "state": "new",
                    "updated_at": utc_now(),
                }
            )
    return records


def select_records(manifest: dict[str, Any], per_document_type: int) -> None:
    """Keep a deterministic, extendable sample selection in the private manifest."""
    for document_type in DEFAULT_ROOTS:
        records = sorted(
            (record for record in manifest["files"] if record["document_type"] == document_type),
            key=lambda record: record["source"],
        )
        for index, record in enumerate(records):
            if index < per_document_type:
                record["selected"] = True


def authorization_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def request_with_retry(call: Any, *, attempts: int = 4, **kwargs: Any) -> requests.Response:
    """Retry transient TLS/network and server failures without logging secrets."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = call(**kwargs)
            if response.status_code < 500:
                return response
            last_error = RuntimeError(f"remote service returned HTTP {response.status_code}")
        except requests.RequestException as error:
            last_error = error
        if attempt < attempts:
            time.sleep(2 ** (attempt - 1))
    assert last_error is not None
    raise RuntimeError(f"network request failed after {attempts} attempts: {last_error}")


def request_upload_urls(token: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    files = [
        {
            "name": record["remote_name"],
            "data_id": record["data_id"],
            "is_ocr": True,
        }
        for record in records
    ]
    response = request_with_retry(
        requests.post,
        url=f"{API_ROOT}/file-urls/batch",
        headers=authorization_headers(token),
        json={
            "files": files,
            "model_version": "vlm",
            "language": "ch",
            "enable_formula": True,
            "enable_table": True,
        },
        timeout=60,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("code") != 0:
        raise RuntimeError(f"MinerU upload URL request failed: {result.get('code')} {result.get('msg')}")
    return result["data"]


def upload_file(upload_url: str, path: Path) -> None:
    def send() -> requests.Response:
        with path.open("rb") as source:
            return requests.put(upload_url, data=source, timeout=(30, 1800))

    response = request_with_retry(send)
    if response.status_code not in {200, 201, 204}:
        raise RuntimeError(f"upload returned HTTP {response.status_code}")


def submit_pending(
    repo_root: Path,
    manifest: dict[str, Any],
    token: str,
    batch_size: int,
    max_batches: int | None,
    manifest_path: Path,
) -> int:
    pending = [record for record in manifest["files"] if record.get("selected") and record["state"] == "new"]
    if max_batches is not None:
        pending = pending[: batch_size * max_batches]
    submitted = 0
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        upload_data = request_upload_urls(token, batch)
        urls = upload_data.get("file_urls", [])
        if len(urls) != len(batch):
            raise RuntimeError("MinerU returned a different number of upload URLs")
        batch_id = upload_data["batch_id"]
        for record, upload_url in zip(batch, urls, strict=True):
            record["state"] = "uploading"
            record["batch_id"] = batch_id
            record["updated_at"] = utc_now()
            save_json(manifest_path, manifest)
            try:
                upload_file(upload_url, repo_root / record["source"])
            except Exception as error:  # Preserve the failed item for an explicit retry.
                record["state"] = "upload_failed"
                record["error"] = str(error)
                record["updated_at"] = utc_now()
                save_json(manifest_path, manifest)
                continue
            record["state"] = "uploaded"
            record.pop("error", None)
            record["updated_at"] = utc_now()
            save_json(manifest_path, manifest)
        submitted += 1
        print(f"submitted batch {submitted}: {len(batch)} files")
    return submitted


def download_zip(url: str, destination: Path) -> None:
    response = request_with_retry(requests.get, url=url, stream=True, timeout=(30, 1800))
    response.raise_for_status()
    with destination.open("wb") as target:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                target.write(chunk)


def collect_results(
    manifest: dict[str, Any], token: str, output_dir: Path, manifest_path: Path
) -> tuple[int, int]:
    records_by_batch: dict[str, list[dict[str, Any]]] = {}
    for record in manifest["files"]:
        if record.get("batch_id") and record["state"] in {"uploaded", "running", "pending", "waiting-file"}:
            records_by_batch.setdefault(record["batch_id"], []).append(record)
    completed = failed = 0
    for batch_id, batch_records in records_by_batch.items():
        response = request_with_retry(
            requests.get,
            url=f"{API_ROOT}/extract-results/batch/{batch_id}",
            headers=authorization_headers(token),
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        if result.get("code") != 0:
            raise RuntimeError(f"MinerU result query failed: {result.get('code')} {result.get('msg')}")
        by_identifier = {record["data_id"]: record for record in batch_records}
        for item in result["data"].get("extract_result", []):
            record = by_identifier.get(item.get("data_id"))
            if record is None:
                continue
            state = item.get("state", "pending")
            record["state"] = state
            record["updated_at"] = utc_now()
            if state == "failed":
                record["error"] = item.get("err_msg", "MinerU parsing failed")
                failed += 1
                continue
            if state != "done":
                continue
            target_dir = output_dir / record["document_type"] / record["data_id"]
            target_dir.mkdir(parents=True, exist_ok=True)
            zip_path = target_dir / "mineru-result.zip"
            if not zip_path.exists():
                download_zip(item["full_zip_url"], zip_path)
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(target_dir)
            record["result_dir"] = str(target_dir)
            record.pop("error", None)
            completed += 1
        save_json(manifest_path, manifest)
    return completed, failed


def summarize(manifest: dict[str, Any]) -> None:
    counts: dict[str, int] = {}
    for record in manifest["files"]:
        counts[record["state"]] = counts.get(record["state"], 0) + 1
    selected = sum(1 for record in manifest["files"] if record.get("selected"))
    print(json.dumps({"total": len(manifest["files"]), "selected": selected, "states": counts}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="output/mineru/private")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument(
        "--select-per-document-type",
        type=int,
        default=100,
        help="retain a deterministic sample of this size per document type; later runs may increase it",
    )
    parser.add_argument("--submit", action="store_true", help="request upload URLs and upload pending files")
    parser.add_argument("--collect", action="store_true", help="poll submitted batches and download completed results")
    parser.add_argument("--retry-upload-failures", action="store_true")
    arguments = parser.parse_args()
    if not 1 <= arguments.batch_size <= 50:
        parser.error("--batch-size must be between 1 and 50")
    if arguments.select_per_document_type < 1:
        parser.error("--select-per-document-type must be positive")

    repo_root = Path(__file__).resolve().parents[1]
    output_dir = (repo_root / arguments.output_dir).resolve()
    manifest_path = output_dir / "manifest.json"
    manifest = load_json(manifest_path, {"version": 1, "created_at": utc_now(), "files": []})
    if not manifest["files"]:
        manifest["files"] = discover_files(repo_root, DEFAULT_ROOTS, output_dir)
    select_records(manifest, arguments.select_per_document_type)
    save_json(manifest_path, manifest)
    if arguments.retry_upload_failures:
        for record in manifest["files"]:
            if record["state"] == "upload_failed":
                record["state"] = "new"
                record.pop("error", None)
        save_json(manifest_path, manifest)

    if arguments.submit or arguments.collect:
        token = os.environ.get("MINERU_API_TOKEN")
        if not token:
            parser.error("MINERU_API_TOKEN is required for --submit or --collect")
    else:
        token = ""
    if arguments.submit:
        submit_pending(repo_root, manifest, token, arguments.batch_size, arguments.max_batches, manifest_path)
    if arguments.collect:
        completed, failed = collect_results(manifest, token, output_dir, manifest_path)
        print(f"collected completed={completed} failed={failed}")
    summarize(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
