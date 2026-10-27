"""Command workflows shared by the CLI and the interactive shell."""

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from git import Git
from rich.console import Console
from rich.table import Table
from rich.text import Text

from ai_alchemist.ai.base import ModelStatus
from ai_alchemist.ai.context import (
    build_explain_prompt,
    build_history_prompt,
    build_inspect_prompt,
    build_question_prompt,
)
from ai_alchemist.ai.ollama_provider import OllamaProvider
from ai_alchemist.config import (
    EXAMPLE_MODEL,
    FALLBACK_MODEL,
    PERSONALITY_LEVELS,
    RECOMMENDED_MODEL,
    AlchemistConfig,
    config_path,
    data_dir,
    ensure_data_dir_writable,
    is_loopback_host,
    load_config,
)
from ai_alchemist.exceptions import AIAlchemistError, ConfigError
from ai_alchemist.repository.code_explainer import excerpt, outline_source
from ai_alchemist.repository.file_filters import read_for_analysis
from ai_alchemist.repository.git_history import CommitInfo, inspect_history
from ai_alchemist.repository.git_safety import ensure_git_readonly_env
from ai_alchemist.repository.scanner import ScanReport, find_git_root, scan_repository
from ai_alchemist.shell.display import (
    render_ai_notice,
    render_commit_table,
    render_excerpt,
    render_facts_header,
    render_key_values,
    render_lines,
    render_model_header,
    render_model_text,
    render_tree,
    render_warning,
    stream_token,
)
from ai_alchemist.shell.persona import discovery_line, narration


@dataclass
class EnvironmentReport:
    """Real checks. Missing services stay missing."""

    python_version: str
    python_ok: bool
    git_ok: bool
    git_detail: str
    data_directory: Path
    data_dir_ok: bool
    data_dir_detail: str
    config_ok: bool
    config_error: str | None
    config: AlchemistConfig | None
    color_disabled: bool
    is_tty: bool
    ollama_detail: str
    ollama_reachable: bool | None
    model_present: bool | None
    available_models: list[str]

    def exit_code(self) -> int:
        """1 when core setup is broken, 2 when Git or the local model is degraded."""
        if not (self.python_ok and self.config_ok and self.data_dir_ok):
            return 1
        ai_ok = self.ollama_reachable is True and self.model_present is True
        if not self.git_ok or not ai_ok:
            return 2
        return 0


def git_binary_status() -> tuple[bool, str]:
    """Check that the git executable exists. Does not modify a repository."""
    location = shutil.which("git")
    if not location:
        return (
            False,
            "git was not found on PATH. Install Git to use history. AI Alchemist will not install it.",
        )
    try:
        ensure_git_readonly_env()
        version = str(Git().version())
    except Exception as exc:
        return False, f"git was found at {location} but could not be executed: {exc}"
    return True, version


def collect_environment(config: AlchemistConfig | None = None) -> EnvironmentReport:
    """Probe Python, Git, configuration, the data directory, and local Ollama."""
    python_ok = sys.version_info >= (3, 11)
    git_ok, git_detail = git_binary_status()
    directory = data_dir()
    data_ok, data_detail = ensure_data_dir_writable(directory)
    config_error: str | None = None
    if config is None:
        try:
            config = load_config()
        except ConfigError as exc:
            config_error = str(exc)
    reachable: bool | None = None
    present: bool | None = None
    models: list[str] = []
    if config is None:
        ollama_detail = "Ollama was not checked because the configuration is invalid."
    else:
        try:
            status = OllamaProvider(config).status()
        except AIAlchemistError as exc:
            reachable = False
            ollama_detail = str(exc)
        else:
            reachable = status.reachable
            present = status.model_present
            models = list(status.available_models)
            ollama_detail = status.detail
    return EnvironmentReport(
        python_version=sys.version.split()[0],
        python_ok=python_ok,
        git_ok=git_ok,
        git_detail=git_detail,
        data_directory=directory,
        data_dir_ok=data_ok,
        data_dir_detail=data_detail,
        config_ok=config_error is None,
        config_error=config_error,
        config=config,
        color_disabled="NO_COLOR" in os.environ,
        is_tty=sys.stdout.isatty(),
        ollama_detail=ollama_detail,
        ollama_reachable=reachable,
        model_present=present,
        available_models=models,
    )


