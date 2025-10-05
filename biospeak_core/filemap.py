"""Utility to describe repository contents."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

EXCLUDED = {".git", "__pycache__", "build", "dist"}


def _should_skip(path: Path) -> bool:
    return any(part in EXCLUDED for part in path.parts)


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if _should_skip(path.relative_to(root)):
            continue
        if path.is_file():
            yield path


def describe_path(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    size = path.stat().st_size
    return f"{rel.as_posix()} ({size} bytes)"


def generate_file_map(root: str | Path | None = None) -> List[str]:
    """Return a list of descriptive lines for every project file."""
    base = Path(root or Path(__file__).resolve().parent.parent)
    return [describe_path(path, base) for path in iter_files(base)]

