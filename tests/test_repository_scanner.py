"""Repository scanning returns real files and skips dangerous ones."""

import os
from pathlib import Path

from ai_alchemist.ai.context import build_inspect_prompt
from ai_alchemist.config import AlchemistConfig
from ai_alchemist.repository.code_explainer import outline_source
from ai_alchemist.repository.file_filters import FileRead
from ai_alchemist.repository.scanner import scan_repository
from tests.helpers import commit_file, make_repo


def _project(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "README.md").write_text("# Lamp Archive\n\nA leftover catalog.\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "lamp-archive"\ndescription = "Old lamp readings."\n',
        encoding="utf-8",
    )
    (root / "src" / "catalog.py").write_text(
        "def average_brightness(readings):\n    return readings[0]\n",
        encoding="utf-8",
    )
    (root / "node_modules").mkdir()
    (root / "node_modules" / "leftpad.js").write_text("module.exports = 1\n", encoding="utf-8")
    (root / "build").mkdir()
    (root / "build" / "out.js").write_text("compiled\n", encoding="utf-8")
    (root / ".env").write_text("TOKEN=super-secret-value\n", encoding="utf-8")
    (root / ".env.example").write_text("TOKEN=replace-me\n", encoding="utf-8")
    (root / "blob.bin").write_bytes(b"\x00\x01binary")


def test_scan_reports_real_files_and_skips_secrets(tmp_path: Path):
    root = tmp_path / "proj"
    _project(root)
    report = scan_repository(root, AlchemistConfig())
    texts = "\n".join(item.text for item in report.excerpts)
    assert report.git_root is None
    assert any(item.relative_path == "README.md" for item in report.excerpts)
    assert "super-secret-value" not in texts
    assert ".env" in report.skipped_secrets
    assert any("catalog.py" in path for path in report.source_paths)
    assert all("leftpad" not in path for path in report.source_paths)
    assert all(not path.startswith("build/") for path in report.source_paths)
    assert report.excluded_directories >= 2
    assert report.skipped_binary >= 1
    assert any("lamp-archive" in line for line in report.metadata)
    assert report.languages.get("Python") == 1
    assert "leftpad" not in report.tree
    bundle = build_inspect_prompt(report, AlchemistConfig())
    prompt = "\n".join(message.content for message in bundle.messages)
    assert "super-secret-value" not in prompt
    assert "README.md" in bundle.files_used


def test_non_git_directory_still_scans(tmp_path: Path):
    root = tmp_path / "plain"
    root.mkdir()
    (root / "README.md").write_text("Just notes.\n", encoding="utf-8")
    report = scan_repository(root, AlchemistConfig())
    assert report.git_root is None
    assert report.files_seen == 1


def test_gitignore_and_negation_use_git(tmp_path: Path):
    root = tmp_path / "repo"
    repo = make_repo(root)
    (root / ".gitignore").write_text("*.txt\n!keep.txt\n", encoding="utf-8")
    commit_file(repo, ".gitignore", (root / ".gitignore").read_text(encoding="utf-8"), "ignore rules")
    (root / "drop.txt").write_text("drop me\n", encoding="utf-8")
    (root / "keep.txt").write_text("keep me\n", encoding="utf-8")
    report = scan_repository(root, AlchemistConfig())
    assert "keep.txt" in report.source_paths
    assert "drop.txt" not in report.source_paths
    assert report.skipped_ignored >= 1


def test_simple_gitignore_without_git(tmp_path: Path):
    root = tmp_path / "plain"
    root.mkdir()
    (root / ".gitignore").write_text("secret_notes.py\n", encoding="utf-8")
    (root / "secret_notes.py").write_text("x = 1\n", encoding="utf-8")
    (root / "kept.py").write_text("y = 2\n", encoding="utf-8")
    report = scan_repository(root, AlchemistConfig())
    assert "kept.py" in report.source_paths
    assert "secret_notes.py" not in report.source_paths


def test_large_file_is_counted_not_read_into_context(tmp_path: Path):
    root = tmp_path / "plain"
    root.mkdir()
    (root / "README.md").write_text("short\n", encoding="utf-8")
    (root / "huge.py").write_text("x = 1\n" * 100, encoding="utf-8")
    config = AlchemistConfig(max_file_bytes=20)
    report = scan_repository(root, config)
    assert report.skipped_large >= 1
    assert "huge.py" not in report.source_paths
    prompt = "\n".join(message.content for message in build_inspect_prompt(report, config).messages)
    assert "x = 1" not in prompt


def test_python_outline_is_static(tmp_path: Path):
    source = FileRead(
        relative_path="src/catalog.py",
        text="import math\n\nclass Lamp:\n    def average_brightness(self, readings):\n        return readings[0]\n",
        byte_size=80,
    )
    outline = outline_source(source)
    rendered = outline.render()
    assert outline.executed is False
    assert "average_brightness" in rendered
    assert "Lamp" in rendered
    assert "was not executed" in rendered
    broken = FileRead(relative_path="bad.py", text="def (\n", byte_size=6)
    note = outline_source(broken)
    assert "parser" in note.parse_note.lower()
    assert note.executed is False


def test_selecting_a_git_directory_does_not_read_it(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    git_dir = root / ".git"
    git_dir.mkdir()
    (git_dir / "README.md").write_text("SECRET-GIT-README\n", encoding="utf-8")
    (git_dir / "config").write_text("token = super-secret-value\n", encoding="utf-8")
    report = scan_repository(git_dir, AlchemistConfig())
    combined = "\n".join(item.text for item in report.excerpts)
    assert "SECRET-GIT-README" not in combined
    assert "super-secret-value" not in combined
    assert report.files_seen == 0
    assert report.source_paths == []


def test_junction_directory_is_not_walked(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    gate = root / "gate"
    gate.mkdir(parents=True)
    (gate / "app.py").write_text("secret_marker = 1\n", encoding="utf-8")
    (root / "ok.py").write_text("value = 1\n", encoding="utf-8")

    def isjunction(path):
        return Path(path).name == "gate"

    monkeypatch.setattr(os.path, "isjunction", isjunction)
    report = scan_repository(root, AlchemistConfig())
    assert "ok.py" in report.source_paths
    assert "gate/app.py" not in report.source_paths
    prompt = "\n".join(message.content for message in build_inspect_prompt(report, AlchemistConfig()).messages)
    assert "secret_marker" not in prompt
    assert report.skipped_symlinks >= 1
