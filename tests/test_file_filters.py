"""Secret, binary, size, and ignore filters."""

from pathlib import Path

import pytest

from ai_alchemist.config import AlchemistConfig
from ai_alchemist.exceptions import FileSkippedError, SecretFileError, SensitiveContentError
from ai_alchemist.repository.file_filters import (
    is_probably_binary,
    read_for_analysis,
    simple_ignored,
)
from ai_alchemist.security.secrets import content_looks_sensitive, is_secret_path


def test_secret_names_and_examples(tmp_path: Path):
    assert is_secret_path(Path(".env"))
    assert is_secret_path(Path("config") / ".env.production")
    assert is_secret_path(Path("keys") / "id_rsa")
    assert is_secret_path(Path("certs") / "server.pem")
    assert is_secret_path(Path(".ssh") / "config")
    assert not is_secret_path(Path(".env.example"))
    assert not is_secret_path(Path("README.md"))


def test_sensitive_content_detector_does_not_echo_the_secret():
    assert content_looks_sensitive("-----BEGIN PRIVATE KEY-----\nabc")
    assert content_looks_sensitive("token = ghp_abcdefghijklmnopqrstuvwxyz")
    assert not content_looks_sensitive("def average(xs):\n    return 1\n")


def test_secret_file_is_not_read(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    secret = repo / ".env"
    secret.write_text("TOKEN=super-secret-value\n", encoding="utf-8")
    with pytest.raises(SecretFileError):
        read_for_analysis(repo, ".env", max_bytes=10_000)
    assert secret.read_text(encoding="utf-8") == "TOKEN=super-secret-value\n"


def test_symlink_to_a_secret_file_is_not_read(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    secret = repo / ".env"
    secret.write_text("TOKEN=super-secret-value\n", encoding="utf-8")
    link = repo / "notes.md"
    try:
        link.symlink_to(secret)
    except OSError:
        pytest.skip("symbolic links are not available")
    with pytest.raises(SecretFileError) as caught:
        read_for_analysis(repo, "notes.md", max_bytes=10_000)
    assert "super-secret-value" not in str(caught.value)
    assert secret.read_text(encoding="utf-8") == "TOKEN=super-secret-value\n"


def test_symlink_to_an_ordinary_file_can_be_read(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "real.py"
    target.write_text("value = 1\n", encoding="utf-8")
    link = repo / "alias.py"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are not available")
    loaded = read_for_analysis(repo, "alias.py", max_bytes=10_000)
    assert loaded.text == "value = 1\n"


def test_windows_relative_secret_is_not_read(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "keys").mkdir(parents=True)
    (repo / "keys" / "id_rsa").write_text("private", encoding="utf-8")
    with pytest.raises(SecretFileError):
        read_for_analysis(repo, "keys\\id_rsa", max_bytes=10_000)


def test_binary_and_large_files_are_skipped(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    binary = repo / "blob.bin"
    binary.write_bytes(b"\x00\x01\x02")
    assert is_probably_binary(binary)
    text = repo / "notes.txt"
    text.write_text("x" * 50, encoding="utf-8")
    with pytest.raises(FileSkippedError):
        read_for_analysis(repo, "notes.txt", max_bytes=10)


def test_private_key_inside_source_is_refused(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "keys.py").write_text(
        'TOKEN = "-----BEGIN PRIVATE KEY-----\\nABC\\n"\n',
        encoding="utf-8",
    )
    with pytest.raises(SensitiveContentError):
        read_for_analysis(repo, "src/keys.py", max_bytes=10_000)


def test_excluded_directory_is_refused(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "node_modules").mkdir(parents=True)
    (repo / "node_modules" / "left.js").write_text("module.exports = 1\n", encoding="utf-8")
    with pytest.raises(FileSkippedError):
        read_for_analysis(repo, "node_modules/left.js", max_bytes=10_000)


def test_simple_gitignore_patterns():
    patterns = ["build/", "*.log", "secret_notes.py"]
    assert simple_ignored(patterns, "build/output.js")
    assert simple_ignored(patterns, "debug.log")
    assert simple_ignored(patterns, "secret_notes.py")
    assert not simple_ignored(patterns, "src/app.py")


def test_config_size_limit_is_positive():
    assert AlchemistConfig().max_file_bytes > 0
