"""Path containment, including Windows-style traversal on any host."""

import os
from pathlib import Path

import pytest

from ai_alchemist.exceptions import PathSecurityError, RepositoryError
from ai_alchemist.security.paths import resolve_directory, safe_child


def test_rejects_missing_and_file_paths(tmp_path: Path):
    with pytest.raises(RepositoryError):
        resolve_directory(tmp_path / "missing")
    target = tmp_path / "file.txt"
    target.write_text("x", encoding="utf-8")
    with pytest.raises(RepositoryError):
        resolve_directory(target)


def test_rejects_traversal_absolute_and_windows_paths(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(PathSecurityError):
        safe_child(repo, "../outside.txt")
    with pytest.raises(PathSecurityError):
        safe_child(repo, "..\\..\\Windows\\System32\\config\\SAM")
    with pytest.raises(PathSecurityError):
        safe_child(repo, "/etc/passwd")
    with pytest.raises(PathSecurityError):
        safe_child(repo, "C:\\Windows\\System32\\cmd.exe")
    with pytest.raises(PathSecurityError):
        safe_child(repo, "\\\\server\\share\\secret")
    with pytest.raises(PathSecurityError):
        safe_child(repo, "src/\x00evil.py")


def test_accepts_windows_separators_for_an_inside_file(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    target = repo / "src" / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")
    resolved = safe_child(repo, "src\\app.py")
    assert resolved == target.resolve()


def test_symlink_escape_is_refused(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside-secret", encoding="utf-8")
    link = repo / "leak.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links are not available")
    with pytest.raises(PathSecurityError):
        safe_child(repo, "leak.txt")


def test_symlink_inside_repository_can_be_resolved(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "real.py"
    target.write_text("value = 1\n", encoding="utf-8")
    link = repo / "alias.py"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are not available")
    assert safe_child(repo, "alias.py") == target.resolve()


def test_junction_pointing_outside_is_refused(tmp_path: Path, monkeypatch):
    """Windows junctions are not symlinks. Simulate one without requiring Windows."""
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("nope", encoding="utf-8")
    gate = repo / "gate"
    gate.mkdir()
    (gate / "secret.txt").write_text("decoy", encoding="utf-8")
    real_resolve = Path.resolve

    def resolve(self, *args, **kwargs):
        if self == gate:
            return real_resolve(outside)
        return real_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    monkeypatch.setattr(os.path, "isjunction", lambda path: Path(path) == gate)
    with pytest.raises(PathSecurityError):
        safe_child(repo, "gate/secret.txt")
    assert (outside / "secret.txt").read_text(encoding="utf-8") == "nope"


def test_broken_symlink_is_refused(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    link = repo / "broken.py"
    try:
        link.symlink_to(repo / "missing.py")
    except OSError:
        pytest.skip("symbolic links are not available")
    with pytest.raises(PathSecurityError):
        safe_child(repo, "broken.py")
