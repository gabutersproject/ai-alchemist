"""SQLite connection for conversation rows. The file stays on the local machine."""

import sqlite3
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    """Open the conversation database and create the schema when needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            repo_key TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def erase_all(path: Path) -> int:
    """Delete every stored message. Returns the number of rows removed."""
    if not path.exists():
        return 0
    connection = connect(path)
    try:
        count = int(connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0])
        connection.execute("DELETE FROM messages")
        connection.commit()
        return count
    finally:
        connection.close()
