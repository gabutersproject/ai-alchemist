# AI Alchemist: A Local Reading of What the Repository Left Behind

*Draft for the Week 4 submission. The command is `ai-alchemist`. The Python package is `ai_alchemist`. Suggested tags if you publish it: `devchallenge`, `hf26challenge`. This draft does not say the entry has been accepted, and the repository does not contain a published DEV post or a DevRelay session.*

---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26)*

## What I Built

[AI Alchemist](https://github.com/gabutersproject/ai-alchemist) is a read-only terminal assistant for a repository on your own machine. Version 0.1.0 is marked beta in [`pyproject.toml`](https://github.com/gabutersproject/ai-alchemist/blob/master/pyproject.toml). The tagline in [`src/ai_alchemist/__init__.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/__init__.py) is "Transform Ideas Into Intelligence."

The problem it is built for is a checkout whose files are still there and whose reasons are not. `inspect` counts what the walk actually saw. `history` prints commit hashes, dates, authors, and messages copied from Git. `explain` outlines one file with `ast` or a text pattern and does not import it. `haunt` is an interactive session over those same operations. A local [Ollama](https://ollama.com/) model can add a summary afterward. If the model is skipped or unreachable, the facts still print, and the program does not fill the gap with a canned paragraph.

The intended user is a developer opening a directory they can already read: an old project, a sample, or someone else's tree. It is a local CLI. There is no hosted app in the repository. The HTTP client talks only to the configured Ollama host.

Week 4 asked for something spooky, or something that honors the past, built with an open-weight model or other open-source AI. The reading in this repository is the lamp archive under [`examples/sample_repository`](https://github.com/gabutersproject/ai-alchemist/blob/master/examples/sample_repository/README.md). Brightness was stored as plain integers. [`notes/forgotten.md`](https://github.com/gabutersproject/ai-alchemist/blob/master/examples/sample_repository/notes/forgotten.md) says nobody wrote down the unit. `average_brightness` walks every reading except the last one and still divides by the full length. That behavior is in the sample source. AI Alchemist can point at the function. It does not execute it, and it does not decide whether the off-by-one was a rush or a theory of the mean.

The names in the program are the command and the package. `haunt`, `inspect`, `history`, and `explain` are Typer commands in [`src/ai_alchemist/cli.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/cli.py).

## Demo

![AI Alchemist playground while it is running](assets/demo-playground.png)

![AI Alchemist model list while it is running](assets/demo-models.png)

There is no hosted URL. Inference, when you ask for it, goes to the configured Ollama host. The default is `http://127.0.0.1:11434`. The transcript below is the `--no-ai` path, which does not contact Ollama. It was produced on Linux from this repository with `NO_COLOR=1` and with stdout not attached to a terminal, so Rich used a width of 100. Absolute paths in a real run are the resolved paths on that machine. Column padding depends on the terminal. The sentences and the counts do not.

```bash
ai-alchemist inspect examples/sample_repository --no-ai --personality normal
```

The facts header and the discovery sentence are:

```text
Local inspection. Not a model response.
I only read what the repository left behind.
Counted from the walk. 1 Markdown file was discovered. 1 other eligible source file had a different extension.
```

The inspection table for the sample, as it exists in the repository, reported:

| Item | Value |
| --- | --- |
| Files seen | 6 |
| Directories seen | 3 |
| Eligible source files | 2 |
| Languages by extension | Markdown 1, Python 1 |
| Excluded directories, skipped secrets, sensitive content, binary files, large files, symbolic links, and ignored files | 0 |

The Git root line names the work tree that contains the sample and adds `(this directory is inside that work tree)`, because `examples/sample_repository` has no `.git` of its own. The command also prints:

- `project.name = lamp-archive`
- `project.description = A leftover catalog of lamp brightness readings.`
- a dependency-manifest line, `pyproject.toml`
- a directory tree of `notes/`, `src/`, `.env.example`, `.gitignore`, `pyproject.toml`, and `README.md`
- a README excerpt panel subtitled `File text, not a model response`
- `AI summary skipped because --no-ai was set. The facts above came from local inspection.`

Those six files are why the counts look the way they do. [`src/ai_alchemist/repository/scanner.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/repository/scanner.py) reads README names and dependency manifests as excerpts, then `continue`s before it increments `source_total`. `README.md` and `pyproject.toml` are in that group. The two eligible source files are `notes/forgotten.md` and `src/catalog.py`. `.gitignore` and `.env.example` are seen and not counted as source. `.env.example` is allowed by the secret-name check because the name ends in `.example`; it is still not a source extension, so its body is not put in a prompt.

When the top two extension counts tie, the sentence names the one that sorts first by lowercase label. The sort is `(-count, name.lower())` in [`src/ai_alchemist/shell/persona.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/shell/persona.py). Markdown and Python are both 1, so the sentence says Markdown. The table still lists both. Personality `off` prints no discovery sentence at all.

```bash
ai-alchemist explain examples/sample_repository --file src/catalog.py --no-ai --personality subtle
```

```text
Local inspection. Not a model response.
Static reading only. The file was not run.
File: src/catalog.py
Language guess: python
Analysis: static read only. This file was not executed or tested.
Imports: none recorded by the static reader.
Definitions:
  - function average_brightness (line 4)
  - function darkest (line 14)
```

The same command prints an excerpt panel of the file. [`render_excerpt`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/shell/display.py) keeps 20 lines, and this file is longer, so the panel ends with `… [2 more lines not shown in the terminal]`. The closing line is:

```text
AI explanation skipped because --no-ai was set. Fallback: the outline and excerpt above are static analysis. They are not a model response, and the file was not executed.
```

With a reachable model, [`request_model`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/workflows.py) adds a section whose header says `Model response` and `This text came from the model.` This draft does not include a model paragraph. Ollama was not running during the capture, and inventing one would violate the tool's own rule.

`history` on the sample from a clone of this repository follows the Git work tree that contains the path. It prints `No branches were checked out and no Git state was changed.`, then real hashes, dates, and authors. `--limit` caps the recent table (`iter_commits(..., max_count=limit)`). The oldest commit is found with `git rev-list --max-parents=0`, because reversing a limited log still returns the newest commit. That comment is in [`src/ai_alchemist/repository/git_history.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/repository/git_history.py). A copy of the sample that is not inside any repository exits 1 with:

```text
Not a Git repository: <resolved path>. AI Alchemist did not run git init.
```

Inside `haunt`, known words are commands. Anything else is a question. With `--no-ai`, the question `ls` is not executed. The session prints:

```text
AI answers are off for this session. The text 'ls' was not executed as an operating-system command.
AI Alchemist did not generate a substitute model answer.
```

`ai-alchemist doctor` on the same Linux run exited 2. Git was present. Ollama refused the connection, so the Ollama row was `Unreachable` and the model row was `FAIL` with `Model availability was not confirmed.` The advice included `ollama pull qwen2.5-coder:3b` and did not run it. Python, the configuration check, and the data directory passed. Paths in that table follow `AI_ALCHEMIST_DATA_DIR` or the platform data directory, so they are machine-specific.

There is no screen recording in the repository. The commands above are the demo.

## Code

{% github gabutersproject/ai-alchemist %}

[github.com/gabutersproject/ai-alchemist](https://github.com/gabutersproject/ai-alchemist)

The application is [MIT](https://github.com/gabutersproject/ai-alchemist/blob/master/LICENSE). The model weights are not. [`README.md`](https://github.com/gabutersproject/ai-alchemist/blob/master/README.md) and the `doctor` advice say that, as of October 2026, the upstream Qwen2.5-Coder 3B checkpoint is under the Qwen Research License and the 1.5B checkpoint is Apache-2.0. An Ollama tag can differ from those snapshots. The model card on the tag you pull is the one that counts. The MIT license in this repository does not relicense Ollama, Git, the Python dependencies, or the weights.

The module map in the repository is [`docs/architecture.md`](https://github.com/gabutersproject/ai-alchemist/blob/master/docs/architecture.md). The security notes are [`docs/security.md`](https://github.com/gabutersproject/ai-alchemist/blob/master/docs/security.md).

## How I Built It

### Architecture and workflow

The package is `src/ai_alchemist`. Typer parses the CLI. [`workflows.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/workflows.py) is what both the one-shot commands and the interactive session call. Rich renders panels. The optional model client is Ollama over `urllib.request`. SQLite is used only when conversation persistence is turned on.

```text
Typer CLI (cli.py)
  └─ workflows.py
       ├─ repository scanner, Git history, static explainer
       ├─ path and secret checks
       ├─ prompt builder (untrusted delimiter, size limits)
       ├─ Ollama HTTP provider (no tools, redirects refused)
       ├─ Rich display
       └─ optional SQLite conversation store
```

File inspection works like this. `history` skips the walk and reads Git instead. It joins at the model step when `--no-ai` is not set.

1. [`resolve_directory`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/security/paths.py) resolves the directory you named. [`scan_repository`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/repository/scanner.py) walks it with `followlinks=False`. A symbolic link or Windows junction is skipped during the walk. The walk also skips directory names in `EXCLUDED_DIR_NAMES` in [`file_filters.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/repository/file_filters.py): `.git`, virtualenvs, `node_modules`, build outputs, caches, and the rest of that set. Pointing the scanner at a `.git` directory returns a warning and does not read Git internals.
2. If the directory is inside a work tree, ignore rules come from `git check-ignore`. If it is not, [`simple_ignored`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/repository/file_filters.py) applies a small subset of `.gitignore` and does not honor negation.
3. `explain` is the command that outlines a file. Python files go through `ast` in [`code_explainer.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/repository/code_explainer.py). Other languages get regular expressions for a few `function`, `fn`, `func`, `class`, and `struct` shapes. The outline says those matches are approximate. The file is not imported.
4. If you did not pass `--no-ai`, [`context.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/ai/context.py) wraps a bounded slice of the evidence in `<untrusted_repository_data>`. For `inspect` and a `haunt` question, that slice is file text. For `explain`, it is the outline plus the file. For `history`, it is commit metadata. The system prompt is built only from static strings in [`prompts.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/ai/prompts.py). Repository text cannot close the wrapper by repeating the delimiter: copies of the markers are replaced before the block is closed.
5. [`OllamaProvider`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/ai/ollama_provider.py) sends one `POST /api/chat` at a time, with `options.num_predict` set to `max_output_tokens`. The payload has no `tools` field and no API key. A `tool_calls` reply is rejected. Redirects are refused. A timeout, malformed JSON, an empty answer, or a refused connection becomes an error string. Facts printed before the request stay on screen. If a streamed reply stops midway, the partial text stays too, with a warning that it is incomplete.

`haunt` is not a system shell. [`parse_shell_line`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/shell/commands.py) recognizes a fixed set of words. Any other line is an `ask` action.

### Features and how they are implemented

**`inspect`.** Walks the directory and prints a facts panel, language counts, manifest paths, lockfile paths, the tree, and README excerpts. Lockfile bodies are not read. `pyproject.toml`, `package.json`, `Cargo.toml`, and `go.mod` are parsed into metadata lines with the standard-library `tomllib` and `json` modules. Other names in `MANIFEST_NAMES`, including `requirements.txt`, `Pipfile`, and `pom.xml`, are listed as paths and get no extra metadata lines. The tree is capped by `max_tree_depth` (default 3) and `max_tree_entries` (default 80).

**`history`.** Opens the repository with GitPython after [`ensure_git_readonly_env`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/repository/git_safety.py) has set process-local `GIT_CONFIG_*` overrides for `core.fsmonitor`, `core.hooksPath`, `core.sshCommand`, `core.pager`, `diff.external`, `credential.helper`, and `protocol.ext.allow`. The repository's config file is not rewritten. The module lists commits and local branches. It does not check out, commit, reset, fetch, or push. A keyword pass over the listed subjects looks for `security`, `vuln`, `cve`, `revert`, `breaking`, `hotfix`, and `fix` as substrings, and it notes merge commits (`parent_count > 1`). The terminal says that this is a keyword match, not evidence of intent or of a vulnerability, and that the closer look is not a judgment of abandonment. The inspect prompt, not the history prompt, is what tells the model `Do not classify the project as abandoned.`

**`explain`.** Requires `--file` as a path relative to the directory. `..`, absolute paths, drive paths, UNC paths, and null bytes are rejected in [`normalize_relative_parts`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/security/paths.py). `explain` may read a symlink whose target stays inside the directory, unless that target is a secret filename. The scan does not follow those links.

**`haunt`.** Prints the banner from [`display.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/shell/display.py), then reads lines until `exit` or `quit`. The words the parser accepts are `help`, `status`, `scan`, `history`, `explain`, `model`, `personality`, `repo`, `clear`, `memory`, `exit`, and `quit`. The help text lists `exit` and does not list `quit`; both end the session. `clear` drops this session's in-memory turns. When persistence is on, it also deletes stored rows for the current repository key. `personality` changes the session only, and the shell tells you to run `ai-alchemist config set personality LEVEL` if you want that saved. `repo PATH` switches the directory and the conversation key.

**`doctor` and `model`.** They report Python, Git, the config file, the data directory, the terminal, Ollama (`GET /api/tags`), and whether the configured tag is in that list. They do not install Ollama and do not pull weights. `doctor` exit codes come from `EnvironmentReport.exit_code`:

```python
# src/ai_alchemist/workflows.py
    def exit_code(self) -> int:
        """1 when core setup is broken, 2 when Git or the local model is degraded."""
        if not (self.python_ok and self.config_ok and self.data_dir_ok):
            return 1
        ai_ok = self.ollama_reachable is True and self.model_present is True
        if not self.git_ok or not ai_ok:
            return 2
        return 0
```

So exit 2 also covers a reachable Ollama whose configured model is missing or whose presence could not be checked. `ai-alchemist model` returns 0 only when Ollama is reachable and the configured model is installed. Otherwise it returns 2. `inspect`, `explain`, and `history` still return 0 when the local facts were printed and the model request failed: `request_model` catches `AIAlchemistError`, including `AIUnavailableError`, prints it, and the workflow returns 0. Other errors that reach the CLI, such as a missing path or a non-Git directory passed to `history`, use exit code 1. `KeyboardInterrupt` in the CLI becomes exit 130.

**Personality.** `subtle`, `normal`, `cursed`, or `off`. Narration strings live in `persona.py`. The module docstring says those strings may set a tone and must not introduce hashes, dates, authors, files, or findings. Callers interpolate the evidence. `prompts.py` adds a voice instruction to the system prompt. `off` drops the atmospheric lead and tells the model to skip horror framing. Counts and hashes are still printed by the caller, from the scanner or from Git.

**Configuration.** [`AlchemistConfig`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/config.py) is a Pydantic model. Unknown keys are rejected. Settings are loaded from defaults, then JSON, then environment variables. `config set` writes the file only. If the matching variable is set, the variable still wins for that process.

| Variable | Setting |
| --- | --- |
| `AI_ALCHEMIST_MODEL` | `model` |
| `AI_ALCHEMIST_FALLBACK_MODEL` | `fallback_model` |
| `AI_ALCHEMIST_USE_FALLBACK` | `use_fallback` |
| `AI_ALCHEMIST_OLLAMA_HOST` | `ollama_host` |
| `AI_ALCHEMIST_MAX_OUTPUT_TOKENS` | `max_output_tokens` |
| `AI_ALCHEMIST_PERSONALITY` | `personality` |
| `AI_ALCHEMIST_PERSIST` | `persist_conversations` |
| `AI_ALCHEMIST_CONNECT_TIMEOUT` | `connect_timeout_seconds` |
| `AI_ALCHEMIST_REQUEST_TIMEOUT` | `request_timeout_seconds` |
| `AI_ALCHEMIST_STREAM` | `stream` |

`AI_ALCHEMIST_DATA_DIR` replaces the data directory. `AI_ALCHEMIST_CONFIG` replaces the config file path. `AI_ALCHEMIST_DEBUG` sets the log level to debug. The only logging setup is [`logging_config.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/logging_config.py). No other module emits a log record, so prompts and file contents are not written by the application.

The default host is loopback (`127.0.0.1`, `localhost`, or `::1`). Another host is allowed and produces a warning in `doctor` and `model`, because prompts are sent there. The URL cannot embed a username or password. Model names must be a single token whose characters are letters, digits, and `_ . : @ + / -`, so the printed `ollama pull` line cannot change shell meaning.

Defaults that bound a request: `max_output_tokens` 512, `max_file_bytes` 200000, `max_files_in_context` 8, `max_context_chars` 24000, `max_history_messages` 16, `history_limit` 20, `connect_timeout_seconds` 3, `request_timeout_seconds` 120. Streaming is on by default and is used only when stdout is a TTY.

If the configured model is missing, `use_fallback` is true, and `fallback_model` is already installed, that request uses the fallback and prints a warning. Nothing is downloaded. The configured default is `qwen2.5-coder:3b`. The fallback default is `qwen2.5-coder:1.5b`.

**Memory.** Off by default. When `persist_conversations` is true, [`storage/database.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/storage/database.py) creates a plaintext SQLite file, `conversations.sqlite`, with columns `id`, `repo_key`, `role`, `content`, and `created_at`. Turns that match the credential-content check stay in process memory and are not inserted. The store keeps at most 200 messages for the current repository key, and 16000 characters of each turn. The database prune uses the same 200-row cap. `ai-alchemist memory path` prints the path and whether storage is enabled. `ai-alchemist memory clear` deletes stored rows even if persistence is currently off.

**Color.** Rich color follows the terminal. `NO_COLOR=1` disables it. Piped stdout also works.

### A few implementation points

The discovery sentence is built only from the counts the scanner already computed. The leading count is chosen with `sorted(..., key=lambda item: (-item[1], item[0].lower()))`. Personality `off` returns before this branch, with an empty string.

```python
# src/ai_alchemist/shell/persona.py
    if personality == "subtle":
        line = f"{count} {name} {noun} {verb} found by extension. The files were not executed."
    else:
        line = f"Counted from the walk. {count} {name} {noun} {verb} discovered."
        if personality == "cursed":
            line += " I will not invent the rest."
```

Repository evidence is wrapped in `<untrusted_repository_data>`. Before that, `neutralize` strips any copy of the markers out of the evidence:

```python
# src/ai_alchemist/ai/context.py
def neutralize(text: str) -> str:
    """Remove delimiter strings so repository text cannot close the data block."""
    return text.replace(UNTRUSTED_START, "[removed-delimiter]").replace(
        UNTRUSTED_END, "[removed-delimiter]"
    )
```

A model that asks for a tool does not get one:

```python
# src/ai_alchemist/ai/ollama_provider.py
    if message.get("tool_calls"):
        raise AIResponseError(
            "The model requested a tool call. AI Alchemist has no tools and did not execute anything. "
            + _NO_SUBSTITUTE
        )
```

The sample function the outline names is this one. The range stops before the last reading, and the divisor is `len(readings)`:

```python
# examples/sample_repository/src/catalog.py
def average_brightness(readings: list[int]) -> float:
    """Return the mean of the recorded brightness readings."""
    if not readings:
        return 0.0
    total = 0
    for index in range(len(readings) - 1):
        total += readings[index]
    return total / len(readings)
```

### Technologies

Runtime dependencies in `pyproject.toml` are GitPython, Pydantic, Rich, and Typer. The build backend is Hatchling. The console script is `ai-alchemist = ai_alchemist.cli:app`. Development extras are pytest and Ruff. HTTP is the Python standard library (`urllib.request`), not a third-party client. TOML parsing is `tomllib`. Conversation storage is `sqlite3`. There is no CUDA package and no cloud SDK.

`requires-python` is `>=3.11`. Classifiers list Python 3.11 and 3.12, and operating systems Windows and Linux. `doctor` checks `sys.version_info >= (3, 11)`. The design target written in the README and in the `doctor` advice is a laptop with about 8 GB of RAM and no GPU. The program does not measure RAM, and the same text says that figure is not a promise that a given model will feel fast.

### Install, configure, run, and test

The Linux setup below is the one in the [README](https://github.com/gabutersproject/ai-alchemist/blob/master/README.md) and in [CONTRIBUTING.md](https://github.com/gabutersproject/ai-alchemist/blob/master/CONTRIBUTING.md). It was run for this article on Python 3.12. The editable install succeeded, `ai-alchemist --version` printed `0.1.0`, and `inspect` and `explain` with `--no-ai` exited 0. `history` on a copy of the sample that was not inside a Git repository exited 1.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ai-alchemist --help
```

CONTRIBUTING notes that on one Linux development machine `python3 -m venv` was unavailable, and the suite was run from a `--prefix` install instead. Inside a normal virtual environment, the two commands below are the ones the project documents. On the Python 3.12 environment used for this article, `python -m pytest` reported `71 passed` and `python -m ruff check src tests` reported that all checks passed. The tests use temporary directories and a fake Ollama client. They do not start a model.

```bash
python -m pytest
python -m ruff check src tests
```

Windows PowerShell, as documented in the README and not re-run for this draft:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
ai-alchemist --help
```

If `py` is not available, the README says to use `python` once Python 3.11 or newer is on `PATH`.

Installing the package downloads dependencies from PyPI unless they are already cached. Later inference does not contact a model vendor. AI Alchemist will not install Ollama and will not pull weights. The README's model steps are: install Ollama from <https://ollama.com/download>, start it with `ollama serve` if it is not already running, and pull a tag whose license you have read (`ollama pull qwen2.5-coder:3b`, and optionally `ollama pull qwen2.5-coder:1.5b`).

Useful commands after that:

```bash
ai-alchemist doctor
ai-alchemist model
ai-alchemist inspect PATH
ai-alchemist explain PATH --file RELATIVE_PATH
ai-alchemist history PATH
ai-alchemist haunt PATH
ai-alchemist config show
ai-alchemist config set personality off
ai-alchemist config set persist_conversations true
ai-alchemist memory path
```

`python -m ai_alchemist` runs the same Typer app. Typer also exposes its own `--install-completion` and `--show-completion` flags. They are not an AI Alchemist feature beyond what Typer provides.

Configuration files:

- Linux: `$XDG_DATA_HOME/ai-alchemist/config.json`, or `~/.local/share/ai-alchemist/config.json`
- Windows: `%LOCALAPPDATA%\ai-alchemist\config.json`

[`CHANGELOG.md`](https://github.com/gabutersproject/ai-alchemist/blob/master/CHANGELOG.md) says an older data directory named `phantomos` is not read. Copy `config.json` into the `ai-alchemist` directory if you still have one. The public command, package, environment prefix (`AI_ALCHEMIST_*`), and data directory are all AI Alchemist. The version is still 0.1.0. Command names, including `haunt`, were kept through that rename.

### Decisions that are written down

The read-only boundary is the design, not a default you can flip. [`docs/security.md`](https://github.com/gabutersproject/ai-alchemist/blob/master/docs/security.md) says features that write files or execute commands are out of scope for this version and would need a separate design. CONTRIBUTING tells contributors not to add a shell tool, a write mode, telemetry, or an automatic model download.

Git still has to run for history. The application does not import `subprocess` or call `os.system`. GitPython is the Git boundary, and the `GIT_CONFIG_*` overrides exist because Git can run `core.fsmonitor` during ordinary reads such as `rev-list`. A repository can point that setting at a program. The override lasts for this process.

Local inference is the only provider. [`ai/base.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/ai/base.py) defines an `AIProvider` protocol. The only implementation is `OllamaProvider`. One generation holds a process-wide lock. A second caller gets `Another model request is already running in this process.` There is no queue.

The 8 GB note, the Qwen license note, and the warning for a non-loopback host are printed by the program. They are not inferred from a successful model call.

### What is implemented, and what is not

Implemented in this version:

- Read-only `inspect`, `history`, `explain`, and `haunt`
- Optional local Ollama summaries, with `--no-ai` as the facts-only path
- `doctor`, `model`, `config`, and `memory`
- Four narration levels
- Optional SQLite memory, off by default
- Path containment, secret-filename skips, and a credential-content heuristic
- Tests under [`tests/`](https://github.com/gabutersproject/ai-alchemist/tree/master/tests) that build temporary Git repositories and a fake Ollama client

Partial, or only as strong as the code says:

- Non-Python outlines are pattern matches and can be wrong. The output says so.
- Secret detection is a filename list plus a few content markers (private-key blocks, `aws_secret_access_key`, Slack `xoxb-` / `xoxp-` tokens, GitHub `ghp_` tokens, and an `AKIA` access-key pattern). A novel format can pass. The match itself is not printed.
- Without Git, `.gitignore` support is the subset in `simple_ignored`. Negation is ignored.
- Symlink checks and the later read are not atomic. [`docs/security.md`](https://github.com/gabutersproject/ai-alchemist/blob/master/docs/security.md) says so.
- Junction handling was tested by simulating `os.path.isjunction` on Linux. The security document says it was not executed on Windows.
- A model can still invent a plausible sentence. That text is labeled as a model response. The facts panel is separate. Do not treat the model section as an audit.
- Context is a sample. At most `max_files_in_context` files are attached, and adding stops early once fewer than 200 characters of budget remain. Excerpts already collected are attached first (relative paths that contain `readme`, then the other excerpts). Source files come after that, shallower paths first. A large repository is not sent in full.
- [`test_application_source_has_no_shell_execution`](https://github.com/gabutersproject/ai-alchemist/blob/master/tests/test_security.py) walks `src/ai-alchemist`. The package directory after the rename is `src/ai_alchemist`, so that test currently scans no files. The package source itself contains no `subprocess`, `os.system`, or `shell=True`. The test does not currently prove that.

Not in this version:

- A hosted demo, a web UI, or a recorded video
- Installing Ollama, pulling weights, or calling a commercial model API
- Executing repository code, running shell commands from the model or from `haunt`, writing into the repository, or changing Git history
- A second model provider
- Reading the old `phantomos` config directory
- The "suggested first tasks" in CONTRIBUTING. That file says they are not existing issue numbers. They are ideas, not behavior in the tree.

### Contributing

Patches that keep the read-only boundary are welcome. The guide is [CONTRIBUTING.md](https://github.com/gabutersproject/ai-alchemist/blob/master/CONTRIBUTING.md). The conduct note is [CODE_OF_CONDUCT.md](https://github.com/gabutersproject/ai-alchemist/blob/master/CODE_OF_CONDUCT.md). It does not list a private email. It says to open an issue when the repository has a public issue tracker, or to contact the maintainers through the forge that hosts the code.

The project's own expectations for a change:

- Python 3.11 or newer, with type hints on public functions
- New behavior needs a pytest, including the failure path
- Repository text stays inside the untrusted prompt block
- Facts in the terminal come from the filesystem, Git, or a real model response
- Personality strings must not introduce hashes, dates, authors, or counts

A bug report template lives at [`.github/ISSUE_TEMPLATE/bug_report.md`](https://github.com/gabutersproject/ai-alchemist/blob/master/.github/ISSUE_TEMPLATE/bug_report.md). It asks for the command and the environment, and it asks you not to paste `.env` files, private keys, or source you cannot share. The pull-request template asks for `python -m pytest` and `python -m ruff check src tests`.

Suggested first tasks in CONTRIBUTING, still not implemented as issues:

- Add one file extension to `language_name` and assert the scan count
- Teach `simple_ignored` one more pattern, with a unit test, and document what it still does not parse
- Add a credential filename to the secret list and prove the file body never reaches a prompt

The test-path mismatch described above is a concrete place a small patch can start. It is a gap in the test, visible in `tests/test_security.py`, not a shell that the package grew.

## Why Does Open Innovation Matter?

A forgotten repository is often a private one. The first reading should stay on the machine that already has the files.

The open piece in this project is local inference through Ollama, plus inspection that does not need a model at all. A closed API could have written a spookier paragraph. The properties this tool actually implements are narrower, and they are in the repository:

- `inspect`, `explain`, and `history` with `--no-ai` never call a model. When Python, the configuration, and the data directory are fine and Ollama is down, `doctor` exits 2 and says the service is unreachable. The inspection output is still the walk and, for history, Git.
- The model is a config value, `model`, overridable for one process with `AI_ALCHEMIST_MODEL`. The scanner does not know the tokenizer or the lab. A missing tag is not downloaded. A fallback is used only when that tag is already installed.
- The refusal to follow `..`, the refusal to honor `core.fsmonitor` from a repository `.git/config`, and the refusal to treat a README as a new system prompt are ordinary Python. You can read [`paths.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/security/paths.py), [`git_safety.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/repository/git_safety.py), and [`prompts.py`](https://github.com/gabutersproject/ai-alchemist/blob/master/src/ai_alchemist/ai/prompts.py).

That is not a magic circle. A hostile README can still influence the model's wording. A non-loopback `ollama_host` receives whatever you choose to send. The 3B weights the README recommends are research-licensed, which is a reason to say so instead of hiding behind the word "open." Open weights are not the same thing as an OSI license. What this path buys is a first reading that stays on the laptop, a model name you can change without rewriting the scanner, and a failure mode that admits the model is missing.

The first install of Python dependencies, Ollama, and weights still needs a network or a local cache. Runtime inspection with `--no-ai` does not add another remote service.

## The Spirit of It

The sample in the repo is a lamp catalog from a workshop that closed. `average_brightness` drops the last reading and still divides by the full length. The sample README says that is visible in the source and that AI Alchemist has not executed it.

That is the ghost this project is willing to show. A small mistake that outlived the person who would have explained it. The outline can point at line 4. The commit message, when there is one, is the only intent on record, and the history prompt tells the model to describe that as the message, not as verified intent. The sample directory does not even have its own commits until you create them.

When the model is silent, the line on screen is still a count from the walk. For this sample the sentence says `Counted from the walk` and names one Markdown file, then one other eligible source file. The table is what lists that other file as Python. The past stays in the repository. The tool does not get to invent the rest.

## Prize categories

This project does not use the partner products listed on the Week 4 challenge page, so it is not entered in those categories. The open-source AI piece is a local Ollama server and a model tag you install yourself. There is no Render, Gemma, Tinker, TabPFN, Arduino, DigitalOcean, or other partner SDK in `pyproject.toml`.
