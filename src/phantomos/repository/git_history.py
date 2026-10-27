"""Read Git metadata. This module never checks out, commits, resets, or fetches."""

from dataclasses import dataclass, field
from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, NoSuchPathError, Repo

from phantomos.exceptions import NotAGitRepositoryError, RepositoryError
from phantomos.repository.git_safety import open_git_repository
from phantomos.security.paths import resolve_directory

_INTERESTING_WORDS = (
    "security",
    "vuln",
    "cve",
    "revert",
    "breaking",
    "hotfix",
    "fix",
)


@dataclass(frozen=True)
class CommitInfo:
    """Metadata copied from a real commit object."""

    hexsha: str
    short_hash: str
    authored_at: str
    author_name: str | None
    author_email: str | None
    message: str
    summary: str
    parent_count: int


@dataclass(frozen=True)
class BranchInfo:
    """A local branch pointer. Reading it does not change HEAD."""

    name: str
    commit: str
    summary: str
    is_active: bool


@dataclass
class HistoryReport:
    """A read-only view of commits and branch pointers."""

    git_root: Path
    commits: list[CommitInfo] = field(default_factory=list)
    total_commits: int = 0
    oldest: CommitInfo | None = None
    newest: CommitInfo | None = None
    branches: list[BranchInfo] = field(default_factory=list)
    detached: bool = False
    unborn: bool = False
    bare: bool = False
    interesting: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _commit_info(commit: object) -> CommitInfo:
    author = getattr(commit, "author", None)
    authored = commit.authored_datetime
    return CommitInfo(
        hexsha=commit.hexsha,
        short_hash=commit.hexsha[:12],
        authored_at=authored.isoformat(timespec="seconds"),
        author_name=_clean(getattr(author, "name", None)),
        author_email=_clean(getattr(author, "email", None)),
        message=commit.message,
        summary=commit.summary,
        parent_count=len(commit.parents),
    )


def _interesting_notes(commits: list[CommitInfo]) -> list[str]:
    notes: list[str] = []
    for commit in commits:
        if commit.parent_count > 1:
            notes.append(
                f"Merge commit {commit.short_hash}: {commit.summary!r} "
                f"({commit.parent_count} parents)."
            )
        lowered = commit.summary.lower()
        matched = [word for word in _INTERESTING_WORDS if word in lowered]
        if matched:
            notes.append(
                f"Subject of {commit.short_hash} contains {matched!r}: {commit.summary!r}. "
                "This is a keyword match, not evidence of author intent or of a vulnerability."
            )
    return notes


def open_repository(path: Path) -> Repo:
    """Open a Git repository that contains `path`. Does not create one."""
    selected = resolve_directory(path)
    try:
        repo = open_git_repository(selected, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        raise NotAGitRepositoryError(
            f"Not a Git repository: {selected}. AI Alchemist did not run git init."
        ) from exc
    return repo


def inspect_history(path: Path, *, limit: int) -> HistoryReport:
    """Collect commit and branch metadata without changing repository state."""
    if limit < 1:
        raise RepositoryError("History limit must be at least 1.")
    repo = open_repository(path)
    if repo.bare or repo.working_tree_dir is None:
        root = Path(repo.git_dir).resolve()
        bare = True
    else:
        root = Path(repo.working_tree_dir).resolve()
        bare = False
    report = HistoryReport(git_root=root, bare=bare)
    report.notes.append("No branches were checked out and no Git state was changed.")

    if not repo.head.is_valid():
        report.unborn = True
        report.notes.append("This repository has no commits yet.")
        return report

    try:
        report.detached = bool(repo.head.is_detached)
    except (TypeError, ValueError):
        report.detached = True
    active_name: str | None = None
    if not report.detached:
        try:
            active_name = repo.active_branch.name
        except (TypeError, ValueError):
            report.detached = True

    try:
        report.total_commits = int(repo.git.rev_list("--count", "HEAD"))
    except GitCommandError:
        report.total_commits = 0

    recent = list(repo.iter_commits("HEAD", max_count=limit))
    report.commits = [_commit_info(commit) for commit in recent]
    if report.commits:
        report.newest = report.commits[0]
    # `git log --reverse -n 1` still returns the newest commit: max-count is applied
    # before the reverse. Root commits come from `--max-parents=0`.
    try:
        root_shas = [
            line.strip()
            for line in repo.git.rev_list("--max-parents=0", "HEAD").splitlines()
            if line.strip()
        ]
    except GitCommandError:
        root_shas = []
    if root_shas:
        earliest = min((repo.commit(sha) for sha in root_shas), key=lambda item: item.authored_datetime)
        report.oldest = _commit_info(earliest)
    report.interesting = _interesting_notes(report.commits)

    for head in repo.heads:
        try:
            summary = head.commit.summary
            hexsha = head.commit.hexsha
        except (ValueError, GitCommandError):
            continue
        report.branches.append(
            BranchInfo(
                name=head.name,
                commit=hexsha,
                summary=summary,
                is_active=active_name == head.name,
            )
        )
    report.branches.sort(key=lambda item: item.name.lower())
    if report.detached:
        report.notes.append("HEAD is detached. The active branch was left unchanged.")
    return report
