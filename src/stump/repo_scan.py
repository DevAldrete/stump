"""
Discover source files under a directory and apply .gitignore-style filtering.

Only ``ignore_root/.gitignore`` is loaded (plus ``--extra-ignore`` lines), merged
into one pathspec. Per-subdirectory ``.gitignore`` files are not applied yet;
paths are matched relative to ``ignore_root`` the same way as for a repository
root ignore file.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from pathspec import PathSpec

# Extension -> Stump language name (internal parser id)
EXT_TO_LANG = {
    ".py": "python",
    ".java": "java",
    ".cs": "csharp",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
}


def find_git_toplevel(start: Path) -> Optional[Path]:
    """Return git work tree root, or None if not in a git repo."""
    start = start.resolve()
    try:
        out = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()).resolve()
    except (FileNotFoundError, OSError):
        pass
    cur = start
    while True:
        if (cur / ".git").exists():
            return cur.resolve()
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _read_gitignore_lines(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [line.rstrip("\n\r") for line in text.splitlines()]


def _compile_gitignore_spec(lines: Iterable[str]) -> Optional[PathSpec]:
    plines = [
        ln
        for ln in lines
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    if not plines:
        return None
    return PathSpec.from_lines("gitignore", plines)


def load_gitignore_spec(
    ignore_root: Path,
    extra_patterns: Optional[List[str]] = None,
) -> Optional[PathSpec]:
    """
    Load patterns from ignore_root/.gitignore plus optional extra gitwildmatch lines.
    """
    ignore_root = ignore_root.resolve()
    merged: List[str] = []
    gi = ignore_root / ".gitignore"
    if gi.is_file():
        merged.extend(_read_gitignore_lines(gi))
    if extra_patterns:
        merged.extend(extra_patterns)
    return _compile_gitignore_spec(merged)


def _path_under_git_dir(path: Path) -> bool:
    return any(part == ".git" for part in path.parts)


def is_path_ignored(
    file_path: Path,
    ignore_root: Path,
    spec: Optional[PathSpec],
) -> bool:
    """Whether file_path should be skipped when using the given spec (paths relative to ignore_root)."""
    if spec is None:
        return False
    file_path = file_path.resolve()
    ignore_root = ignore_root.resolve()
    try:
        rel = file_path.relative_to(ignore_root).as_posix()
    except ValueError:
        return False
    if _path_under_git_dir(file_path):
        return True
    return spec.match_file(rel)


def collect_source_files(
    scan_root: Path,
    ignore_root: Path,
    spec: Optional[PathSpec],
    use_gitignore: bool,
    language: Optional[str],
) -> List[Tuple[Path, str]]:
    """
    Sorted list of (absolute_path, language) for files to chunk.

    language=None means auto-detect from extension; otherwise only that language's extensions.
    """
    scan_root = scan_root.resolve()
    ignore_root = ignore_root.resolve()
    out: List[Tuple[Path, str]] = []

    for path in sorted(scan_root.rglob("*")):
        if not path.is_file():
            continue
        if _path_under_git_dir(path):
            continue
        if use_gitignore and is_path_ignored(path, ignore_root, spec):
            continue
        suffix = path.suffix.lower()
        lang = EXT_TO_LANG.get(suffix)
        if language is not None:
            if lang != language:
                continue
        elif lang is None:
            continue
        out.append((path.resolve(), lang))

    out.sort(key=lambda t: str(t[0]))
    return out


def resolve_ignore_root(scan_root: Path, override: Optional[Path]) -> Path:
    if override is not None:
        return override.resolve()
    found = find_git_toplevel(scan_root)
    if found is not None:
        return found
    return scan_root.resolve()