def status_rows(
    *,
    repository: Path | None,
    personality: str,
    persistence: str,
    environment: EnvironmentReport | None,
    ai_checked: bool,
) -> list[tuple[str, str]]:
    """Build status rows from checks the caller already performed."""
    if repository is None:
        repo_value = "(none)"
        git_repo = "No repository selected"
    else:
        repo_value = str(repository)
        root, bare = find_git_root(repository)
        if root is None:
            git_repo = "Not a Git repository"
        elif bare:
            git_repo = f"Bare repository at {root}"
        elif root == repository.resolve():
            git_repo = f"Work tree at {root}"
        else:
            git_repo = f"Inside work tree {root}"
    rows = [
        ("Repository", repo_value),
        ("Git repository", git_repo),
        ("Mode", "Read-only"),
        ("Narration", personality),
        ("Memory", persistence),
    ]
    if environment is None or not ai_checked:
        rows.extend(
            [
                ("Git binary", "Not checked"),
                ("Ollama", "Not checked"),
                ("Model", "Not checked"),
                ("Inference", "Local, not contacted"),
            ]
        )
        return rows
    rows.append(("Git binary", "Available" if environment.git_ok else "Not found"))
    if environment.ollama_reachable is True and environment.model_present is True:
        rows.extend(
            [
                ("Ollama", "Connected"),
                ("Model", f"{environment.config.model if environment.config else ''} (installed)"),
                ("Inference", "Local"),
            ]
        )
    elif environment.ollama_reachable is True and environment.model_present is False:
        model = environment.config.model if environment.config else ""
        rows.extend(
            [
                ("Ollama", "Connected"),
                ("Model", f"{model} (not installed)"),
                ("Inference", "Local, model missing"),
            ]
        )
    elif environment.ollama_reachable is True:
        model = environment.config.model if environment.config else ""
        rows.extend(
            [
                ("Ollama", "Connected"),
                ("Model", f"{model} (availability unknown)"),
                ("Inference", "Local, model not confirmed"),
            ]
        )
    else:
        model = environment.config.model if environment.config else "(configuration invalid)"
        rows.extend(
            [
                ("Ollama", "Unreachable"),
                ("Model", f"{model} (not checked)"),
                ("Inference", "Local, unavailable"),
            ]
        )
    return rows


def _format_commit(label: str, commit: CommitInfo) -> str:
    author = commit.author_name or "not recorded"
    email = commit.author_email or "not recorded"
    return (
        f"{label}\n"
        f"Hash: {commit.hexsha}\n"
        f"Date: {commit.authored_at}\n"
        f"Author recorded on the commit: {author} <{email}>\n"
        f"Message:\n{commit.message.rstrip()}\n"
    )


def choose_inference_model(
    config: AlchemistConfig,
    status: ModelStatus,
) -> tuple[str | None, str | None]:
    """Pick an installed local tag. Return `(model, notice)` or `(None, reason)`.

    The fallback is used only when it is already installed. Nothing is downloaded.
    """
    if not status.reachable:
        return None, status.detail
    if status.model_present is True:
        return config.model, None
    installed = set(status.available_models)
    fallback = config.fallback_model
    if config.use_fallback and fallback != config.model and fallback in installed:
        notice = (
            f"'{config.model}' is not installed. This request will use the fallback "
            f"'{fallback}', which is already installed locally. "
            "AI Alchemist did not download a model."
        )
        return fallback, notice
    return None, status.detail


def _note_model_fallback(console: Console, text: str | None) -> None:
    """Say so when inference did not produce text. Facts already on screen stay facts."""
    if text is None:
        console.print(
            Text(
                "No model response was added. The inspection above is the fallback, "
                "and it is not a generated answer."
            )
        )


