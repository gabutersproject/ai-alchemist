# AI Alchemist

**Turn Open Models Into Intelligent Creations.**

AI Alchemist is a local laboratory for trying open-weight models. You pick a model, send a prompt, compare two models on the same prompt, and optionally keep the exchange on your own machine. The interface talks to [Ollama](https://ollama.com/). It does not ship a proprietary model API, and it does not invent a reply when the provider is down.

This repository used to contain a read-only terminal inspector for Git repositories. That program is no longer the product. Its source remains in Git history. The geometric mark in the interface is the same mark from that earlier version (`docs/assets/mark.svg`).

## Features

- **Playground.** A conversation view that streams tokens from the configured model, with loading, error, and stopped states, a new-conversation control, and copy on a finished reply.
- **Ollama provider.** One adapter isolates the HTTP client. The interface reads provider status, model lists, and replies from that adapter.
- **Model laboratory.** Models are the tags Ollama returns from `/api/tags`, including the family, parameter size, quantization, and size when Ollama sent them. Nothing here adds benchmark scores.
- **Comparison.** The same prompt is sent to two model names. Each side succeeds or fails on its own. The page does not rank the replies.
- **Experiment history.** Optional SQLite storage for the prompt, reply, model, provider, and time. It is off until you turn it on, and it can be deleted.
- **Ghost mode.** A darker laboratory theme with emerald and gold geometry. It is a visual mode, not a different model.
- **Settings.** Host, optional bearer token, default model, comparison model, output cap, and the history switch. The token is not shown again after it is saved.

## Architecture

The browser is a static page. A small FastAPI application serves that page and the JSON API. Provider calls stay on the server.

```
Browser (playground, compare, models, history, settings)
  -> FastAPI routes
       -> provider adapter (Ollama HTTP)
       -> optional SQLite history
       -> lab-config.json
```

| Module | Responsibility |
| --- | --- |
| `src/ai_alchemist/web/` | Interface |
| `src/ai_alchemist/routes.py` | HTTP API |
| `src/ai_alchemist/providers/` | Provider protocol and the Ollama adapter |
| `src/ai_alchemist/history.py` | Local experiment rows |
| `src/ai_alchemist/config.py` | Settings validation and the token file |
| `src/ai_alchemist/cli.py` | `ai-alchemist` process |

A new provider means a new class behind `ChatProvider` and a registration in `providers/registry.py`. The pages already read provider name, execution mode, and model records from the API. This release only registers Ollama.

More detail is in [docs/architecture.md](docs/architecture.md) and [docs/security.md](docs/security.md).

## Supported providers

| Provider | Execution | What this release does |
| --- | --- | --- |
| Ollama | Local when the host is loopback (`127.0.0.1`, `localhost`, or `::1`). Remote when it is any other host. | `GET /api/tags` and `POST /api/chat`. Optional bearer token. Redirects are not followed. Tool calls are not run. |

Hugging Face and other open-weight hosts are not built in. Pointing the host at a non-Ollama URL will fail unless that URL speaks the Ollama HTTP API.

The laboratory does not download weights. `ollama pull` is printed in errors and documentation. The application never runs it.

## Prerequisites

- Python 3.11 or newer
- Ollama, if you want real inference
- A model you have already pulled, if you want a reply

Installing Python packages needs a network or a local cache. Pulling a model needs a network or a cache the first time. After that, a loopback Ollama server can answer without a commercial API. The application is not an offline product: the first install, and any remote host you configure, use the network.

## Installation

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

If `py` is not available, use `python` once Python 3.11 or newer is on `PATH`.

## Provider configuration

1. Install Ollama from <https://ollama.com/download>.
2. Start it with `ollama serve` if it is not already running.
3. Pull a model yourself, for example `ollama pull qwen2.5-coder:1.5b`. Read that model's license before you pull it. AI Alchemist does not choose or download one for you.
4. Open Settings in the app. The default host is `http://127.0.0.1:11434`.
5. Enter the model name as the default model. Enter a second name if you want comparison.
6. Use **Test connection**. A loopback host is labeled local. Any other host is labeled remote, and prompts will leave the machine.

An optional bearer token is for an Ollama-compatible server that requires one. Leave the field blank to keep a saved token. Use **Clear the saved token** to remove it. The browser is not shown the token after a successful save. Do not put the token in the host URL. URLs with a username or password are rejected.

Settings are stored in:

- Linux: `$XDG_DATA_HOME/ai-alchemist/lab-config.json`, or `~/.local/share/ai-alchemist/lab-config.json`
- Windows: `%LOCALAPPDATA%\ai-alchemist\lab-config.json`

Override the directory with `AI_ALCHEMIST_DATA_DIR`, or the file with `AI_ALCHEMIST_CONFIG`. The file mode is owner-read/write when the operating system allows it. An older inspector `config.json` is not read.

## Running the application

```bash
ai-alchemist
```

Then open <http://127.0.0.1:8000>. The process binds to loopback by default.

```bash
ai-alchemist --host 127.0.0.1 --port 8000
```

`python -m ai_alchemist` does the same thing. Binding to `0.0.0.0` or `::` prints a warning: anyone who can reach the port can read history and change settings.

In the playground, enter a model name, write a prompt, and send it. **Stop** aborts the browser request. **New conversation** clears the screen and does not delete saved rows. **Copy** copies a finished reply.

Turn on **Save experiments on this computer** before a send if you want that turn kept. History then lists the row and can delete one row or all rows.

Ghost mode is the control at the bottom of the sidebar. The choice is stored in this browser only.

## Running tests

```bash
python -m pytest
python -m ruff check src tests
```

The tests use a fake provider and `httpx.MockTransport`. They do not need a running Ollama server, and a passing test run is not a live inference check. To verify a real model, start Ollama, pull a tag, and send a prompt in the playground.

## Privacy

- Experiment history is off by default. Turning it on stores prompts and replies in SQLite next to the settings file. That file is not encrypted.
- History is not sent to a telemetry service. There is no analytics call.
- A saved provider token is kept in `lab-config.json` and sent only as an `Authorization` header to the configured host. It is not written into the web page, the JavaScript, or an experiment row. A turn that contains the token text is not saved.
- A loopback host keeps inference on this machine. A remote host receives the prompt.
- Do not paste secrets into prompts. Saved experiments include the prompt text.
- The default bind address is loopback. A process that can reach a non-loopback bind can read history and change the host.

## Troubleshooting

| What you see | What it means |
| --- | --- |
| Provider chip says Unavailable | Ollama is not running, or the host is wrong. Inspection of the page still works. Start `ollama serve` or fix Settings. |
| The model returned an error naming a missing tag | That tag is not installed. Pull it yourself. The app will not download it. |
| Comparison asks for two models | Set two model names. One Ollama server is enough if both tags are installed. |
| A reply never appears and the status is an error | The provider failed. The text is the provider error, not a substitute answer. |
| Stop left a partial sentence | The request was aborted. Partial text is not saved. |
| Settings say the host is remote | The host is not loopback. Prompts leave this machine. |
| Token field is empty after save | That is intentional. The token stays in the settings file. |

## Why open-source AI matters here

The laboratory is only useful if the model can be swapped. Ollama runs open-weight models on a machine you control, and the same HTTP shape can point at another Ollama-compatible server. You are not required to send a prompt to one proprietary API to use the page.

Local inference, when the host really is loopback, keeps the prompt on that machine. Remote inference is labeled as remote so a custom host is not described as local. Model choice is the point of comparison: two tags, one prompt, two replies, and no score invented by this application.

Open weights are not one license. A model card can be Apache-2.0, a research license, or something else, and an Ollama package can add its own terms. Read the card for the tag you pull. Local execution also does not make a hostile model safe. It removes one mandatory data path.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

- Keep provider HTTP code inside `providers/`.
- Do not execute prompts as shell commands, and do not give the model a tool channel.
- Do not replace a provider failure with a canned reply.
- Do not log or return saved tokens.
- Cover new behavior with pytest, including the failure path. Do not require a live model server.
- Run `python -m pytest` and `python -m ruff check src tests`.

## License and attribution

The application is [MIT](LICENSE), copyright 2026 AI Alchemist Contributors.

The mark at `docs/assets/mark.svg` and `src/ai_alchemist/web/mark.svg` was drawn for this repository. [docs/dev-community-article.md](docs/dev-community-article.md) describes the retired repository inspector, not this laboratory.

FastAPI, Starlette, Uvicorn, HTTPX, Pydantic, and their dependencies are installed from PyPI and keep their own licenses. Ollama and any model weights you pull are separate works. The MIT license in this repository does not relicense them.

This release was checked with mocked provider tests. It was not certified against a particular Ollama version beyond the `/api/tags` and `/api/chat` fields the adapter reads.
