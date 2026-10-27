"""Interactive AI Alchemist session. It is not a system shell."""

import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

from phantomos.config import PERSONALITY_LEVELS, PhantomConfig, database_path
from phantomos.exceptions import PhantomOSError
from phantomos.repository.scanner import ScanReport, scan_repository
from phantomos.security.paths import resolve_directory
from phantomos.shell.commands import HELP_TEXT, parse_shell_line
from phantomos.shell.display import (
    render_ai_notice,
    render_error,
    render_logo,
    render_status,
    render_warning,
)
from phantomos.storage.conversation_store import ConversationStore
from phantomos.workflows import (
    answer_question,
    apply_personality,
    collect_environment,
    run_explain,
    run_history,
    run_inspect,
    run_model,
    status_rows,
)


class Session:
    """State for one interactive process."""

    def __init__(
        self,
        *,
        console: Console,
        config: PhantomConfig,
        repository: Path | None,
        use_ai: bool,
    ) -> None:
        self.console = console
        self.config = config
        self.repository = repository
        self.use_ai = use_ai
        self.report: ScanReport | None = None
        key = str(repository) if repository is not None else ""
        self.store = ConversationStore(
            database_path() if config.persist_conversations else None,
            enabled=config.persist_conversations,
            repo_key=key,
        )

    def close(self) -> None:
        self.store.close()

    def persistence_label(self) -> str:
        if self.config.persist_conversations:
            return f"enabled ({database_path()})"
        return "disabled (this session only)"


def _read_lines(console: Console):
    if sys.stdin.isatty():
        while True:
            try:
                yield console.input("[phantom.accent]you[/]> ")
            except (EOFError, KeyboardInterrupt):
                console.print()
                return
    for line in sys.stdin:
        yield line.rstrip("\n")


def _ensure_report(session: Session) -> ScanReport:
    if session.repository is None:
        raise PhantomOSError("No repository is selected. Use: repo PATH")
    if session.report is None or session.report.selected_path != session.repository:
        session.report = scan_repository(session.repository, session.config)
    return session.report


def _show_status(session: Session) -> None:
    environment = collect_environment(session.config) if session.use_ai else None
    rows = status_rows(
        repository=session.repository,
        personality=session.config.personality,
        persistence=session.persistence_label(),
        environment=environment,
        ai_checked=session.use_ai,
    )
    render_status(session.console, rows, personality=session.config.personality)


def _ask(session: Session, question: str) -> None:
    if not session.use_ai:
        render_ai_notice(
            session.console,
            "AI answers are off for this session. "
            f"The text {question!r} was not executed as an operating-system command.",
        )
        return
    if session.repository is None:
        render_ai_notice(
            session.console,
            "No repository is selected, so no model request was sent. "
            "Use `repo PATH` first. The line was not executed as a command.",
        )
        return
    try:
        report = _ensure_report(session)
    except PhantomOSError as exc:
        render_error(session.console, str(exc))
        return
    history = session.store.as_chat(session.config.max_history_messages)
    answer = answer_question(
        question,
        report,
        history,
        console=session.console,
        config=session.config,
    )
    if answer is None:
        return
    before = session.store.skipped_sensitive_writes
    session.store.add("user", question)
    session.store.add("assistant", answer)
    if session.store.skipped_sensitive_writes > before:
        render_warning(
            session.console,
            "A turn looked like credential material and was kept only in this process, "
            "not written to the database.",
        )


