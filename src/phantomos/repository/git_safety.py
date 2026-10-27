"""Keep Git from honoring repository config that executes programs.

Git runs ``core.fsmonitor`` during ordinary read commands such as ``rev-list``.
A repository can point that setting at a program. AI Alchemist overrides the
    settings below for its own process so repository content cannot choose a
    command. This does not modify the repository's config file. Git is still
    invoked through GitPython.
"""

import os
import tempfile
from pathlib import Path

from git import Repo

_INSTALLED = False

# Keys whose values Git may treat as a program or as a hook directory.
_OVERRIDE_KEYS = (
    "core.fsmonitor",
    "core.hooksPath",
    "core.sshCommand",
    "core.pager",
    "diff.external",
    "credential.helper",
    "protocol.ext.allow",
)


def ensure_git_readonly_env() -> None:
    """Apply command-line Git config that outranks repository config.

    The overrides are appended to any ``GIT_CONFIG_COUNT`` block already in
    the environment. They last for this process only.
    """
    global _INSTALLED
    if _INSTALLED:
        return
    hooks = Path(tempfile.mkdtemp(prefix="phantomos-no-hooks-"))
    values = {
        "core.fsmonitor": "",
        "core.hooksPath": str(hooks),
        "core.sshCommand": "",
        "core.pager": "cat",
        "diff.external": "",
        "credential.helper": "",
        "protocol.ext.allow": "never",
    }
    try:
        start = int(os.environ.get("GIT_CONFIG_COUNT", "") or "0")
    except ValueError:
        start = 0
    if start < 0:
        start = 0
    existing = {os.environ.get(f"GIT_CONFIG_KEY_{index}") for index in range(start)}
    index = start
    for key in _OVERRIDE_KEYS:
        if key in existing:
            continue
        os.environ[f"GIT_CONFIG_KEY_{index}"] = key
        os.environ[f"GIT_CONFIG_VALUE_{index}"] = values[key]
        index += 1
    os.environ["GIT_CONFIG_COUNT"] = str(index)
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    os.environ["GIT_PAGER"] = "cat"
    _INSTALLED = True


def open_git_repository(path: Path, *, search_parent_directories: bool = False) -> Repo:
    """Open a repository for reading after read-only Git overrides are in place."""
    ensure_git_readonly_env()
    return Repo(os.fspath(path), search_parent_directories=search_parent_directories)