def request_model(
    config: AlchemistConfig,
    messages: list,
    console: Console,
) -> str | None:
    """Print a real model response. Return None when inference did not succeed."""
    provider = OllamaProvider(config)
    try:
        status = provider.status()
    except AIAlchemistError as exc:
        render_ai_notice(console, str(exc))
        return None
    chosen, notice = choose_inference_model(config, status)
    if chosen is None:
        render_ai_notice(console, notice or status.detail)
        return None
    if notice:
        render_warning(console, notice)
    stream = bool(config.stream and sys.stdout.isatty())
    started = False
    try:
        if stream:
            render_model_header(console, chosen, config.ollama_host)
            started = True
            generation = provider.generate(
                messages,
                stream=True,
                on_token=lambda token: stream_token(console, token),
                model=chosen,
            )
            console.print()
        else:
            generation = provider.generate(messages, stream=False, model=chosen)
            render_model_header(console, chosen, config.ollama_host)
            render_model_text(console, generation.text)
    except AIAlchemistError as exc:
        if started:
            console.print()
            render_warning(
                console,
                "The model response did not finish. "
                f"{exc} Any partial text above is incomplete.",
            )
        else:
            render_ai_notice(console, str(exc))
        return None
    return generation.text


def run_inspect(
    path: Path,
    *,
    use_ai: bool,
    console: Console,
    config: AlchemistConfig,
) -> int:
    """Scan a directory and optionally ask the local model to summarize it."""
    report = scan_repository(path, config)
    _render_scan(console, report, config.personality)
    if not use_ai:
        console.print(
            Text(
                "AI summary skipped because --no-ai was set. "
                "The facts above came from local inspection."
            )
        )
        return 0
    bundle = build_inspect_prompt(report, config)
    for warning in bundle.warnings:
        render_warning(console, warning)
    if not bundle.files_used:
        render_ai_notice(
            console,
            "No eligible file text was available, so no model request was sent.",
        )
        return 0
    if bundle.truncated:
        render_warning(
            console,
            "Repository context was truncated to the configured character and file limits.",
        )
    render_lines(console, "Files sent to the model", bundle.files_used)
    _note_model_fallback(console, request_model(config, bundle.messages, console))
    return 0


def _render_scan(console: Console, report: ScanReport, personality: str) -> None:
    render_facts_header(console, personality, "facts")
    discovered = discovery_line(personality, report.languages)
    if discovered:
        console.print(Text(discovered))
    git_value = "Not a Git repository"
    if report.bare_repository and report.git_root is not None:
        git_value = f"Bare repository at {report.git_root}"
    elif report.git_root == report.selected_path:
        git_value = str(report.git_root)
    elif report.git_root is not None:
        git_value = f"{report.git_root} (this directory is inside that work tree)"
    render_key_values(
        console,
        "Inspection",
        [
            ("Selected path", str(report.selected_path)),
            ("Git root", git_value),
            ("Files seen", str(report.files_seen)),
            ("Directories seen", str(report.directories_seen)),
            ("Eligible source files", str(report.source_total)),
            (
                "Languages by extension",
                ", ".join(
                    f"{name} {count}"
                    for name, count in sorted(report.languages.items(), key=lambda item: (-item[1], item[0]))
                )
                or "none recorded",
            ),
            ("Excluded directories", str(report.excluded_directories)),
            ("Skipped secrets", str(len(report.skipped_secrets))),
            ("Skipped sensitive content", str(len(report.skipped_sensitive_content))),
            ("Skipped binary files", str(report.skipped_binary)),
            ("Skipped large files", str(report.skipped_large)),
            ("Skipped symbolic links", str(report.skipped_symlinks)),
            ("Skipped ignored files", str(report.skipped_ignored)),
        ],
    )
    if report.metadata:
        render_lines(console, "Project metadata", report.metadata)
    if report.manifests_found:
        render_lines(console, "Dependency manifests", report.manifests_found)
    if report.lockfiles_found:
        render_lines(
            console,
            "Lockfiles found and excluded from model context",
            report.lockfiles_found,
        )
    if report.skipped_secrets or report.skipped_sensitive_content:
        names = report.skipped_secrets + report.skipped_sensitive_content
        render_warning(
            console,
            "Skipped possible secrets or credential material: " + ", ".join(names),
        )
    for warning in report.warnings:
        render_warning(console, warning)
    if report.tree:
        render_tree(console, report.tree)
    for item in report.excerpts:
        if "readme" in Path(item.relative_path).name.lower():
            render_excerpt(console, item.relative_path, item.text)


