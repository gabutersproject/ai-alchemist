"""Conversation memory is optional and does not store obvious secrets."""

from pathlib import Path

from ai_alchemist.storage.conversation_store import ConversationStore
from ai_alchemist.storage.database import erase_all


def test_disabled_store_does_not_create_a_database(tmp_path: Path):
    database = tmp_path / "conversations.sqlite"
    store = ConversationStore(database, enabled=False, repo_key="/repo")
    store.add("user", "hello")
    store.close()
    assert not database.exists()
    assert store.recent()[0].content == "hello"


def test_enabled_store_survives_a_new_session_and_can_be_cleared(tmp_path: Path):
    database = tmp_path / "conversations.sqlite"
    store = ConversationStore(database, enabled=True, repo_key="/repo")
    store.add("user", "hello archive")
    store.add("assistant", "the readme says lamps")
    store.close()

    again = ConversationStore(database, enabled=True, repo_key="/repo")
    assert [item.content for item in again.recent()] == [
        "hello archive",
        "the readme says lamps",
    ]
    other = ConversationStore(database, enabled=True, repo_key="/other")
    assert other.recent() == []
    removed = again.clear()
    assert removed >= 1
    again.close()
    other.close()

    reloaded = ConversationStore(database, enabled=True, repo_key="/repo")
    assert reloaded.recent() == []
    reloaded.close()
    assert erase_all(database) == 0


def test_sensitive_turn_is_not_written(tmp_path: Path):
    database = tmp_path / "conversations.sqlite"
    store = ConversationStore(database, enabled=True, repo_key="/repo")
    message = store.add("user", "-----BEGIN PRIVATE KEY-----\nabc")
    assert message.persisted is False
    store.add("assistant", "it is a \"quoted\" reply")
    store.close()
    again = ConversationStore(database, enabled=True, repo_key="/repo")
    contents = [item.content for item in again.recent()]
    assert contents == ['it is a "quoted" reply']
    assert "PRIVATE KEY" not in "\n".join(contents)
    again.close()
