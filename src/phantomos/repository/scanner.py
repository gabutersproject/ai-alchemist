"""Directory, README, and manifest inspection. Nothing is executed or modified."""

import json
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from git import InvalidGitRepositoryError, NoSuchPathError, Repo

from phantomos.config import PhantomConfig
from phantomos.exceptions import FileSkippedError, SecretFileError, SensitiveContentError
from phantomos.repository.file_filters import (
    LOCKFILE_NAMES,
    MANIFEST_NAMES,
    README_NAMES,
    SOURCE_EXTENSIONS,
    FileRead,
    git_ignored_paths,
    is_excluded_dir,
    is_probably_binary,
    language_name,
    load_simple_ignore,
    read_for_analysis,
    simple_ignored,
)
from phantomos.repository.git_safety import open_git_repository
from phantomos.security.paths import is_symlink_or_junction, resolve_directory
from phantomos.security.secrets import is_secret_path


@dataclass
class ScanReport:
    """Facts collected by reading the tree. This is not a model response."""

    selected_path: Path
    git_root: Path | None
    bare_repository: bool = False
    excerpts: list[FileRead] = field(default_factory=list)
    source_paths: list[str] = field(default_factory=list)
    source_total: int = 0
    tree: str = ""
    files_seen: int = 0
    directories_seen: int = 0
    excluded_directories: int = 0
    skipped_secrets: list[str] = field(default_factory=list)
    skipped_sensitive_content: list[str] = field(default_factory=list)
    skipped_binary: int = 0
    skipped_large: int = 0
    skipped_symlinks: int = 0
    skipped_ignored: int = 0
    skipped_undecodable: int = 0
    manifests_found: list[str] = field(default_factory=list)
    lockfiles_found: list[str] = field(default_factory=list)
    metadata: list[str] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def find_git_root(path: Path) -> tuple[Path | None, bool]:
    """Return `(work tree, bare)` when `path` is inside a repository."""
    try:
        repo = open_git_repository(path, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return None, False
    if repo.bare or repo.working_tree_dir is None:
        return Path(repo.git_dir).resolve(), True
    root = Path(repo.working_tree_dir).resolve()
    try:
        path.resolve().relative_to(root)
    except ValueError:
        return None, False
    return root, False


def _metadata_for(excerpt: FileRead) -> list[str]:
    name = Path(excerpt.relative_path).name.lower()
    if name == "pyproject.toml":
        try:
            data = tomllib.loads(excerpt.text)
        except tomllib.TOMLDecodeError:
            return ["pyproject.toml is present but is not valid TOML."]
        project = data.get("project")
        lines: list[str] = []
        if isinstance(project, dict):
            if project.get("name"):
                lines.append(f"project.name = {project['name']}")
            if project.get("description"):
                lines.append(f"project.description = {project['description']}")
        return lines or ["pyproject.toml is present."]
    if name == "cargo.toml":
        try:
            data = tomllib.loads(excerpt.text)
        except tomllib.TOMLDecodeError:
            return ["Cargo.toml is present but is not valid TOML."]
        package = data.get("package")
        if isinstance(package, dict) and package.get("name"):
            return [f"cargo package.name = {package['name']}"]
        return ["Cargo.toml is present."]
    if name == "package.json":
        try:
            data = json.loads(excerpt.text)
        except json.JSONDecodeError:
            return ["package.json is present but is not valid JSON."]
        lines = []
        if isinstance(data, dict):
            if data.get("name"):
                lines.append(f"package.json name = {data['name']}")
            if data.get("description"):
                lines.append(f"package.json description = {data['description']}")
        return lines or ["package.json is present."]
    if name == "go.mod":
        for line in excerpt.text.splitlines():
            if line.startswith("module "):
                return [f"go module = {line.split(maxsplit=1)[1].strip()}"]
        return ["go.mod is present."]
    return []


def _build_tree(root: Path, *, max_depth: int, max_entries: int) -> str:
    lines = [root.name + "/"]
    count = 0

    def walk(directory: Path, depth: int, prefix: str) -> None:
        nonlocal count
        if depth > max_depth or count >= max_entries:
            return
        try:
            children = list(directory.iterdir())
        except OSError:
            return
        visible: list[Path] = []
        for child in children:
            try:
                if is_symlink_or_junction(child) or (child.is_dir() and is_excluded_dir(child.name)):
                    continue
            except OSError:
                continue
            visible.append(child)
        visible.sort(key=lambda item: (not item.is_dir(), item.name.lower()))
        for index, child in enumerate(visible):
            if count >= max_entries:
                lines.append(prefix + "…")
                return
            last = index == len(visible) - 1
            branch = "└── " if last else "├── "
            extension = "    " if last else "│   "
            suffix = "/" if child.is_dir() else ""
            lines.append(f"{prefix}{branch}{child.name}{suffix}")
            count += 1
            if child.is_dir():
                walk(child, depth + 1, prefix + extension)

    walk(root, 1, "")
    return "\n".join(lines)


def scan_repository(path: Path, config: PhantomConfig) -> ScanReport:
    """Walk `path` without following links that leave it, and without executing files."""
    selected = resolve_directory(path)
    git_root, bare = find_git_root(selected)
    report = ScanReport(selected_path=selected, git_root=git_root, bare_repository=bare)
    if any(part.lower() == ".git" for part in selected.parts):
        report.warnings.append(
            "The selected path is inside a .git directory. "
            "PhantomOS did not read Git internals."
        )
        report.tree = selected.name + "/"
        return report
    if bare and git_root == selected:
        report.warnings.append(
            "This path is a bare Git repository. Object storage was not scanned. "
            "History can still be read."
        )
        report.tree = selected.name + "/"
        return report

    repo: Repo | None = None
    if git_root is not None and not bare:
        try:
            repo = open_git_repository(git_root)
        except (InvalidGitRepositoryError, NoSuchPathError):
            repo = None
    simple_patterns = [] if repo is not None else load_simple_ignore(selected)
    candidates: list[tuple[Path, str]] = []

    for dirpath, dirnames, filenames in os.walk(selected, followlinks=False):
        current = Path(dirpath)
        report.directories_seen += 1
        kept: list[str] = []
        for name in list(dirnames):
            child = current / name
            if is_symlink_or_junction(child):
                report.skipped_symlinks += 1
                continue
            if is_excluded_dir(name):
                report.excluded_directories += 1
                continue
            kept.append(name)
        dirnames[:] = kept

        for name in filenames:
            full = current / name
            report.files_seen += 1
            if is_symlink_or_junction(full):
                report.skipped_symlinks += 1
                continue
            relative = full.relative_to(selected).as_posix()
            if is_secret_path(full):
                report.skipped_secrets.append(relative)
                continue
            try:
                size = full.stat().st_size
            except OSError:
                report.warnings.append(f"Could not stat {relative}.")
                continue
            lowered = name.lower()
            if lowered in LOCKFILE_NAMES:
                report.lockfiles_found.append(relative)
                continue
            is_readme = lowered in README_NAMES
            is_manifest = lowered in MANIFEST_NAMES
            is_source = full.suffix.lower() in SOURCE_EXTENSIONS
            if not (is_readme or is_manifest or is_source):
                if is_probably_binary(full):
                    report.skipped_binary += 1
                continue
            if size > config.max_file_bytes:
                report.skipped_large += 1
                continue
            if is_probably_binary(full):
                report.skipped_binary += 1
                continue
            candidates.append((full, relative))

    ignored: set[str] = set()
    if repo is not None and candidates:
        ignored = git_ignored_paths(repo, [item[0] for item in candidates])
    kept_candidates: list[tuple[Path, str]] = []
    for full, relative in candidates:
        if repo is not None and str(full.resolve()) in ignored:
            report.skipped_ignored += 1
            continue
        if repo is None and simple_ignored(simple_patterns, relative):
            report.skipped_ignored += 1
            continue
        kept_candidates.append((full, relative))

    for full, relative in kept_candidates:
        lowered = full.name.lower()
        if lowered in README_NAMES or lowered in MANIFEST_NAMES:
            try:
                excerpt = read_for_analysis(
                    selected, relative, max_bytes=config.max_file_bytes
                )
            except SecretFileError:
                report.skipped_secrets.append(relative)
                continue
            except SensitiveContentError:
                report.skipped_sensitive_content.append(relative)
                report.warnings.append(
                    f"Skipped {relative}: the file appears to contain credential material."
                )
                continue
            except FileSkippedError as exc:
                message = str(exc).lower()
                if "binary" in message:
                    report.skipped_binary += 1
                elif "utf-8" in message:
                    report.skipped_undecodable += 1
                elif "above the limit" in message:
                    report.skipped_large += 1
                else:
                    report.warnings.append(str(exc))
                continue
            report.excerpts.append(excerpt)
            if lowered in MANIFEST_NAMES:
                report.manifests_found.append(relative)
            report.metadata.extend(_metadata_for(excerpt))
            continue
        report.source_total += 1
        language = language_name(full.suffix)
        report.languages[language] = report.languages.get(language, 0) + 1
        if len(report.source_paths) < 5000:
            report.source_paths.append(relative)

    report.source_paths.sort()
    report.manifests_found.sort()
    report.lockfiles_found.sort()
    report.skipped_secrets.sort()
    report.excerpts.sort(key=lambda item: item.relative_path)
    if report.source_total > len(report.source_paths):
        report.warnings.append("The stored source-file list was capped at 5000 paths.")
    report.tree = _build_tree(
        selected,
        max_depth=config.max_tree_depth,
        max_entries=config.max_tree_entries,
    )
    return report