def run_history(
    path: Path,
    *,
    limit: int | None,
    use_ai: bool,
    console: Console,
    config: AlchemistConfig,
) -> int:
    """Show recorded Git metadata and optionally ask the model to discuss it."""
    report = inspect_history(path, limit=limit or config.history_limit)
    render_facts_header(console, config.personality, "history")
    for note in report.notes:
        console.print(Text(note, style="alchemist.muted"))
    console.print(Text(f"Repository: {report.git_root}"))
    if report.unborn:
        console.print(Text("This repository has no commits yet."))
        return 0
    console.print(
        Text(f"Showing {len(report.commits)} of {report.total_commits} commits on HEAD.")
    )
    if report.oldest is not None:
        lead = narration(config.personality, "oldest")
        if lead:
            console.print(Text(lead))
        console.print(Text(_format_commit("Oldest commit", report.oldest)))
    if report.newest is not None and (
        report.oldest is None or report.newest.hexsha != report.oldest.hexsha
    ):
        lead = narration(config.personality, "newest")
        if lead:
            console.print(Text(lead))
        console.print(Text(_format_commit("Newest commit", report.newest)))
    render_commit_table(
        console,
        [
            (
                commit.hexsha,
                commit.authored_at,
                commit.author_name or "not recorded",
                commit.summary,
            )
            for commit in report.commits
        ],
    )
    if report.branches:
        table = Table(title="Local branches", header_style="alchemist.accent")
        table.add_column("Branch")
        table.add_column("Commit")
        table.add_column("Active")
        table.add_column("Subject")
        for branch in report.branches:
            table.add_row(
                branch.name,
                branch.commit,
                "yes" if branch.is_active else "no",
                branch.summary,
            )
        console.print(table)
    console.print(
        Text(
            "Closer look: keyword and merge heuristic over the listed commits. "
            "This is not a judgment of importance, abandonment, or author intent.",
            style="alchemist.muted",
        )
    )
    if report.interesting:
        for line in report.interesting:
            console.print(Text(line))
    else:
        console.print(Text("No merge commits or keyword matches in the listed subjects."))
    if not use_ai:
        console.print(
            Text("AI history notes skipped because --no-ai was set. The metadata above is from Git.")
        )
        return 0
    if not report.commits:
        render_ai_notice(console, "There are no commits to explain, so no model request was sent.")
        return 0
    bundle = build_history_prompt(report, config)
    _note_model_fallback(console, request_model(config, bundle.messages, console))
    return 0


def run_explain(
    path: Path,
    relative: str,
    *,
    use_ai: bool,
    console: Console,
    config: AlchemistConfig,
) -> int:
    """Explain one file with static analysis and, when available, the local model."""
    from ai_alchemist.security.paths import resolve_directory

    root = resolve_directory(path)
    source = read_for_analysis(root, relative, max_bytes=config.max_file_bytes)
    outline = outline_source(source)
    render_facts_header(console, config.personality, "explain")
    console.print(Text(outline.render()))
    render_excerpt(console, source.relative_path, excerpt(source.text))
    if not use_ai:
        console.print(
            Text(
                "AI explanation skipped because --no-ai was set. "
                "Fallback: the outline and excerpt above are static analysis. "
                "They are not a model response, and the file was not executed."
            )
        )
        return 0
    bundle = build_explain_prompt(source, outline, config)
    render_lines(console, "Files sent to the model", bundle.files_used)
    _note_model_fallback(console, request_model(config, bundle.messages, console))
    return 0


