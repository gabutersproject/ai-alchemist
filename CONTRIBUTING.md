# Contributing to AI Alchemist

AI Alchemist is a local laboratory for open-weight models. Patches that keep provider calls isolated, and that refuse to invent replies, are welcome.

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

You do not need Ollama to run the tests. A live model is only for your own check in the browser.

## Tests and lint

```bash
python -m pytest
python -m ruff check src tests
```

Tests inject a fake provider or an `httpx.MockTransport`. Do not point them at a personal Ollama server or put real tokens in fixtures.

## Conventions

- Python 3.11 or newer. Type hints on public functions.
- New provider behavior belongs in `src/ai_alchemist/providers/`.
- Do not import `subprocess` or call `os.system`.
- Do not add a tool channel, telemetry, or an automatic model download.
- Do not return saved tokens to the browser or write them into experiment rows.
- A provider failure stays a failure. Do not add a fallback paragraph that pretends to be the model.
- Cover the failure path with pytest.

## Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
