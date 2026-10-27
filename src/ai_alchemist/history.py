"""Local experiment history.

Rows stay in a SQLite file beside the settings. Nothing in this module opens a
network connection. A configured provider token is refused if it appears in the
prompt or the response.
"""

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


def connect(path: Path) -> sqlite3.Connection:
    """Open the experiment database and create it on first use."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(_SCHEMA)
    connection.commit()
    return connection


def add_experiment(
    path: Path,
    *,
    prompt: str,
    response: str,
    model: str,
    provider: str,
    kind: str,
    group_id: str | None = None,
    secrets: list[str] | None = None,
) -> str | None:
    """Insert one turn. Return None when the text contains a saved secret."""
    for secret in secrets or []:
        if secret and (secret in prompt or secret in response):
            return None
    experiment_id = uuid.uuid4().hex
    title = " ".join(prompt.split())[:80] or "Untitled experiment"
    created_at = datetime.now(UTC).isoformat()

    def write(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT INTO experiments (
                id, group_id, kind, title, prompt, response, model, provider, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                group_id or experiment_id,
                kind,
                title,
                prompt,
                response,
                model,
                provider,
                created_at,
            ),
        )

    _transaction(path, write)
    return experiment_id


def list_experiments(path: Path, *, limit: int = 100) -> list[dict[str, Any]]:
    """Return newest experiments first."""
    if not path.exists():
        return []
    connection = connect(path)
    try:
        rows = connection.execute(
            """
            SELECT id, group_id, kind, title, prompt, response, model, provider, created_at
            FROM experiments
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def delete_experiment(path: Path, experiment_id: str) -> bool:
    """Delete one row. Return False when the id is unknown."""
    if not path.exists():
        return False

    def remove(connection: sqlite3.Connection) -> bool:
        cursor = connection.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
        return cursor.rowcount > 0

    return bool(_transaction(path, remove))


def clear_experiments(path: Path) -> int:
    """Delete every stored experiment."""
    if not path.exists():
        return 0

    def remove_all(connection: sqlite3.Connection) -> int:
        cursor = connection.execute("DELETE FROM experiments")
        return int(cursor.rowcount)

    return int(_transaction(path, remove_all))


def _transaction(path: Path, operation):
    connection = connect(path)
    try:
        result = operation(connection)
        connection.commit()
        return result
    finally:
        connection.close()
