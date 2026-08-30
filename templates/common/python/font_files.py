"""Resolve exact licensed font files without allowing silent substitution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .typography import load_font_policy


def font_roots(local_font_dir: Path | None = None) -> list[Path]:
    roots: list[Path] = []
    if local_font_dir is not None:
        roots.append(local_font_dir)
    extra = os.environ.get("SZTU_FONT_DIR")
    if extra:
        roots.extend(Path(item).expanduser() for item in extra.split(os.pathsep) if item)
    if sys.platform == "darwin":
        roots.extend(
            [
                Path.home() / "Library" / "Fonts",
                Path("/Library/Fonts"),
                Path("/System/Library/Fonts"),
                Path("/System/Library/Fonts/Supplemental"),
            ]
        )
    elif os.name == "nt":
        roots.append(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")
    else:
        roots.extend(
            [
                Path.home() / ".local" / "share" / "fonts",
                Path.home() / ".fonts",
                Path("/usr/local/share/fonts"),
                Path("/usr/share/fonts"),
            ]
        )
    unique: list[Path] = []
    for root in roots:
        resolved = root.expanduser()
        if resolved.is_dir() and resolved not in unique:
            unique.append(resolved)
    return unique


def resolve_font_files(
    required_keys: list[str], *, local_font_dir: Path | None = None
) -> dict[str, Path]:
    policy = load_font_policy()
    definitions = policy["font_files"]
    unknown = set(required_keys) - set(definitions)
    if unknown:
        raise ValueError(f"unknown required font file keys: {sorted(unknown)}")

    index: dict[str, Path] = {}
    for root in font_roots(local_font_dir):
        for path in root.rglob("*"):
            if path.is_file():
                index.setdefault(path.name.casefold(), path.resolve())

    resolved: dict[str, Path] = {}
    missing: list[str] = []
    for key in required_keys:
        definition = definitions[key]
        override = os.environ.get(definition["environment"])
        if override:
            path = Path(override).expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError(
                    f"{definition['environment']} does not point to a font file: {path}"
                )
            resolved[key] = path
            continue
        path = next(
            (
                index[name.casefold()]
                for name in definition["candidates"]
                if name.casefold() in index
            ),
            None,
        )
        if path is None:
            missing.append(f"{key} ({'/'.join(definition['candidates'])})")
        else:
            resolved[key] = path
    if missing:
        raise FileNotFoundError(
            "required official fonts are missing; font substitution is forbidden: "
            + ", ".join(missing)
        )
    return resolved


def tex_font_parts(path: Path) -> tuple[str, str]:
    directory = path.parent.as_posix().rstrip("/") + "/"
    filename = path.name
    if any(character in directory + filename for character in ("{", "}", "%", "#")):
        raise ValueError(f"font path contains unsupported TeX characters: {path}")
    return directory, filename