def _dispatch(session: Session, name: str, argument: str) -> bool:
    """Run one command. Return False when the session should end."""
    console = session.console
    if name in {"exit", "quit"}:
        console.print(Text("Leaving the archive. The repository was not modified."))
        return False
    if name == "help":
        console.print(Text(HELP_TEXT))
        return True
    if name == "empty":
        return True
    if name == "status":
        _show_status(session)
        return True
    if name == "scan":
        if session.repository is None:
            render_error(console, "No repository is selected. Use: repo PATH")
            return True
        run_inspect(
            session.repository,
            use_ai=session.use_ai,
            console=console,
            config=session.config,
        )
        session.report = scan_repository(session.repository, session.config)
        return True
    if name == "history":
        if session.repository is None:
            render_error(console, "No repository is selected. Use: repo PATH")
            return True
        try:
            run_history(
                session.repository,
                limit=session.config.history_limit,
                use_ai=session.use_ai,
                console=console,
                config=session.config,
            )
        except PhantomOSError as exc:
            render_error(console, str(exc))
        return True
    if name == "explain":
        if session.repository is None:
            render_error(console, "No repository is selected. Use: repo PATH")
            return True
        if not argument:
            render_error(console, "Usage: explain RELATIVE_PATH")
            return True
        try:
            run_explain(
                session.repository,
                argument,
                use_ai=session.use_ai,
                console=console,
                config=session.config,
            )
        except PhantomOSError as exc:
            render_error(console, str(exc))
        return True
    if name == "model":
        if session.use_ai:
            run_model(console, session.config)
        else:
            render_ai_notice(
                console,
                "Model status was not checked because --no-ai was set. "
                f"Configured model name: {session.config.model}.",
            )
        return True
    if name == "clear":
        removed = session.store.clear()
        if session.config.persist_conversations:
            console.print(Text(f"Cleared {removed} stored message(s) for this repository."))
        else:
            console.print(
                Text(
                    f"Cleared {removed} in-memory message(s). "
                    "Persistence is disabled, so nothing was written to disk."
                )
            )
        return True
    if name == "memory":
        console.print(Text(f"Conversation storage: {session.persistence_label()}"))
        console.print(
            Text(
                "Stored turns are separated by repository path. "
                "Use `ai-alchemist memory clear` to delete the database contents."
            )
        )
        return True
    if name == "personality":
        if not argument:
            console.print(Text(f"Narration: {session.config.personality}"))
            console.print(Text("Levels: " + ", ".join(PERSONALITY_LEVELS)))
            return True
        try:
            session.config = apply_personality(session.config, argument.lower())
        except PhantomOSError as exc:
            render_error(console, str(exc))
            return True
        console.print(Text(f"Narration for this session: {session.config.personality}"))
        console.print(Text("Persist it with: ai-alchemist config set personality LEVEL"))
        return True
    if name == "repo":
        if not argument:
            current = session.repository or "(none)"
            console.print(Text(f"Repository: {current}"))
            return True
        try:
            selected = resolve_directory(Path(argument))
        except PhantomOSError as exc:
            render_error(console, str(exc))
            return True
        session.repository = selected
        session.report = None
        session.store.set_repo(str(selected))
        console.print(Text(f"Selected repository: {selected}"))
        console.print(Text("Conversation context now follows this repository only."))
        return True
    if name == "ask":
        _ask(session, argument)
        return True
    render_error(console, f"Unknown action: {name}")
    return True


def run_haunt(
    path: Path | None,
    *,
    use_ai: bool,
    personality: str | None,
    console: Console,
    config: PhantomConfig,
) -> int:
    """Open the interactive session."""
    selected: Path | None = None
    if path is not None:
        selected = resolve_directory(path)
    config = apply_personality(config, personality)
    session = Session(console=console, config=config, repository=selected, use_ai=use_ai)
    try:
        render_logo(console, config.personality)
        if not use_ai:
            console.print(Text("AI requests are disabled for this session (--no-ai)."))
        _show_status(session)
        console.print(
            Text(
                "Offline commands: help, status, scan, history, explain, repo, personality, exit. "
                "They do not need Ollama. Other lines are questions and are not shell commands."
            )
        )
        for line in _read_lines(console):
            action = parse_shell_line(line)
            if not _dispatch(session, action.name, action.argument):
                break
    finally:
        session.close()
    return 0
