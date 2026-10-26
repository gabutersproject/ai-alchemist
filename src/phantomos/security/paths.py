"""Path containment. Repository text is never trusted to choose a path."""

import os
import re
from pathlib import Path

from phantomos.exceptions import PathSecurityError, RepositoryError

_DRIVE = re.compile(r"^[A-Za-z]:")


def normalize_relative_parts(relative: str) -> list[str]:
    """Split a user path and reject traversal, absolute paths, and null bytes.

    Backslashes are treated as separators so Windows-style traversal is rejected
    on every platform.
    """
    if "\x00" in relative:
        raise PathSecurityError("Paths cannot contain null bytes.")
    raw = relative.strip()
    if not raw:
        raise PathSecurityError("A relative file path is required.")
    unified = raw.replace("\\", "/")
    if unified.startswith("//") or unified.startswith("/"):
        raise PathSecurityError(
            "Absolute paths are not allowed. Pass a path relative to the selected directory."
        )
    if _DRIVE.match(unified):
        raise PathSecurityError("Drive-absolute paths are not allowed.")
    parts: list[str] = []
    for part in unified.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise PathSecurityError("Path traversal ('..') is not allowed.")
        parts.append(part)
    if not parts:
        raise PathSecurityError("A relative file path is required.")
    return parts


def resolve_directory(path: Path) -> Path:
    """Resolve an existing directory. A symlinked directory becomes its real path."""
    try:
        resolved = path.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise RepositoryError(f"Path does not exist: {path}") from exc
    except OSError as exc:
        raise RepositoryError(f"Cannot read path: {path} ({exc})") from exc
    if not resolved.is_dir():
        raise RepositoryError(f"Path is not a directory: {resolved}")
    return resolved


def is_symlink_or_junction(path: Path) -> bool:
    """True for a symbolic link or a Windows junction. Unreadable paths fail closed."""
    try:
        if path.is_symlink():
            return True
    except OSError:
        return True
    checker = getattr(os.path, "isjunction", None)
    if checker is None:
        return False
    try:
        return bool(checker(path))
    except OSError:
        return True


def _require_within(root: Path, candidate: Path, display: str) -> Path:
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise PathSecurityError(
            f"Path escapes the repository and was refused: {display}"
        ) from exc
    return resolved


def safe_child(root: Path, relative: str) -> Path:
    """Resolve `relative` and require every symlink or junction target to stay inside `root`."""
    root_real = root.expanduser().resolve()
    if not root_real.is_dir():
        raise RepositoryError(f"Repository path is not a directory: {root}")
    parts = normalize_relative_parts(relative)
    current = root_real
    for part in parts:
        if current.exists() and not current.is_dir():
            raise PathSecurityError(f"Not a directory along the path: {relative}")
        candidate = current / part
        if is_symlink_or_junction(candidate):
            try:
                target = candidate.resolve(strict=True)
            except FileNotFoundError as exc:
                raise PathSecurityError(
                    f"Symbolic link is broken and was refused: {relative}"
                ) from exc
            except OSError as exc:
                raise PathSecurityError(
                    f"Cannot resolve symbolic link safely: {relative}"
                ) from exc
            try:
                target.relative_to(root_real)
            except ValueError as exc:
                raise PathSecurityError(
                    f"Symbolic link points outside the repository and was refused: {relative}"
                ) from exc
            current = target
            continue
        current = candidate
    if current.exists():
        return _require_within(root_real, current, relative)
    try:
        current.resolve().relative_to(root_real)
    except (OSError, ValueError) as exc:
        raise PathSecurityError(
            f"Path escapes the repository and was refused: {relative}"
        ) from exc
    return current
