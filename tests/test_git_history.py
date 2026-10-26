"""Git history comes from the repository and does not change it."""

from pathlib import Path

import pytest

from phantomos.exceptions import NotAGitRepositoryError
from phantomos.repository.git_history import inspect_history
from tests.helpers import commit_file, make_repo


def test_history_uses_real_commits_and_stays_read_only(tmp_path: Path):
    root = tmp_path / "repo"
    repo = make_repo(root)
    first = commit_file(repo, "readme.md", "one\n", "first memory")
    repo.create_head("old-experiment", first)
    second = commit_file(repo, "readme.md", "two\n", "fixed the lamp")
    head_before = repo.head.commit.hexsha
    status_before = repo.git.status("--porcelain")
    active = repo.active_branch.name

    report = inspect_history(root, limit=10)

    assert report.oldest is not None
    assert report.newest is not None
    assert report.oldest.hexsha == first.hexsha
    assert report.newest.hexsha == second.hexsha
    assert report.newest.summary == "fixed the lamp"
    assert report.newest.author_name == "Archive Tester"
    assert report.total_commits == 2
    assert any(branch.name == "old-experiment" and not branch.is_active for branch in report.branches)
    assert any(branch.name == active and branch.is_active for branch in report.branches)
    assert any("fixed the lamp" in note for note in report.interesting)
    assert any("keyword" in note.lower() for note in report.interesting)
    assert repo.head.commit.hexsha == head_before
    assert repo.active_branch.name == active
    assert repo.git.status("--porcelain") == status_before


def test_empty_repository_has_no_invented_commits(tmp_path: Path):
    root = tmp_path / "empty"
    make_repo(root)
    report = inspect_history(root, limit=5)
    assert report.unborn
    assert report.commits == []
    assert report.oldest is None
    assert report.newest is None


def test_non_git_directory_is_rejected(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(NotAGitRepositoryError):
        inspect_history(plain, limit=5)
