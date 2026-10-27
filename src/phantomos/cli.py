"""AI Alchemist command-line interface."""

from pathlib import Path
from typing import Annotated

import typer

from phantomos import APP_NAME, TAGLINE, __version__
from phantomos.config import (
    PhantomConfig,
    config_path,
    database_path,
    load_config,
    overriding_env_var,
    update_config,
)
from phantomos.exceptions import PhantomOSError
from phantomos.logging_config import configure_logging
from phantomos.shell.display import make_console, render_error, render_key_values, render_warning
from phantomos.shell.interactive import run_haunt
from phantomos.storage.database import erase_all
from phantomos.workflows import (
    apply_personality,
    run_doctor,
    run_explain,
    run_history,
    run_inspect,
    run_model,
)

app = typer.Typer(
    name="ai-alchemist",
    no_args_is_help=True,
    rich_markup_mode=None,
    help=f"{APP_NAME} — {TAGLINE} Read-only local assistant.",
)
config_app = typer.Typer(
    no_args_is_help=True,
    rich_markup_mode=None,
    help="View or update local configuration.",
)
memory_app = typer.Typer(
    no_args_is_help=True,
    rich_markup_mode=None,
    help="Manage optional conversation storage.",
)
app.add_typer(config_app, name="config")
app.add_typer(memory_app, name="memory")


def _version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version, is_eager=True, help="Show the version and exit."),
    ] = False,
) -> None:
    """AI Alchemist — Transform Ideas Into Intelligence."""
    configure_logging()


def _invoke(func) -> None:
    console = make_console()
    try:
        code = func(console)
    except PhantomOSError as exc:
        render_error(console, str(exc))
        raise typer.Exit(code=exc.exit_code) from exc
    except KeyboardInterrupt:
        raise typer.Exit(code=130) from None
    if code:
        raise typer.Exit(code=code)


def _settings(personality: str | None) -> PhantomConfig:
    return apply_personality(load_config(), personality)


@app.command()
def haunt(
    path: Annotated[
        Path | None,
        typer.Argument(help="Repository or directory to investigate."),
    ] = None,
    no_ai: Annotated[bool, typer.Option("--no-ai", help="Do not contact Ollama.")] = False,
    personality: Annotated[
        str | None,
        typer.Option("--personality", help="subtle, normal, cursed, or off."),
    ] = None,
) -> None:
    """Open the interactive AI Alchemist shell. It does not replace your system shell."""

    def action(console):
        return run_haunt(
            path,
            use_ai=not no_ai,
            personality=personality,
            console=console,
            config=load_config(),
        )

    _invoke(action)


@app.command()
def inspect(
    path: Annotated[Path, typer.Argument(help="Directory to inspect.")],
    no_ai: Annotated[bool, typer.Option("--no-ai", help="Skip the local model.")] = False,
    personality: Annotated[
        str | None,
        typer.Option("--personality", help="subtle, normal, cursed, or off."),
    ] = None,
) -> None:
    """Inspect a directory without modifying it. Statistics do not require a model."""

    def action(console):
        return run_inspect(
            path,
            use_ai=not no_ai,
            console=console,
            config=_settings(personality),
        )

    _invoke(action)


@app.command()
def history(
    path: Annotated[Path, typer.Argument(help="Directory inside a Git repository.")],
    limit: Annotated[
        int | None,
        typer.Option("--limit", min=1, max=200, help="Recent commits to list."),
    ] = None,
    no_ai: Annotated[bool, typer.Option("--no-ai", help="Skip the local model.")] = False,
    personality: Annotated[
        str | None,
        typer.Option("--personality", help="subtle, normal, cursed, or off."),
    ] = None,
) -> None:
    """Show recorded commits and branches without changing Git state."""

    def action(console):
        return run_history(
            path,
            limit=limit,
            use_ai=not no_ai,
            console=console,
            config=_settings(personality),
        )

    _invoke(action)


@app.command()
def explain(
    path: Annotated[Path, typer.Argument(help="Directory that contains the file.")],
    file: Annotated[str, typer.Option("--file", help="Path relative to the directory.")],
    no_ai: Annotated[bool, typer.Option("--no-ai", help="Skip the local model.")] = False,
    personality: Annotated[
        str | None,
        typer.Option("--personality", help="subtle, normal, cursed, or off."),
    ] = None,
) -> None:
    """Explain one source file. The file is read, not executed."""

    def action(console):
        return run_explain(
            path,
            file,
            use_ai=not no_ai,
            console=console,
            config=_settings(personality),
        )

    _invoke(action)


@app.command()
def doctor() -> None:
    """Check Python, Git, configuration, and local Ollama. Installs nothing."""
    _invoke(lambda console: run_doctor(console))


@app.command()
def model() -> None:
    """Show the configured model and the command to download it yourself."""
    _invoke(lambda console: run_model(console))


@config_app.command("show")
def config_show() -> None:
    """Print the effective configuration."""
    console = make_console()
    try:
        config = load_config()
    except PhantomOSError as exc:
        render_error(console, str(exc))
        raise typer.Exit(code=exc.exit_code) from exc
    rows = [(name, str(value)) for name, value in config.model_dump(mode="json").items()]
    render_key_values(console, f"Configuration ({config_path()})", rows)
    console.print(
        "Environment variables override the file when they are set. "
        "AI Alchemist does not send this configuration to a remote analytics service."
    )


@config_app.command("path")
def config_path_cmd() -> None:
    """Print the configuration file path."""
    typer.echo(str(config_path()))


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Setting name.")],
    value: Annotated[str, typer.Argument(help="New value.")],
) -> None:
    """Validate and save one setting."""
    console = make_console()
    try:
        updated = update_config(key, value)
    except PhantomOSError as exc:
        render_error(console, str(exc))
        raise typer.Exit(code=exc.exit_code) from exc
    saved = updated.model_dump(mode="json")[key]
    console.print(f"Saved {key}={saved} to {config_path()}")
    override = overriding_env_var(key)
    if override:
        render_warning(
            console,
            f"{override} is set, so it still overrides {key} for this process. "
            "The file was updated, but the environment value is the one in effect.",
        )


@memory_app.command("path")
def memory_path() -> None:
    """Show where conversations would be stored and whether storage is enabled."""
    console = make_console()
    try:
        config = load_config()
    except PhantomOSError as exc:
        render_error(console, str(exc))
        raise typer.Exit(code=exc.exit_code) from exc
    path = database_path()
    state = "enabled" if config.persist_conversations else "disabled"
    console.print(f"Conversation storage is {state}.")
    console.print(f"Database path: {path}")
    console.print(
        "The database is local SQLite and is created only when persistence is enabled. "
        "AI Alchemist remains usable with persistence off."
    )


@memory_app.command("clear")
def memory_clear() -> None:
    """Delete stored conversation rows, if a database exists."""
    console = make_console()
    path = database_path()
    removed = erase_all(path)
    if removed == 0 and not path.exists():
        console.print(f"No conversation database was present at {path}.")
        return
    console.print(f"Removed {removed} stored message(s) from {path}.")
