# Contributing to AI Alchemist

AI Alchemist is a read-only local assistant. Patches that keep that boundary are welcome.

## Setup

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

You do not need Ollama to run the tests. A live model is only for your own manual check of `ai-alchemist explain` without `--no-ai`.

## Tests and lint

From the activated environment:

```bash
python -m pytest
python -m ruff check src tests
```

Tests build temporary Git repositories and a fake Ollama client. Do not point them at a personal checkout or put real credentials in fixtures.

On this project's Linux development machine, `python3 -m venv` was unavailable, so the suite was run with a `--prefix` install instead. That layout can make `python -m ruff` miss the `ruff` binary. Inside a normal virtual environment the two commands above are the ones to use.

## Conventions

- Python 3.11 or newer. Type hints on public functions.
- New behavior needs a pytest, including the failure path.
- Repository text stays inside the untrusted prompt block.
- Do not import `subprocess` or call `os.system` from `src/ai_alchemist`. Git access goes through GitPython, with the read-only overrides in `repository/git_safety.py`.
- Do not add a shell tool, a write mode, telemetry, or an automatic model download.
- Facts printed in the terminal come from the filesystem, Git, or a real model response.
- Personality strings must not contain hashes, dates, authors, or counts that the caller did not supply.
- Keep changes small. Match the module that already owns the behavior.

## Suggested first tasks

These are not existing issue numbers.

- Add one file extension to `language_name` and assert the scan count.
- Teach `simple_ignored` one more pattern, with a unit test, and document what it still does not parse.
- Add a credential filename to the secret list and prove the file body never reaches a prompt.

## Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
