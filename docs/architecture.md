# Architecture

AI Alchemist is a read-only terminal assistant. It is not an operating system. `ai-alchemist haunt` opens the interactive session. `inspect`, `history`, and `explain` are the one-shot inspection commands. Both use the same security boundary and the same optional Ollama provider. The Python package is `src/ai_alchemist`.

```
Typer CLI
  └─ workflows
       ├─ repository scanner / Git history / static explainer
       ├─ path and secret checks
       ├─ prompt builder (untrusted delimiter, size limits)
       ├─ Ollama HTTP provider (local by default, no tools)
       ├─ Rich display
       └─ optional SQLite conversation store
```

## Modules

| Path | Responsibility |
| --- | --- |
| `src/ai_alchemist/cli.py` | Commands and exit codes |
| `src/ai_alchemist/workflows.py` | Shared behavior for the CLI and the shell |
| `src/ai_alchemist/config.py` | Pydantic settings, platform data directory |
| `src/ai_alchemist/security/paths.py` | Traversal, symlink, and Windows junction containment |
| `src/ai_alchemist/security/secrets.py` | Credential filenames and content markers |
| `src/ai_alchemist/repository/scanner.py` | Trees, READMEs, manifests, counts |
| `src/ai_alchemist/repository/git_history.py` | Read-only commits and branches |
| `src/ai_alchemist/repository/git_safety.py` | Git config overrides so a repository cannot name a program |
| `src/ai_alchemist/repository/code_explainer.py` | Static outlines, never execution |
| `src/ai_alchemist/ai/ollama_provider.py` | `GET /api/tags`, `POST /api/chat` |
| `src/ai_alchemist/ai/prompts.py` | Persona instructions, no repository text |
| `src/ai_alchemist/ai/context.py` | Bounded evidence blocks |
| `src/ai_alchemist/shell/` | Logo, panels, command parser, session loop |
| `src/ai_alchemist/storage/` | Optional SQLite memory |

## What is trusted

Trusted inputs are the operator's command-line flags, interactive commands (`help`, `scan`, `exit`, and the other names in `shell/commands.py`), and the configuration file.

Repository files, README text, comments, commit messages, manifest fields, and static outlines are untrusted evidence. They are wrapped in `<untrusted_repository_data>` after any copy of that delimiter has been stripped from the evidence. The system prompt is built only from static strings in `prompts.py`.

Natural-language lines in `ai-alchemist haunt` are questions. They are never passed to a system shell.

## Inference

The only provider is Ollama. The default endpoint is `http://127.0.0.1:11434`. Requests set no API key and no `tools` field. Redirects are refused. If the service is down, the model is missing, or the body is malformed, the command reports that and does not substitute a canned "model" answer.

File inspection, counts, and Git metadata do not require Ollama.

## Persistence

Conversation persistence is off by default. When enabled, SQLite in the `ai-alchemist` application data directory stores role, text, time, and repository path. Turns that match credential markers stay in process memory only. `ai-alchemist memory clear` deletes stored rows even if persistence is currently off.

## Read-only boundary

The Git module uses GitPython to list commits, count revisions, and ask `check-ignore`. It does not checkout, commit, reset, fetch, or push. The scanner does not import project code and does not install dependencies.
