"""Temporary repositories for tests. These never touch a developer's real checkout."""

from pathlib import Path

from git import Actor, Repo

AUTHOR = Actor("Archive Tester", "archive@example.com")


def make_repo(path: Path) -> Repo:
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(path)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "Archive Tester")
        writer.set_value("user", "email", "archive@example.com")
    return repo


def commit_file(repo: Repo, relative: str, content: str, message: str):
    file_path = Path(repo.working_tree_dir) / relative
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    repo.index.add([relative])
    return repo.index.commit(message, author=AUTHOR, committer=AUTHOR)
