"""Session memory with optional SQLite persistence.

Persistence is off unless configuration enables it. Sensitive-looking text is
kept in the current process only and is not written to the database.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from phantomos.ai.base import ChatMessage
from phantomos.security.secrets import content_looks_sensitive
from phantomos.storage.database import connect

_MAX_STORED_CHARS = 16_000
_MAX_ROWS = 200


@dataclass(frozen=True)
class StoredMessage:
    """One conversation turn."""

    role: str
    content: str
    created_at: str
    persisted: bool


class ConversationStore:
    """In-memory history, optionally mirrored to SQLite for one repository key."""

    def __init__(self, database: Path | None, *, enabled: bool, repo_key: str = "") -> None:
        self.database = database
        self.enabled = enabled
        self.repo_key = repo_key
        self._memory: list[StoredMessage] = []
        self.skipped_sensitive_writes = 0
        self._connection = None
        if enabled:
            if database is None:
                raise ValueError("Persistence is enabled but no database path was provided.")
            self._connection = connect(database)
            self._memory = self._load()

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def set_repo(self, repo_key: str) -> None:
        """Switch repositories and reload only that repository's stored turns."""
        self.repo_key = repo_key
        self._memory = self._load() if self.enabled else []

    def recent(self, limit: int | None = None) -> list[StoredMessage]:
        if limit is None or limit >= len(self._memory):
            return list(self._memory)
        if limit <= 0:
            return []
        return list(self._memory[-limit:])

    def as_chat(self, limit: int) -> list[ChatMessage]:
        return [
            ChatMessage(role=item.role, content=item.content) for item in self.recent(limit)
        ]

    def add(self, role: str, content: str) -> StoredMessage:
        if role not in {"user", "assistant"}:
            raise ValueError(f"Unsupported conversation role: {role}")
        text = content[:_MAX_STORED_CHARS]
        created = datetime.now(UTC).isoformat(timespec="seconds")
        persist = self.enabled and self._connection is not None
        if persist and content_looks_sensitive(text):
            persist = False
            self.skipped_sensitive_writes += 1
        message = StoredMessage(role=role, content=text, created_at=created, persisted=persist)
        self._memory.append(message)
        if len(self._memory) > _MAX_ROWS:
            self._memory = self._memory[-_MAX_ROWS:]
        if persist and self._connection is not None:
            self._connection.execute(
                """
                INSERT INTO messages (repo_key, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (self.repo_key, role, text, created),
            )
            self._prune_database()
            self._connection.commit()
        return message

    def clear(self) -> int:
        """Drop the in-memory turns and any stored turns for this repository key."""
        removed = len(self._memory)
        self._memory = []
        if self.enabled and self._connection is not None:
            cursor = self._connection.execute(
                "DELETE FROM messages WHERE repo_key = ?",
                (self.repo_key,),
            )
            self._connection.commit()
            return int(cursor.rowcount)
        return removed

    def _load(self) -> list[StoredMessage]:
        if self._connection is None:
            return []
        rows = self._connection.execute(
            """
            SELECT role, content, created_at FROM messages
            WHERE repo_key = ?
            ORDER BY id ASC
            """,
            (self.repo_key,),
        ).fetchall()
        return [
            StoredMessage(
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
                persisted=True,
            )
            for row in rows
        ]

    def _prune_database(self) -> None:
        if self._connection is None:
            return
        self._connection.execute(
            """
            DELETE FROM messages
            WHERE repo_key = ?
              AND id NOT IN (
                SELECT id FROM messages
                WHERE repo_key = ?
                ORDER BY id DESC
                LIMIT ?
              )
            """,
            (self.repo_key, self.repo_key, _MAX_ROWS),
        )
