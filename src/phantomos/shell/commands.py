"""Parse interactive input. Unknown text is a question, never a shell command."""

from dataclasses import dataclass

KNOWN_COMMANDS = frozenset(
    {
        "help",
        "status",
        "scan",
        "history",
        "model",
        "clear",
        "exit",
        "quit",
        "explain",
        "personality",
        "repo",
        "memory",
    }
)

HELP_TEXT = """
Commands
  help                      Show this list
  status                    Show repository, Git, Ollama, and model status
  scan                      Inspect the selected repository
  history                   Show commit metadata
  explain RELATIVE_PATH     Explain one file
  model                     Show the configured model and the pull command
  personality LEVEL         Set subtle, normal, cursed, or off
  repo PATH                 Select a repository
  clear                     Clear this conversation
  memory                    Show whether conversations are stored
  exit                      Leave AI Alchemist

Any other line is a question for the local model.
AI Alchemist does not run it as an operating-system command.
""".strip()


@dataclass(frozen=True)
class ShellAction:
    """A parsed shell line."""

    name: str
    argument: str


def parse_shell_line(line: str) -> ShellAction:
    """Split a known command from a natural-language question."""
    stripped = line.strip()
    if not stripped:
        return ShellAction("empty", "")
    head, _, rest = stripped.partition(" ")
    key = head.lower()
    if key in KNOWN_COMMANDS:
        return ShellAction(key, rest.strip())
    return ShellAction("ask", stripped)
