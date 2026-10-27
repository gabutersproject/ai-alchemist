"""Rich rendering. Status values are supplied by the caller from real checks."""

import os
import sys

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from phantomos import APP_NAME, SECONDARY_TAGLINE, TAGLINE
from phantomos.shell.persona import intro_text, narration

THEME = Theme(
    {
        "phantom.title": "bold #D4AF37",
        "phantom.accent": "#10B981",
        "phantom.warn": "red",
        "phantom.muted": "dim",
        "phantom.ok": "#10B981",
        "phantom.bad": "red",
    }
)


def make_console() -> Console:
    """Create a console that honors NO_COLOR and avoids markup highlights."""
    no_color = "NO_COLOR" in os.environ
    kwargs: dict[str, object] = {"theme": THEME, "highlight": False}
    if no_color:
        kwargs["no_color"] = True
    if not sys.stdout.isatty():
        kwargs["width"] = 100
    return Console(**kwargs)


def logo_art() -> str:
    """Box drawing for the AI Alchemist banner."""
    width = 54
    rows = [
        "",
        "        \u25cb",
        "       \u2571\u25b3\u2572",
        "",
        f"   {APP_NAME.upper()}",
        "   TRANSFORM IDEAS INTO INTELLIGENCE.",
        "",
        f'   "{SECONDARY_TAGLINE}"',
        f'   "{TAGLINE}"',
        "",
    ]
    top = "\u2554" + ("\u2550" * width) + "\u2557"
    bottom = "\u255a" + ("\u2550" * width) + "\u255d"
    body = ["\u2551" + row.ljust(width) + "\u2551" for row in rows]
    return "\n".join([top, *body, bottom])


def render_logo(console: Console, personality: str) -> None:
    """Print the banner and the session introduction."""
    banner = Text(logo_art(), style="phantom.accent")
    banner.highlight_regex(r"AI ALCHEMIST", style="phantom.title")
    console.print(banner)
    intro = intro_text(personality)
    if personality == "off":
        console.print(Text(intro))
        return
    console.print(Panel(Text(intro), border_style="phantom.accent", box=box.SQUARE))


def render_error(console: Console, message: str) -> None:
    console.print(Panel(Text(message), title="Error", border_style="phantom.warn"))


def render_warning(console: Console, message: str) -> None:
    console.print(Panel(Text(message), title="Warning", border_style="phantom.warn"))


def render_status(console: Console, rows: list[tuple[str, str]], *, personality: str) -> None:
    """Render a status table. The caller is responsible for true values."""
    lead = narration(personality, "facts")
    if lead:
        console.print(Text(lead, style="phantom.muted"))
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column("Field", style="phantom.accent")
    table.add_column("Value")
    for label, value in rows:
        table.add_row(label, value)
    console.print(table)


def render_facts_header(console: Console, personality: str, key: str = "facts") -> None:
    lead = narration(personality, key)
    console.print(Rule("Repository facts", style="phantom.accent"))
    console.print(Text("Local inspection. Not a model response.", style="phantom.muted"))
    if lead:
        console.print(Text(lead))


def render_tree(console: Console, tree: str) -> None:
    console.print(Panel(Text(tree), title="Directory structure", border_style="phantom.accent"))


def render_key_values(console: Console, title: str, rows: list[tuple[str, str]]) -> None:
    table = Table(title=title, box=box.SIMPLE_HEAD, header_style="phantom.accent")
    table.add_column("Item")
    table.add_column("Value")
    for label, value in rows:
        table.add_row(label, value)
    console.print(table)


def render_commit_table(console: Console, rows: list[tuple[str, str, str, str]]) -> None:
    table = Table(title="Commits", box=box.SIMPLE_HEAD, header_style="phantom.accent")
    table.add_column("Hash")
    table.add_column("Date")
    table.add_column("Author")
    table.add_column("Message")
    for row in rows:
        table.add_row(*row)
    console.print(table)


def render_lines(console: Console, title: str, lines: list[str]) -> None:
    if not lines:
        return
    console.print(Rule(title, style="phantom.accent"))
    for line in lines:
        console.print(Text(line))


def render_excerpt(console: Console, relative: str, text: str, *, max_lines: int = 20) -> None:
    rows = text.splitlines()
    shown = rows[:max_lines]
    body = "\n".join(shown)
    if len(rows) > max_lines:
        body += f"\n\u2026 [{len(rows) - max_lines} more lines not shown in the terminal]"
    console.print(
        Panel(
            Text(body),
            title=f"Excerpt: {relative}",
            subtitle="File text, not a model response",
            border_style="phantom.accent",
        )
    )


def render_ai_notice(console: Console, message: str) -> None:
    """An application message. It must not be styled as a successful model answer."""
    console.print(
        Panel(
            Text(message + f"\n{APP_NAME} did not generate a substitute model answer."),
            title="AI unavailable",
            border_style="phantom.warn",
        )
    )


def render_model_header(console: Console, model: str, endpoint: str) -> None:
    console.print(Rule("Model response", style="phantom.accent"))
    console.print(
        Text(
            f"Source: local Ollama model {model} at {endpoint}. This text came from the model.",
            style="phantom.muted",
        )
    )


def render_model_text(console: Console, text: str) -> None:
    """Print model text as literal characters, not Rich markup."""
    console.print(Text(text), overflow="fold")


def stream_token(console: Console, token: str) -> None:
    console.print(Text(token), end="")
