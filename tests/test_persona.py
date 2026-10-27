"""Narration can be turned off without dropping factual fields."""

from ai_alchemist.repository.git_history import CommitInfo
from ai_alchemist.shell.persona import discovery_line, intro_text, narration
from ai_alchemist.workflows import _format_commit

_HORROR = ("haunted", "cursed", "spirit", "sleeping", "ghost")


def _commit() -> CommitInfo:
    return CommitInfo(
        hexsha="abc123def4567890abc123def4567890abc123de",
        short_hash="abc123def456",
        authored_at="2020-01-02T03:04:05+00:00",
        author_name="Ada Lovelace",
        author_email="ada@example.com",
        message="initial catalog\n",
        summary="initial catalog",
        parent_count=0,
    )


def test_off_narration_has_no_horror_flourish():
    intro = intro_text("off").lower()
    for word in _HORROR:
        assert word not in intro
    assert narration("off", "facts") == ""
    assert narration("off", "oldest") == ""
    assert "repository" in intro


def test_commit_facts_survive_every_personality():
    commit = _commit()
    block = _format_commit("Oldest commit", commit)
    for personality in ("off", "subtle", "normal", "cursed"):
        lead = narration(personality, "oldest")
        rendered = f"{lead}\n{block}" if lead else block
        assert commit.hexsha in rendered
        assert commit.authored_at in rendered
        assert "initial catalog" in rendered
        assert "Ada Lovelace" in rendered
        assert "intended" not in rendered.lower()


def test_discovery_line_uses_counted_files_only():
    line = discovery_line("normal", {"Python": 1, "Go": 2})
    assert "2 Go files were discovered" in line
    assert "1 other eligible source file" in line
    assert "Three" not in line
    assert discovery_line("off", {"Python": 3}) == ""
    assert "No eligible source files were discovered." == discovery_line("subtle", {})
    assert "help" in intro_text("off")
    assert "without a model" in intro_text("off")


def test_cursed_lead_does_not_invent_metadata():
    lead = narration("cursed", "oldest")
    assert "abc123" not in lead
    assert "Ada" not in lead
    assert "invent" in lead
