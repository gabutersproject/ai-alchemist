# PhantomOS

**The ghost living inside your code.**

The past never leaves the repository. Some code refuses to rest.

PhantomOS is a read-only terminal assistant for developers who want to look through an old repository without uploading it. It combines two ideas:

- **GhostShell** (`phantomos haunt`) is an interactive session with a dry, eerie archivist.
- **DeadCode** (`inspect`, `history`, `explain`) reads directories, Git metadata, and source files.

It is a developer tool with a horror-themed voice. It is not an operating system, and it does not claim to talk to anything supernatural.

Local inference uses [Ollama](https://ollama.com/). There is no commercial model API. If Ollama is not running, inspection and history still work. PhantomOS will say that the model is unavailable instead of inventing an answer.

## Motivation

Reopening a forgotten repository usually means hunting through a README, a manifest, and `git log`, then guessing. Hosted coding assistants can speed that up, and they also mean the tree leaves your machine. PhantomOS keeps the first reading local, separates recorded facts from model commentary, and stays usable when you decline the model entirely.

## Features

- Interactive shell with `help`, `status`, `scan`, `history`, `explain`, `model`, `personality`, `repo`, `clear`, `memory`, and `exit`.
- Directory inspection: tree, languages by extension, README excerpts, dependency manifests, file counts, and excluded directories.
- Git history: real hashes, dates, messages, recorded authors, oldest and newest commits, and local branches. Nothing is checked out.
- Static explanations of one file, including Python functions, classes, and imports. The file is not executed.
- Optional Ollama summary, labeled as a model response, with the file list that was sent.
- Personality levels: `subtle`, `normal`, `cursed`, and `off`.
- Optional SQLite conversation memory, disabled by default.
- `doctor` and `model` checks that tell you what to install yourself.

An old last-commit date is not treated as proof that a project was abandoned.

## Architecture

```
CLI (Typer, Rich)
  -> workflows
       -> scanner, Git history, static explainer
       -> path and secret checks
       -> bounded prompt builder
       -> Ollama (local HTTP, no tools)
       -> optional SQLite
```

Details live in [docs/architecture.md](docs/architecture.md). The threat model lives in [docs/security.md](docs/security.md).

## Requirements

- Python 3.11 or newer
- Git, only if you want `phantomos history`
- Ollama, only if you want model answers
- A model you have already pulled, only if you want model answers

No GPU or CUDA package is required. The design target is a laptop with about 8 GB of RAM. PhantomOS does not measure RAM or VRAM, and it does not promise that a model will feel fast on every 8 GB machine. The operating system, quantization, context length, and other running programs all matter.

Windows 10/11 and Linux (including Ubuntu and Debian) are the targets. Paths use `pathlib`. The program does not require Bash.

## Install on Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
phantomos --help
```

## Install on Windows

In PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
phantomos --help
```

If `py` is not available, use `python` once Python 3.11+ is on `PATH`.

Installing the Python package downloads dependencies from PyPI unless they are already cached. That step is not offline. Later inference does not contact a model vendor.

## Ollama and a model

PhantomOS will not install Ollama and will not pull weights.

1. Install Ollama from the official download page: <https://ollama.com/download>
2. Start it if it is not already running. The service command is `ollama serve`.
3. Choose a model whose license and size you have actually read. The recommended tag, and the smaller fallback, are:

```bash
ollama pull qwen2.5-coder:3b
ollama pull qwen2.5-coder:1.5b
```

On PowerShell the commands are the same two lines. Pull only what you intend to keep. PhantomOS will not run either command.

4. Check the result:

```bash
phantomos doctor
phantomos model
```

### Recommended model and the 8 GB fallback

The configured default is `qwen2.5-coder:3b`. It is a recommendation, not a statement that the tag is installed or that it will run comfortably in 8 GB.

As of October 2026, the Qwen2.5-Coder model table published by Alibaba lists **Apache-2.0** for the 0.5B, 1.5B, 7B, 14B, and 32B checkpoints, and the **Qwen Research License** for the 3B checkpoint. The recommended tag is open-weight and is not Apache-2.0. The fallback `qwen2.5-coder:1.5b` is the Apache-2.0 checkpoint in that table. Confirm the license file on the exact weights you pull. An Ollama tag is a packaged build; do not assume it is identical to an upstream snapshot, and do not treat "downloadable weights" as a synonym for OSI open source.

If Ollama is up, the configured model is missing, and the fallback tag is already installed, a request uses the fallback and says so. If neither tag is installed, PhantomOS reports that and does not invent an answer. `use_fallback` can be set to `false` when you want a missing model to stay missing. `phantomos model` still exits `2` until the configured model itself is installed.

Generation asks Ollama for at most `max_output_tokens` tokens (default 512). One generation runs at a time in the process. A second request is refused instead of being queued. Context sent to the model is capped by `max_files_in_context`, `max_context_chars`, and `max_file_bytes`. The scan reads files one by one. It does not load the whole tree into the prompt.

`phantomos model` prints the pull commands. It does not run them. If Ollama returns an error, including an out-of-memory error or a timeout, PhantomOS shows that error and does not replace it with a fake completion.

To select another local model:

```bash
phantomos config set model SOME-MODEL:TAG
```

Or, for one process, set `PHANTOMOS_MODEL`.

## Usage

```bash
phantomos doctor
phantomos model
phantomos inspect examples/sample_repository
phantomos explain examples/sample_repository --file src/catalog.py
phantomos history PATH
phantomos haunt PATH
```

Skip the model when you want facts only:

```bash
phantomos inspect examples/sample_repository --no-ai
phantomos explain examples/sample_repository --file src/catalog.py --no-ai --personality off
```

`examples/sample_repository` has no `.git` of its own. `inspect` and `explain` read that folder. `history` uses the Git work tree that contains the path, which is the PhantomOS checkout when you have not copied the sample elsewhere. PhantomOS will not run `git init` for you.

This is a shortened transcript from `phantomos inspect examples/sample_repository --no-ai --personality normal` on Linux, with `NO_COLOR=1`. The absolute path was the machine's checkout. Yours will differ. It is not a screenshot, and it is not a model response.

```text
Local inspection. Not a model response.
I only read what the repository left behind.
The repository has awakened. 1 Markdown file was discovered. 1 other eligible
source file had a different extension.
Eligible source files       2
Languages by extension      Markdown 1, Python 1
project.name = lamp-archive
```

When the counts tie, the sentence names the extension that sorts first. The table still lists every counted language. `explain ... --file src/catalog.py --no-ai` then printed `average_brightness` at line 4 and `darkest` at line 14, and said the file was not executed.

Inside `phantomos haunt`:

```text
you> help
you> status
you> scan
you> history
you> explain src/catalog.py
you> What does average_brightness appear to do?
you> personality off
you> clear
you> exit
```

A line that is not one of those commands is a question. It is not run in a shell. `ls`, `rm`, and anything else a repository file tells you to run stay as text.

Color follows your terminal. Set `NO_COLOR=1` to disable Rich color. The program also runs when stdout is not a terminal, which is what CI needs.

## Configuration

Settings are JSON at the application data directory:

- Linux: `$XDG_DATA_HOME/phantomos/config.json`, or `~/.local/share/phantomos/config.json`
- Windows: `%LOCALAPPDATA%\phantomos\config.json`

Override the directory with `PHANTOMOS_DATA_DIR`, or the file with `PHANTOMOS_CONFIG`.

```bash
phantomos config path
phantomos config show
phantomos config set personality off
phantomos config set persist_conversations true
phantomos config set ollama_host http://127.0.0.1:11434
```

Environment variables override the file when they are set. `phantomos config set` writes the file only. It does not copy other environment overrides into the file. If the variable for the setting you just saved is also set, that variable still wins for the current process:

| Variable | Setting |
| --- | --- |
| `PHANTOMOS_MODEL` | `model` |
| `PHANTOMOS_FALLBACK_MODEL` | `fallback_model` |
| `PHANTOMOS_USE_FALLBACK` | `use_fallback` |
| `PHANTOMOS_MAX_OUTPUT_TOKENS` | `max_output_tokens` |
| `PHANTOMOS_OLLAMA_HOST` | `ollama_host` |
| `PHANTOMOS_PERSONALITY` | `personality` |
| `PHANTOMOS_PERSIST` | `persist_conversations` |
| `PHANTOMOS_CONNECT_TIMEOUT` | `connect_timeout_seconds` |
| `PHANTOMOS_REQUEST_TIMEOUT` | `request_timeout_seconds` |
| `PHANTOMOS_STREAM` | `stream` |

Useful limits: `max_file_bytes` (default 200000), `max_files_in_context` (default 8), `max_context_chars` (default 24000), `max_output_tokens` (default 512), `history_limit` (default 20). Model names must be a single token without spaces or shell metacharacters. `connect_timeout_seconds` bounds the tag check. `request_timeout_seconds` bounds a generation. Both are socket timeouts on the local HTTP call.

The default host is loopback. If you point `ollama_host` at another machine, prompts are sent there. `doctor` and `model` warn when the host is not loopback. The host URL cannot embed a username or password. PhantomOS does not send API keys.

## Privacy

- Source code of this application is in this tree. Read it.
- The inference backend is the Ollama URL in your config. The default is `http://127.0.0.1:11434`.
- Repository analysis runs with no model.
- There is no analytics, telemetry, or background call to a hosted model API.
- Local execution does not remove every risk. A malicious repository can still try to confuse the model. A non-loopback endpoint receives the prompt. Ollama itself keeps a model loaded according to its own `keep_alive` default.
- Model weights and third-party Python packages have their own licenses.
- Conversation storage is off until you enable it. The database path is printed by `phantomos memory path`. Rows are repository path, role, text, and time. Turns that look like credential material are not written. `phantomos memory clear` deletes stored rows.

```bash
phantomos memory path
phantomos memory clear
```

With persistence enabled, a later `phantomos haunt` on the same repository path reloads that repository's stored turns. Other repositories do not share those rows. This was checked with automated tests. The database is not encrypted.

## Security model

PhantomOS will not:

- run arbitrary operating-system commands or commands suggested by the model
- execute, import, or test repository code
- modify source files or Git history
- install repository dependencies
- download models
- give the model a tool-calling interface
- read `.env`, private keys, or the other secret patterns into a prompt
- follow a symbolic link or Windows junction out of the selected directory, or into a secret filename
- let repository Git config choose a filesystem monitor, hook directory, external diff, SSH command, or credential helper
- treat README or source text as instructions

Exit codes for `phantomos doctor`:

| Code | Meaning |
| --- | --- |
| 0 | Python, config, data directory, Git, Ollama, and the model all check out |
| 2 | Core setup works; Git or the local model is unavailable |
| 1 | Python, configuration, or the data directory failed |

`phantomos model` exits `0` when the configured model is installed and `2` when it is not. Other command failures exit `1`. Interrupted sessions exit `130`.

Read [docs/security.md](docs/security.md) before trusting the tool with a repository you did not write.

## Testing

Tests use temporary directories and a fake Ollama client. They do not need a running model, and they do not modify a repository outside the test folder.

```bash
python -m pytest
python -m ruff check src tests
```

## Known limitations

- Only a bounded set of files is sent to the model. Large repositories are sampled, not understood in full.
- Non-Python outlines are pattern matches and can be wrong. The output says so.
- A model can still hallucinate. The facts panel and the model panel are separate for that reason. Prompts tell the model not to invent metadata; that is not a proof that it obeyed.
- Secret detection is a heuristic. Unknown credential formats can slip through. Quoted private-key headers are skipped even in documentation, which will sometimes hide a file you wanted explained.
- Without Git, `.gitignore` support is a small subset and does not honor negation. With Git, `git check-ignore` is used.
- Hard links inside the tree are read like normal files.
- Symlink checks and reads are not atomic. Windows junctions are checked with the same containment rule. That path was exercised with a simulated junction on Linux, not on a Windows machine.
- PhantomOS overrides a short list of Git config keys in its own process so a repository cannot point `core.fsmonitor` or a hook directory at a program. It does not edit the repository's Git config.
- Bare repositories can be read as history. Their object store is not dumped into the model.
- Streaming is used only when stdout is a terminal. Piped output waits for the full reply.
- Performance depends on the model, the quant, and the machine. CPU inference can be slow. That is expected.
- The first install of Python dependencies, Ollama, and weights needs a network or a local cache. Normal inference does not add a second remote API.
- This repository does not certify Hacktoberfest 2026 eligibility. Confirm the official rules, dates, and topic requirements before you submit anything.

## Why Open-Source AI Matters

Open-weight local inference gives developers a practical choice.

- **The code stays put.** A first reading of a private or unreleased repository does not have to be uploaded to a hosted assistant. PhantomOS sends prompts to the configured Ollama process, which is loopback unless you change it.
- **The model is replaceable.** `phantomos config set model` points at any local tag. Nothing in the scanner assumes a context window, a tokenizer, or a vendor SDK.
- **The voice is editable.** Personality text lives in `src/phantomos/shell/persona.py` and `src/phantomos/ai/prompts.py`. `personality off` removes the horror narration and leaves the inspection commands.
- **The program is inspectable.** The read-only rules are ordinary Python in `security/` and `repository/`, not a policy document sitting next to a hidden tool runner.
- **There is no required proprietary API.** PyPI packages and Ollama are the runtime. If the model is missing, `inspect` and `history --no-ai` still report what is on disk.

Downloadable weights are not automatically open source. Apache-2.0 and a research license are different deals, and an Ollama package can add its own terms. Read the model card for the tag you pull. Local execution also does not make a hostile repository or a hostile model safe. It removes one data path. It does not remove the need to read the output.

A longer draft of this argument is in [docs/dev-community-article.md](docs/dev-community-article.md).

## Troubleshooting

| What you see | What it means |
| --- | --- |
| `doctor` exits 2 and Ollama is `Unreachable` | The local service is not running. Inspection with `--no-ai` still works. Start Ollama yourself with `ollama serve`. |
| Model row is `FAIL` | The configured tag is not installed, or its presence could not be checked. PhantomOS does not pull it. |
| A warning names the fallback tag | The configured model is missing and the fallback is already installed. That request uses the fallback. The configured name is unchanged. |
| `Another model request is already running` | This process allows one generation at a time. Wait for it to finish. |
| Path traversal or symbolic-link errors | The path left the selected directory, or a link pointed at a secret filename. |
| `explain` without Ollama | You still get the static outline and an excerpt. That text is labeled as local inspection. |
| Slow replies | CPU inference on an 8 GB machine can be slow. Lower `max_output_tokens` or switch to `qwen2.5-coder:1.5b`. A timeout surfaces as an error, not as a made-up answer. |

## Roadmap

These are the next pieces worth building. They are not implemented here.

- A Windows CI job that runs the suite on a real Windows runner, including a directory junction.
- Optional per-language outlines for more than Python, still without executing the file.
- A way to add secret filename patterns in config without turning detection into a claim of completeness.
- A read-only local index for large trees, still capped, still never uploaded.

## Suggested first tasks

These are suggestions for a future issue tracker. This repository does not pretend those issues already exist.

- Add an extension to the language map and a test that the count changes.
- Extend the simple `.gitignore` matcher with one more pattern and a test.
- Add a secret-filename case that the current heuristic misses, with a test that the body stays out of the prompt.

## Contributing

The longer guide is [CONTRIBUTING.md](CONTRIBUTING.md). The expected standard of conduct is [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

- Keep the default path read-only. Do not add a shell tool, a write mode, or an automatic download behind a flag.
- Repository text stays untrusted. New file types need an exclusion story for secrets and binaries.
- Facts shown in the terminal must come from the filesystem, Git, or a real model response. Do not add a fallback paragraph that pretends to be the model.
- Cover behavior with pytest, including the failure path. Do not require a live Ollama server.
- Run `python -m pytest` and `python -m ruff check src tests` from an activated virtual environment.
- Do not add analytics.

## Hacktoberfest

This project was written for a Week 4 theme described as "Ghost in the Machine — build something spooky with open-weight models or open-source AI." Contest rules, eligibility, and dates change. Verify them on the official Hacktoberfest site before you rely on this repository as a submission. Nothing here confirms that the project has been accepted.

## License

The application is [MIT](LICENSE).

Model weights, Ollama, Git, and the Python dependencies are under their own licenses. The MIT license in this repository does not relicense those works.
