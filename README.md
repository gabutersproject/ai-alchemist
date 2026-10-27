# AI Alchemist

![AI Alchemist mark](docs/assets/mark.svg)

**Transform Ideas Into Intelligence.**

AI Alchemist is a read-only terminal assistant for looking through a repository on your own machine. It prints facts from the files and from Git, and it can add a local [Ollama](https://ollama.com/) summary when you want one. Inspection still works if you skip the model.

It is a developer tool. It is not an operating system, and it does not run commands from the repository or from the model.

```bash
ai-alchemist doctor
ai-alchemist inspect examples/sample_repository --no-ai
ai-alchemist explain examples/sample_repository --file src/catalog.py --no-ai
ai-alchemist haunt examples/sample_repository
```

## Names

| What you type | Name |
| --- | --- |
| Command | `ai-alchemist` |
| Python import | `ai_alchemist` |
| Module | `python -m ai_alchemist` |
| Environment variables | `AI_ALCHEMIST_*` |
| Config directory | `ai-alchemist` |

Python package names cannot contain a hyphen, so the import is `ai_alchemist` and the command is `ai-alchemist`. They are the same program.

## What it does

- `inspect` walks a directory and reports the tree, languages, README excerpts, dependency manifests, and file counts.
- `history` prints real commit hashes, dates, messages, authors, and local branches. It does not check anything out.
- `explain` outlines one file. Python functions, classes, and imports come from the syntax tree. The file is not executed.
- `haunt` opens an interactive session. Known commands are handled by AI Alchemist. Any other line is a question for the local model, not a shell command.
- `doctor` and `model` tell you what is missing. They do not install Ollama or download weights.
- Personality can be `subtle`, `normal`, `cursed`, or `off`. `off` drops the narration and leaves the inspection output.
- Conversation memory is optional SQLite, off by default.

An old last-commit date is not treated as proof that a project was abandoned. A model reply is labeled as a model reply. Counts, hashes, and file lists are labeled as local inspection.

## Requirements

- Python 3.11 or newer
- Git, only if you want history
- Ollama and a model you have already pulled, only if you want model answers

Windows 10/11 and Linux are the targets. No GPU package is required. The design target is a laptop with about 8 GB of RAM. AI Alchemist does not measure RAM, and it does not promise that a given model will feel fast on every 8 GB machine.

## Install

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ai-alchemist --help
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
ai-alchemist --help
```

If `py` is not available, use `python` once Python 3.11 or newer is on `PATH`.

Installing the package downloads dependencies from PyPI unless they are already cached. Later inference does not contact a model vendor.

## Model

AI Alchemist will not install Ollama and will not pull weights.

1. Install Ollama from <https://ollama.com/download>.
2. Start it with `ollama serve` if it is not already running.
3. Pull a model whose license and size you have read:

```bash
ollama pull qwen2.5-coder:3b
ollama pull qwen2.5-coder:1.5b
```

The configured default is `qwen2.5-coder:3b`. As of October 2026, the Qwen2.5-Coder table published by Alibaba lists the 3B checkpoint under the Qwen Research License and the 1.5B checkpoint under Apache-2.0. Confirm the license on the exact weights you pull. An Ollama tag is a packaged build and can differ from an upstream snapshot.

If the configured model is missing and the fallback tag is already installed, a request uses the fallback and says so. If neither tag is installed, AI Alchemist reports that and does not invent an answer. Set `use_fallback` to `false` when a missing model should stay missing.

```bash
ai-alchemist doctor
ai-alchemist model
ai-alchemist config set model SOME-MODEL:TAG
```

For one process, set `AI_ALCHEMIST_MODEL` instead of writing the config file.

Generation asks Ollama for at most `max_output_tokens` tokens (default 512). One generation runs at a time. Context is capped by `max_files_in_context`, `max_context_chars`, and `max_file_bytes`.

## Commands

```bash
ai-alchemist doctor
ai-alchemist model
ai-alchemist inspect PATH
ai-alchemist explain PATH --file RELATIVE_PATH
ai-alchemist history PATH
ai-alchemist haunt PATH
```

Skip the model when you want facts only:

```bash
ai-alchemist inspect examples/sample_repository --no-ai
ai-alchemist explain examples/sample_repository --file src/catalog.py --no-ai --personality off
```

`examples/sample_repository` has no `.git` of its own. `inspect` and `explain` read that folder. `history` uses the Git work tree that contains the path. AI Alchemist will not run `git init` for you.

Inside `ai-alchemist haunt`:

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

`help`, `status`, `scan`, `history`, `explain`, `model`, `personality`, `repo`, `clear`, `memory`, and `exit` are commands. Anything else is a question. `ls` and `rm` are not executed.

Color follows the terminal. Set `NO_COLOR=1` to disable Rich color. Piped output also works, which is what CI needs.

`ai-alchemist doctor` exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Python, config, data directory, Git, Ollama, and the model all check out |
| 2 | Core setup works; Git or the local model is unavailable |
| 1 | Python, configuration, or the data directory failed |

`ai-alchemist model` exits `0` when the configured model is installed and `2` when it is not. Other command failures exit `1`. Interrupted sessions exit `130`.

## Configuration

Settings are JSON in the application data directory:

- Linux: `$XDG_DATA_HOME/ai-alchemist/config.json`, or `~/.local/share/ai-alchemist/config.json`
- Windows: `%LOCALAPPDATA%\ai-alchemist\config.json`

Override the directory with `AI_ALCHEMIST_DATA_DIR`, or the file with `AI_ALCHEMIST_CONFIG`.

```bash
ai-alchemist config path
ai-alchemist config show
ai-alchemist config set personality off
ai-alchemist config set persist_conversations true
ai-alchemist config set ollama_host http://127.0.0.1:11434
```

Environment variables override the file for the current process. `config set` writes the file only. If the matching variable is also set, the variable still wins until you unset it.

| Variable | Setting |
| --- | --- |
| `AI_ALCHEMIST_MODEL` | `model` |
| `AI_ALCHEMIST_FALLBACK_MODEL` | `fallback_model` |
| `AI_ALCHEMIST_USE_FALLBACK` | `use_fallback` |
| `AI_ALCHEMIST_MAX_OUTPUT_TOKENS` | `max_output_tokens` |
| `AI_ALCHEMIST_OLLAMA_HOST` | `ollama_host` |
| `AI_ALCHEMIST_PERSONALITY` | `personality` |
| `AI_ALCHEMIST_PERSIST` | `persist_conversations` |
| `AI_ALCHEMIST_CONNECT_TIMEOUT` | `connect_timeout_seconds` |
| `AI_ALCHEMIST_REQUEST_TIMEOUT` | `request_timeout_seconds` |
| `AI_ALCHEMIST_STREAM` | `stream` |

`AI_ALCHEMIST_DEBUG` turns on debug logging. Prompts and file contents are not written to the log.

Useful limits: `max_file_bytes` (default 200000), `max_files_in_context` (default 8), `max_context_chars` (default 24000), `max_output_tokens` (default 512), `history_limit` (default 20). Model names must be a single token without spaces or shell metacharacters.

The default host is loopback. If you point `ollama_host` at another machine, prompts are sent there, and `doctor` and `model` warn you. The host URL cannot embed a username or password. AI Alchemist does not send API keys.

An older config directory named `phantomos` is not read. Copy `config.json` into the `ai-alchemist` directory if you want to keep those settings.

## Privacy and security

- Analysis runs on the machine. There is no analytics and no hosted model API.
- The default Ollama URL is `http://127.0.0.1:11434`.
- AI Alchemist does not run operating-system commands, execute repository code, modify files, change Git history, install dependencies, or download models.
- The model has no tool-calling interface. A `tool_calls` payload is rejected.
- `.env`, private keys, and other secret-looking paths are not read into a prompt. Text that looks like credential material is not sent.
- Symbolic links and Windows junctions are not followed outside the selected directory.
- Repository Git config cannot choose a filesystem monitor, hook directory, external diff, SSH command, or credential helper for this process.
- README and source text are treated as untrusted evidence, not as instructions.

Conversation storage stays off until you enable it. `ai-alchemist memory path` prints the database path. `ai-alchemist memory clear` deletes stored rows. The database is plaintext SQLite.

Read [docs/security.md](docs/security.md) before you point this tool at a repository you did not write. The module map is in [docs/architecture.md](docs/architecture.md).

## Development

```bash
python -m pytest
python -m ruff check src tests
```

Tests use temporary directories and a fake Ollama client. They do not need a running model.

Personality text lives in `src/ai_alchemist/shell/persona.py` and `src/ai_alchemist/ai/prompts.py`. The read-only rules live in `src/ai_alchemist/security/` and `src/ai_alchemist/repository/`.

The longer guide is [CONTRIBUTING.md](CONTRIBUTING.md). The expected standard of conduct is [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The rename notes are in [CHANGELOG.md](CHANGELOG.md).

## Limits

- Only a bounded set of files is sent to the model. A large repository is sampled, not understood in full.
- Non-Python outlines are pattern matches and can be wrong. The output says so.
- A model can still invent a plausible sentence. The facts panel and the model panel are separate for that reason.
- Secret detection is a heuristic. An unknown credential format can slip through.
- Without Git, `.gitignore` support is a small subset and does not honor negation.
- Symlink checks and reads are not atomic.
- CPU inference can be slow. A timeout is shown as an error, not replaced with a made-up answer.
- The first install of Python dependencies, Ollama, and weights needs a network or a local cache.

## Troubleshooting

| What you see | What it means |
| --- | --- |
| `doctor` exits 2 and Ollama is `Unreachable` | The local service is not running. `--no-ai` inspection still works. Start Ollama yourself with `ollama serve`. |
| Model row is `FAIL` | The configured tag is not installed, or its presence could not be checked. AI Alchemist does not pull it. |
| A warning names the fallback tag | The configured model is missing and the fallback is already installed. That request uses the fallback. |
| `Another model request is already running` | This process allows one generation at a time. |
| Path traversal or symbolic-link errors | The path left the selected directory, or a link pointed at a secret filename. |
| `explain` without Ollama | You still get the static outline and an excerpt, labeled as local inspection. |
| Slow replies | CPU inference can be slow. Lower `max_output_tokens` or switch to `qwen2.5-coder:1.5b`. |

## License

The application is [MIT](LICENSE).

Model weights, Ollama, Git, and the Python dependencies are under their own licenses. The MIT license in this repository does not relicense those works.
