"""Resolve exact licensed font files without allowing silent substitution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .typography import load_font_policy


CJK_FAKE_BOLD_STRENGTH = 3
CJK_FAKE_SLANT_FACTOR = 0.2


def font_roots(local_font_dir: Path | None = None) -> list[Path]:
    roots: list[Path] = []
    if local_font_dir is not None:
        roots.insert(0, local_font_dir)
    extra = os.environ.get("SZTU_FONT_DIR")
    if extra:
        roots.extend(Path(item).expanduser() for item in extra.split(os.pathsep) if item)
    roots.append(Path(__file__).resolve().parents[3] / "fonts.local")
    if sys.platform == "darwin":
        roots.extend(
            [
                Path.home() / "Library" / "Fonts",
                Path("/Library/Fonts"),
                Path("/System/Library/Fonts"),
                Path("/System/Library/Fonts/Supplemental"),
                Path("/Applications/Microsoft Word.app/Contents/Resources/DFonts"),
                Path("/Applications/Microsoft Excel.app/Contents/Resources/DFonts"),
                Path("/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts"),
                Path("/Applications/wpsoffice.app/Contents/Resources/office6/fonts"),
            ]
        )
    elif os.name == "nt":
        roots.append(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")
        if os.environ.get("LOCALAPPDATA"):
            roots.append(Path(os.environ["LOCALAPPDATA"]) / "Microsoft/Windows/Fonts")
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


def discover_font_files(
    required_keys: list[str], *, local_font_dir: Path | None = None
) -> tuple[dict[str, Path], list[str]]:
    policy = load_font_policy()
    definitions = policy["font_files"]
    unknown = set(required_keys) - set(definitions)
    if unknown:
        raise ValueError(f"unknown required font file keys: {sorted(unknown)}")

    indexes: list[dict[str, Path]] = []
    for root in font_roots(local_font_dir):
        index: dict[str, Path] = {}
        for path in sorted(root.rglob("*")):
            if path.is_file():
                index.setdefault(path.name.casefold(), path.resolve())
        indexes.append(index)

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
                for index in indexes
                for name in definition["candidates"]
                if name.casefold() in index
            ),
            None,
        )
        if path is None:
            missing.append(f"{key} ({'/'.join(definition['candidates'])})")
        else:
            resolved[key] = path
    return resolved, missing


def resolve_font_files(
    required_keys: list[str], *, local_font_dir: Path | None = None
) -> dict[str, Path]:
    resolved, missing = discover_font_files(required_keys, local_font_dir=local_font_dir)
    if missing:
        raise FileNotFoundError(
            "缺少必需字体：" + ", ".join(missing)
            + "。请安装对应字体，或用 SZTU_FONT_DIR 指定字体文件夹；不会自动替换字体。"
        )
    return resolved


def tex_font_parts(path: Path) -> tuple[str, str]:
    directory = path.parent.as_posix().rstrip("/") + "/"
    filename = path.name
    if any(character in directory + filename for character in ("{", "}", "%", "#")):
        raise ValueError(f"font path contains unsupported TeX characters: {path}")
    return directory, filename


def cjk_emphasis_options(directory: str) -> str:
    """Return deterministic xeCJK options for regular-only official CJK fonts."""

    return ",".join(
        [
            f"Path={{{directory}}}",
            f"AutoFakeBold={CJK_FAKE_BOLD_STRENGTH:g}",
            f"AutoFakeSlant={CJK_FAKE_SLANT_FACTOR:g}",
        ]
    )
