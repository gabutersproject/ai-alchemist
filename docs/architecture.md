# Architecture

AI Alchemist is a single-process laboratory. The browser does not call Ollama directly. FastAPI holds the settings file and the provider client.

```
Browser
  -> routes.py
       -> providers/registry.py
            -> providers/ollama.py
       -> history.py
       -> config.py
```

## Modules

| Path | Responsibility |
| --- | --- |
| `src/ai_alchemist/web/` | Playground, comparison, model list, history, settings, ghost mode |
| `src/ai_alchemist/routes.py` | JSON and server-sent events |
| `src/ai_alchemist/providers/base.py` | `ChatProvider`, model records, probe results |
| `src/ai_alchemist/providers/ollama.py` | Ollama `/api/tags` and `/api/chat` |
| `src/ai_alchemist/providers/registry.py` | The provider constructed for a request |
| `src/ai_alchemist/config.py` | Host, token, model names, history switch |
| `src/ai_alchemist/history.py` | SQLite experiments |
| `src/ai_alchemist/cli.py` | Loopback server by default |

`ChatProvider` is the boundary the routes use. Adding a provider means implementing `probe`, `list_models`, and `stream_chat`, then returning that class from `build_provider`. The pages do not import Ollama.

## Requests

`POST /api/chat` and `POST /api/chat/stream` send the messages the page shows. No hidden system prompt is added. `POST /api/compare` runs the same user prompt against two model names with `asyncio.gather`, so one failure does not erase the other side.

A turn is stored only when settings have `persist_experiments` and the request sets `save`. The stored prompt is the latest user message, not a hidden transcript.

## What is trusted

Trusted inputs are the operator's settings and the buttons in the page. Model text is untrusted output and is inserted with `textContent` in the browser. Prompts are sent to the configured host and are not passed to a shell.

## Earlier program

Git history contains a read-only repository inspector that used Typer, Rich, and GitPython. That code is not in this tree. The laboratory does not inspect repositories.
