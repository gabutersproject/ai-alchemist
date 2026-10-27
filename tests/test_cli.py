"""CLI commands, exit codes, NO_COLOR, and the refusal to run a shell."""

import subprocess
from io import StringIO
from pathlib import Path

from rich.console import Console
from typer.testing import CliRunner

from ai_alchemist.ai.base import ModelStatus
from ai_alchemist.cli import app
from ai_alchemist.config import AlchemistConfig
from ai_alchemist.shell.display import THEME, make_console
from ai_alchemist.workflows import run_model
from tests.helpers import commit_file, make_repo

runner = CliRunner()


def _sample(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "README.md").write_text("# Lamp Archive\n\nA leftover catalog.\n", encoding="utf-8")
    (root / "src" / "catalog.py").write_text(
        "def average_brightness(readings):\n"
        "    total = 0\n"
        "    for index in range(len(readings) - 1):\n"
        "        total += readings[index]\n"
        "    return total / len(readings)\n",
        encoding="utf-8",
    )
    (root / ".env").write_text("TOKEN=super-secret-value\n", encoding="utf-8")
    return root


def test_help_and_version():
    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0
    for name in ("haunt", "inspect", "history", "explain", "doctor", "model"):
        assert name in help_result.output
    assert "AI Alchemist" in help_result.output
    assert "Transform Ideas Into Intelligence." in help_result.output
    version = runner.invoke(app, ["--version"])
    assert version.exit_code == 0
    assert "0.1.0" in version.output


def test_inspect_invalid_path_and_plain_directory(tmp_path: Path):
    missing = runner.invoke(app, ["inspect", str(tmp_path / "missing")])
    assert missing.exit_code == 1
    root = _sample(tmp_path)
    result = runner.invoke(app, ["inspect", str(root), "--no-ai"])
    assert result.exit_code == 0, result.output
    assert "Lamp Archive" in result.output
    assert "Not a Git repository" in result.output
    assert "super-secret-value" not in result.output
    assert "Not a model response" in result.output
    assert "AI summary skipped" in result.output


def test_explain_is_static_and_refuses_secrets_and_traversal(tmp_path: Path):
    root = _sample(tmp_path)
    explained = runner.invoke(
        app,
        ["explain", str(root), "--file", "src/catalog.py", "--no-ai"],
    )
    assert explained.exit_code == 0, explained.output
    assert "average_brightness" in explained.output
    assert "was not executed" in explained.output
    secret = runner.invoke(app, ["explain", str(root), "--file", ".env", "--no-ai"])
    assert secret.exit_code == 1
    assert "super-secret-value" not in secret.output
    escaped = runner.invoke(app, ["explain", str(root), "--file", "../outside.txt", "--no-ai"])
    assert escaped.exit_code == 1
    windows = runner.invoke(
        app,
        ["explain", str(root), "--file", "src\\catalog.py", "--no-ai"],
    )
    assert windows.exit_code == 0
    assert "average_brightness" in windows.output


def test_history_on_non_git_and_on_a_real_commit(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    rejected = runner.invoke(app, ["history", str(plain), "--no-ai"])
    assert rejected.exit_code == 1
    root = tmp_path / "repo"
    repo = make_repo(root)
    commit = commit_file(repo, "readme.md", "one\n", "first memory")
    result = runner.invoke(app, ["history", str(root), "--no-ai"])
    assert result.exit_code == 0, result.output
    assert commit.hexsha in result.output
    assert "first memory" in result.output
    assert "Archive Tester" in result.output
    assert "No branches were checked out" in result.output


def test_doctor_reports_unreachable_ollama_without_claiming_success():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 2, result.output
    assert "Unreachable" in result.output
    assert "Connected" not in result.output
    assert "ollama pull" in result.output
    assert "Python" in result.output


def test_model_prints_pull_command_and_does_not_run_it(monkeypatch):
    observed = []
    real_popen = subprocess.Popen

    def spy(*args, **kwargs):
        observed.append(args[0] if args else kwargs.get("args"))
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", spy)
    result = runner.invoke(app, ["model"])
    assert result.exit_code == 2, result.output
    assert "ollama pull qwen2.5-coder:3b" in result.output
    assert "ollama pull qwen2.5-coder:1.5b" in result.output
    assert "Qwen Research License" in result.output
    assert "not a promise" in result.output
    assert "will not run" in result.output
    rendered = " ".join(str(item) for item in observed)
    assert "ollama" not in rendered


def test_haunt_never_executes_natural_language(tmp_path: Path):
    root = _sample(tmp_path)
    marker = tmp_path / "PWNED"
    result = runner.invoke(
        app,
        ["haunt", str(root), "--no-ai", "--personality", "off"],
        input="status\nls -la\nscan\nexit\n",
    )
    assert result.exit_code == 0, result.output
    assert "AI ALCHEMIST" in result.output
    assert "Read-only" in result.output
    assert "was not executed" in result.output
    assert "Lamp Archive" in result.output
    assert "I only read what the repository left behind." not in result.output
    assert not marker.exists()
    assert "super-secret-value" not in result.output


def test_no_color_disables_rich_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    console = make_console()
    assert console.no_color is True
    buffer = StringIO()
    local = Console(
        file=buffer,
        no_color=True,
        force_terminal=True,
        theme=THEME,
        highlight=False,
        width=80,
    )
    local.print("[alchemist.accent]Readable[/]")
    assert "\x1b" not in buffer.getvalue()
    result = runner.invoke(app, ["--help"])
    assert "\x1b" not in (result.stdout or "")


def test_config_and_memory_commands():
    show = runner.invoke(app, ["config", "show"])
    assert show.exit_code == 0
    assert "qwen2.5-coder:3b" in show.output
    assert "qwen2.5-coder:1.5b" in show.output
    updated = runner.invoke(app, ["config", "set", "personality", "off"])
    assert updated.exit_code == 0, updated.output
    shown = runner.invoke(app, ["config", "show"])
    assert "off" in shown.output
    rejected = runner.invoke(app, ["config", "set", "model", "bad;name"])
    assert rejected.exit_code == 1
    memory = runner.invoke(app, ["memory", "path"])
    assert memory.exit_code == 0
    assert "disabled" in memory.output
    cleared = runner.invoke(app, ["memory", "clear"])
    assert cleared.exit_code == 0
    assert "No conversation database" in cleared.output


def test_non_loopback_model_warning_uses_a_stub(monkeypatch):
    class StubProvider:
        def __init__(self, config, opener=None):
            self._config = config

        def status(self):
            return ModelStatus(
                reachable=True,
                endpoint=self._config.ollama_host,
                model=self._config.model,
                model_present=True,
                available_models=["demo:latest"],
                detail="stubbed local check",
            )

    monkeypatch.setattr("ai_alchemist.workflows.OllamaProvider", StubProvider)
    buffer = StringIO()
    console = Console(file=buffer, no_color=True, width=100, highlight=False, theme=THEME)
    code = run_model(
        console,
        AlchemistConfig(model="demo:latest", ollama_host="http://example.com:11434"),
    )
    text = buffer.getvalue()
    assert code == 0
    assert "leave the machine" in text
    assert "ollama pull demo:latest" in text