def run_doctor(console: Console) -> int:
    """Report environment checks and actionable next steps. Installs nothing."""
    report = collect_environment()
    table = Table(title="AI Alchemist doctor", header_style="alchemist.accent")
    table.add_column("Check")
    table.add_column("Result")
    table.add_column("Detail")
    python_detail = (
        f"{report.python_version} meets the 3.11 minimum."
        if report.python_ok
        else f"{report.python_version} is older than Python 3.11."
    )
    table.add_row("Python", "PASS" if report.python_ok else "FAIL", python_detail)
    table.add_row("Git", "PASS" if report.git_ok else "FAIL", report.git_detail)
    stored_config = config_path()
    if report.config_ok and stored_config.is_file():
        config_detail = f"Valid configuration file at {stored_config}"
    elif report.config_ok:
        config_detail = f"Built-in defaults are valid. No file at {stored_config}."
    else:
        config_detail = report.config_error or "Invalid configuration"
    table.add_row("Configuration", "PASS" if report.config_ok else "FAIL", config_detail)
    table.add_row(
        "Data directory",
        "PASS" if report.data_dir_ok else "FAIL",
        report.data_dir_detail,
    )
    color = "disabled by NO_COLOR" if report.color_disabled else "available to Rich"
    tty = "interactive terminal" if report.is_tty else "non-interactive stdout"
    table.add_row("Terminal", "INFO", f"{tty}; color {color}.")
    if report.ollama_reachable is True:
        ollama_result = "Connected"
    elif report.ollama_reachable is False:
        ollama_result = "Unreachable"
    else:
        ollama_result = "Unknown"
    table.add_row("Ollama", ollama_result, report.ollama_detail)
    if report.model_present is True:
        model_result = "PASS"
        model_detail = "The configured model is installed locally."
    elif report.model_present is False:
        model_result = "FAIL"
        model_name = report.config.model if report.config else EXAMPLE_MODEL
        model_detail = f"Not installed. AI Alchemist will not download it. Run: ollama pull {model_name}"
    else:
        model_result = "FAIL"
        model_detail = "Model availability was not confirmed."
    table.add_row("Model", model_result, model_detail)
    console.print(table)
    if report.config and not is_loopback_host(report.config.ollama_host):
        render_warning(
            console,
            "ollama_host is not a loopback address. Prompts will be sent to "
            f"{report.config.ollama_host}. The default is local inference.",
        )
    _doctor_advice(console, report)
    code = report.exit_code()
    if code == 0:
        console.print(Text("Doctor: all checks passed.", style="alchemist.ok"))
    elif code == 2:
        console.print(
            Text(
                "Doctor: core inspection can run, but Git or the local model is unavailable.",
                style="alchemist.warn",
            )
        )
    else:
        console.print(Text("Doctor: a required local check failed.", style="alchemist.bad"))
    return code


def _doctor_advice(console: Console, report: EnvironmentReport) -> None:
    advice: list[str] = []
    if not report.python_ok:
        advice.append("Install Python 3.11 or newer. AI Alchemist will not install it for you.")
    if not report.git_ok:
        advice.append(
            "Install Git from https://git-scm.com/downloads if you need history. "
            "File inspection still works without Git."
        )
    if not report.config_ok:
        advice.append(
            f"Fix the JSON configuration at {config_path()} or remove it to return to defaults."
        )
    if not report.data_dir_ok:
        advice.append("Set AI_ALCHEMIST_DATA_DIR to a writable directory, or fix the permissions.")
    if report.ollama_reachable is not True:
        advice.append(
            "AI features need a local Ollama service. Install it from https://ollama.com/download "
            "if you do not already have it, then start it with `ollama serve` when it is not running. "
            "AI Alchemist does not install Ollama or download models."
        )
    if report.config is not None and report.model_present is not True:
        advice.append(
            "Download the configured model yourself with: "
            f"ollama pull {report.config.model}"
        )
        if report.config.use_fallback and report.config.fallback_model != report.config.model:
            if report.config.fallback_model in report.available_models:
                advice.append(
                    f"The fallback '{report.config.fallback_model}' is already installed. "
                    "A later request can use it without changing the configured model. "
                    "AI Alchemist will not download either tag."
                )
            else:
                advice.append(
                    "The smaller fallback, if you want it, is installed with: "
                    f"ollama pull {report.config.fallback_model}"
                )
        advice.append(
            "An 8 GB machine is the design target, not a guarantee. "
            "Fit depends on the operating system, quantization, context size, and whatever else is running. "
            "Read the model card for memory, license, and context length. "
            f"Upstream {RECOMMENDED_MODEL} weights are under the Qwen Research License. "
            f"Upstream {FALLBACK_MODEL} weights are under Apache-2.0. "
            "An Ollama tag can differ from that upstream snapshot."
        )
    if advice:
        render_lines(console, "What you can do", advice)


