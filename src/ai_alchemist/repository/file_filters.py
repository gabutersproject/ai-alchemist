"""Rules for which files may be read, counted, or sent to a model."""

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path

from git import GitCommandError, Repo

from ai_alchemist.exceptions import (
    FileSkippedError,
    PathSecurityError,
    RepositoryError,
    SecretFileError,
    SensitiveContentError,
)
from ai_alchemist.security.paths import normalize_relative_parts, safe_child
from ai_alchemist.security.secrets import content_looks_sensitive, is_secret_path

EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        "bower_components",
        ".venv",
        "venv",
        "env",
        ".tox",
        ".nox",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".cache",
        ".parcel-cache",
        "dist",
        "build",
        "target",
        "out",
        ".next",
        ".nuxt",
        ".output",
        "coverage",
        "htmlcov",
        ".idea",
        "vendor",
        "Pods",
        ".terraform",
        "site-packages",
    }
)

BINARY_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".bmp",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".class",
        ".o",
        ".a",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".mp3",
        ".mp4",
        ".wav",
        ".avi",
        ".mov",
        ".pyc",
        ".pyo",
        ".wasm",
        ".sqlite",
        ".db",
        ".parquet",
        ".pickle",
        ".pkl",
    }
)

LOCKFILE_NAMES = frozenset(
    {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "cargo.lock",
        "poetry.lock",
        "pipfile.lock",
        "composer.lock",
        "gemfile.lock",
        "go.sum",
    }
)

MANIFEST_NAMES = frozenset(
    {
        "pyproject.toml",
        "requirements.txt",
        "pipfile",
        "package.json",
        "cargo.toml",
        "go.mod",
        "gemfile",
        "composer.json",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "package.swift",
        "mix.exs",
        "pubspec.yaml",
    }
)

README_NAMES = frozenset({"readme", "readme.md", "readme.rst", "readme.txt"})

SOURCE_EXTENSIONS = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".sh",
        ".ps1",
        ".sql",
        ".lua",
        ".toml",
        ".yaml",
        ".yml",
        ".json",
        ".md",
        ".rst",
        ".txt",
        ".css",
        ".html",
        ".vue",
        ".svelte",
    }
)


@dataclass(frozen=True)
class FileRead:
    """Text that passed the security checks."""

    relative_path: str
    text: str
    byte_size: int


_LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".lua": "Lua",
    ".css": "CSS",
    ".html": "HTML",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".txt": "Text",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
}


def language_name(suffix: str) -> str:
    """Language label from a file extension. This does not read or execute the file."""
    return _LANGUAGE_BY_SUFFIX.get(suffix.lower(), "Other")


def is_excluded_dir(name: str) -> bool:
    """True for dependency, cache, build, and VCS directories."""
    return name in EXCLUDED_DIR_NAMES or name.endswith(".egg-info")


def is_probably_binary(path: Path) -> bool:
    """Use the extension first, then a short null-byte sample."""
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with path.open("rb") as handle:
            sample = handle.read(8192)
    except OSError:
        return True
    return b"\x00" in sample


def load_simple_ignore(root: Path) -> list[str]:
    """Best-effort `.gitignore` patterns used when Git itself is unavailable."""
    path = root / ".gitignore"
    try:
        if not path.is_file() or path.is_symlink():
            return []
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    patterns: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue
        patterns.append(stripped)
    return patterns


def simple_ignored(patterns: list[str], relative: str) -> bool:
    """Match a small subset of gitignore syntax. Negation is not supported."""
    rel = relative.replace("\\", "/")
    name = rel.rsplit("/", 1)[-1]
    for pattern in patterns:
        directory = pattern.endswith("/")
        pat = pattern.rstrip("/")
        if pat.endswith("/**"):
            prefix = pat[:-3].rstrip("/")
            if rel == prefix or rel.startswith(prefix + "/"):
                return True
            continue
        if any(token in pat for token in "*?["):
            if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel, pat):
                return True
            continue
        if directory or "/" in pat:
            prefix = pat.rstrip("/")
            if rel == prefix or rel.startswith(prefix + "/"):
                return True
            continue
        if name == pat or rel == pat:
            return True
    return False


def git_ignored_paths(repo: Repo, paths: list[Path]) -> set[str]:
    """Ask Git which of `paths` are ignored. A Git failure ignores nothing extra."""
    wanted = {str(path.resolve()) for path in paths}
    ignored: set[str] = set()
    root = Path(repo.working_tree_dir or repo.git_dir)
    for offset in range(0, len(paths), 50):
        chunk = paths[offset : offset + 50]
        if not chunk:
            continue
        try:
            output = repo.git.check_ignore("--", *[os.fspath(path) for path in chunk])
        except GitCommandError as exc:
            output = exc.stdout or ""
        for line in str(output).splitlines():
            cleaned = line.strip().strip('"')
            if not cleaned:
                continue
            candidate = Path(cleaned)
            if not candidate.is_absolute():
                candidate = root / candidate
            try:
                resolved = str(candidate.resolve())
            except OSError:
                continue
            if resolved in wanted:
                ignored.add(resolved)
    return ignored


def has_excluded_parent(relative: str) -> bool:
    """True when any parent directory is on the exclusion list."""
    parts = relative.replace("\\", "/").split("/")
    return any(is_excluded_dir(part) for part in parts[:-1])


def read_for_analysis(root: Path, relative: str, *, max_bytes: int) -> FileRead:
    """Read one text file or raise a specific refusal. Contents of refusals stay unread."""
    parts = normalize_relative_parts(relative)
    display = "/".join(parts)
    if has_excluded_parent(display):
        raise FileSkippedError(
            f"'{display}' is inside an excluded directory and was not read."
        )
    if is_secret_path(Path(*parts)):
        raise SecretFileError(display)
    full = safe_child(root, display)
    try:
        relative_real = full.resolve().relative_to(root.expanduser().resolve())
    except (OSError, ValueError) as exc:
        raise PathSecurityError(
            f"Path escapes the repository and was refused: {display}"
        ) from exc
    if is_secret_path(full) or is_secret_path(relative_real):
        raise SecretFileError(display)
    if not full.exists():
        raise RepositoryError(f"File does not exist: {display}")
    if not full.is_file():
        raise RepositoryError(f"Not a file: {display}")
    try:
        size = full.stat().st_size
    except OSError as exc:
        raise FileSkippedError(f"Cannot stat '{display}': {exc}") from exc
    if size > max_bytes:
        raise FileSkippedError(
            f"'{display}' is {size} bytes, above the limit of {max_bytes}, and was not read."
        )
    if is_probably_binary(full):
        raise FileSkippedError(f"'{display}' looks like a binary file and was not read.")
    try:
        text = full.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise FileSkippedError(f"'{display}' is not valid UTF-8 and was not read.") from exc
    except OSError as exc:
        raise FileSkippedError(f"Cannot read '{display}': {exc}") from exc
    if content_looks_sensitive(text):
        raise SensitiveContentError(display)
    return FileRead(relative_path=display, text=text, byte_size=size)