def run_model(console: Console, config: AlchemistConfig | None = None) -> int:
    """Show model status and the exact pull command. Never runs it."""
    if config is None:
        config = load_config()
    report = collect_environment(config)
    console.print(Text(f"Configured model: {config.model}"))
    console.print(Text(f"Ollama endpoint: {config.ollama_host}"))
    console.print(Text("Provider: local Ollama. No commercial API is configured."))
    if not is_loopback_host(config.ollama_host):
        render_warning(
            console,
            "This endpoint is not loopback. Requests will leave the machine.",
        )
    console.print(Text(report.ollama_detail))
    if report.available_models:
        render_lines(console, "Models installed on this Ollama service", report.available_models)
    else:
        console.print(Text("No local model list is available."))
    console.print(
        Text(
            "AI Alchemist does not assume a context length, GPU, or memory size for this model. "
            "If generation fails, the error from Ollama is shown and no answer is invented. "
            "Performance depends on your hardware and the model you choose."
        )
    )
    fallback_installed = config.fallback_model in report.available_models
    console.print(
        Text(
            f"Recommended model: {RECOMMENDED_MODEL}. "
            f"Configured model: {config.model}. "
            f"Fallback: {config.fallback_model} "
            f"({'installed locally' if fallback_installed else 'not confirmed on this machine'})."
        )
    )
    console.print(
        Text(
            "The design target is a machine with about 8 GB of RAM and no GPU. "
            "That is not a promise the model will run smoothly. "
            "The operating system, quantization, context length, and other running programs all change the result. "
            "If generation fails, including an out-of-memory error, AI Alchemist shows that error "
            "and does not invent an answer."
        )
    )
    console.print(
        Text(
            f"Upstream weights for {RECOMMENDED_MODEL} are published under the Qwen Research License, "
            "which is not Apache-2.0. "
            f"Upstream weights for {FALLBACK_MODEL} are published under Apache-2.0. "
            "An Ollama tag is a packaged build and may differ from those snapshots. "
            "Open-weight does not by itself mean every model is OSI open source. "
            "Read the license file on the exact tag you pull."
        )
    )
    console.print(Text("Select another local model with:"))
    console.print(Text("  ai-alchemist config set model NAME"))
    console.print(Text("  ai-alchemist config set fallback_model NAME"))
    console.print(Text("  ai-alchemist config set max_output_tokens 512"))
    console.print(Text("or set AI_ALCHEMIST_MODEL for one process."))
    console.print(Text("To download a model yourself, run one of:"))
    console.print(Text(f"  ollama pull {config.model}"))
    if config.fallback_model != config.model:
        console.print(Text(f"  ollama pull {config.fallback_model}"))
    console.print(Text("AI Alchemist will not run that command."))
    if report.ollama_reachable is True and report.model_present is True:
        return 0
    return 2


def answer_question(
    question: str,
    report: ScanReport | None,
    history: list,
    *,
    console: Console,
    config: AlchemistConfig,
) -> str | None:
    """Ask the local model about the current repository. Returns model text or None."""
    bundle = build_question_prompt(question, report, history, config)
    for warning in bundle.warnings:
        render_warning(console, warning)
    if bundle.files_used:
        render_lines(console, "Files sent to the model", bundle.files_used)
    elif report is not None:
        console.print(Text("No eligible file text was attached to this question."))
    return request_model(config, bundle.messages, console)


def apply_personality(config: AlchemistConfig, personality: str | None) -> AlchemistConfig:
    """Return config with a validated session personality override."""
    if personality is None:
        return config
    if personality not in PERSONALITY_LEVELS:
        allowed = ", ".join(PERSONALITY_LEVELS)
        raise ConfigError(f"Personality must be one of: {allowed}.")
    return config.model_copy(update={"personality": personality})
