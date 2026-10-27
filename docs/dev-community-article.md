*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26)*

## What I Built

[AI Alchemist](https://github.com/gabutersproject/ai-alchemist) is a local laboratory for open-weight models. The tagline is "Turn Open Models Into Intelligent Creations." Version 0.2.0. The command is `ai-alchemist`. The Python package is `ai_alchemist`.

I built it because trying a local model usually means a terminal, a host URL, and a guess about whether the reply came from the model I thought I selected. I wanted one page where the model name, the provider, and the reply stay visible, and where two models can answer the same prompt without one of them being declared the winner.

The model runs through [Ollama](https://ollama.com/). The browser does not call Ollama itself. A small server on the machine does. The default host is `http://127.0.0.1:11434`. If that address is loopback (`127.0.0.1`, `localhost`, or `::1`), the interface says the inference is local. If I point the host anywhere else, the interface says the inference is remote and that the prompt leaves the machine. I did not want a badge that says "local" when the request is actually going somewhere else.

The laboratory has five pages.

**Playground** is the conversation. I choose a model name, write a prompt, and the reply streams in as tokens. Enter sends. Shift+Enter inserts a line break. **Stop** aborts the browser read. A stopped partial reply stays on screen so I can see where it cut off, but it is not saved. **New conversation** clears the screen and does not delete anything already stored. **Copy** copies a finished reply. A follow-up prompt includes the earlier user and assistant text from that screen. Messages that failed are left out. This release does not add a hidden system prompt. What I see is what is sent.

**Compare** sends one prompt to two model names. Each side succeeds or fails on its own. If one tag is missing, that column shows the error and the other column can still show a reply. The page does not score them and does not say which one is better. A difference is not a ranking.

**Models** lists the tags Ollama returns from `GET /api/tags`. When Ollama includes family, parameter size, quantization, byte size, or a modified time, those fields are shown and labeled as reported by Ollama. I do not add benchmark scores, and I do not invent a download status. If the host cannot be reached, the model count stays unknown. The page does not pretend that zero models are installed when the check itself failed.

**History** is optional. Saving is off until I turn on "Save experiments on this computer." A finished playground or compare turn is then written to a SQLite file on this computer. Each row is the prompt, the reply, the model, the provider, the kind of turn, and the time. I can delete one row or all of them. Nothing in that file is uploaded.

**Settings** holds the Ollama host, an optional bearer token, the default model, the comparison model, and the maximum number of output tokens. **Test connection** checks the form without saving it. A blank token field keeps a token that is already saved. "Clear the saved token" removes it. After a successful save the token is not shown again.

**Ghost mode** sits at the bottom of the sidebar. It is a darker laboratory theme: obsidian background, emerald accents, gold lines. The choice stays in this browser only. It does not change the model, the host, or the settings file.

What the program refuses to do is part of the design. It does not download model weights. It does not run `ollama pull`. It does not execute a prompt as a shell command. It does not give the model a tool channel. It does not follow an HTTP redirect from the Ollama host. It does not replace a connection error, a missing model, or an empty body with a paragraph I wrote in advance.

## Demo

There is no hosted URL. The laboratory is a process on the machine that will run the model.

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
ollama serve
ollama pull qwen2.5-coder:1.5b
ai-alchemist
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
ollama serve
ollama pull qwen2.5-coder:1.5b
ai-alchemist
```

`ollama pull` is something I run myself, after I have read the license on that tag. AI Alchemist will not run it. `qwen2.5-coder:1.5b` is only an example of a small tag. Any tag Ollama can serve is a valid model name, as long as it is a single token.

Then I open <http://127.0.0.1:8000>. The server binds to loopback. `python -m ai_alchemist` starts the same process. `ai-alchemist --version` prints `0.2.0` and does not start the server.

In Settings I leave the host at `http://127.0.0.1:11434` unless Ollama is somewhere else. I put the tag I pulled in **Default model**, choose **Test connection**, then **Save**. The sidebar chip should read that Ollama is local and should show how many models the host reported. If Ollama is not running, the chip reads `Ollama · Unavailable` and a prompt returns that error. The page still opens.

These photographs were taken in the browser while the laboratory was running at `127.0.0.1:8000` and connected to an Ollama-compatible host.

![AI Alchemist playground while it is running](assets/demo-playground.png)

The first photograph is the playground after a reply. The sidebar shows the name, the tagline "Turn Open Models Into Intelligent Creations," and the pages. The header shows the active model and that inference is local. The user prompt is on the right. The model reply is on the left, with **Copy**. The prompt box, **Send**, **Stop**, **New conversation**, and the save checkbox are at the bottom. Ghost mode is the green control in the sidebar. The chip says Ollama is local and that two models were reported.

![AI Alchemist model list while it is running](assets/demo-models.png)

The second photograph is the model page. Both cards came from the host's tag list. Each card says "Local host" and "Listed by Ollama," and the description line starts with "Reported by Ollama," including family, parameter size, and quantization. One card is marked Default and the other Comparison. There is no score and no rank.

A second model, if I want Compare, is another tag I have already pulled. I type both names and send one prompt. The two columns fill independently. I do not get a winner.

## Code

The source is [github.com/gabutersproject/ai-alchemist](https://github.com/gabutersproject/ai-alchemist). The application is [MIT](https://github.com/gabutersproject/ai-alchemist/blob/master/LICENSE). Ollama, the model weights, and the Python dependencies keep their own licenses.

The layout is one process, not a set of services.

| Path | What it does |
| --- | --- |
| `src/ai_alchemist/web/` | Playground, Compare, Models, History, Settings, and Ghost mode |
| `src/ai_alchemist/routes.py` | The JSON API and the token stream |
| `src/ai_alchemist/providers/ollama.py` | `GET /api/tags` and `POST /api/chat` |
| `src/ai_alchemist/providers/registry.py` | The single place a provider is constructed |
| `src/ai_alchemist/config.py` | Host, token, model names, and the history switch |
| `src/ai_alchemist/history.py` | SQLite rows |
| `src/ai_alchemist/cli.py` | The `ai-alchemist` process |

The routes the page uses:

| Route | Role |
| --- | --- |
| `GET /api/health` | Process health only. It does not claim a model is running. |
| `GET /api/provider` | Whether the saved host answered, and whether that host is local or remote |
| `GET /api/models` | Tags from that host |
| `GET` and `PUT /api/settings` | Public settings. The token value is never included. |
| `POST /api/settings/test` | Probe the form without saving it |
| `POST /api/chat/stream` | Playground tokens as server-sent events |
| `POST /api/compare` | One prompt, two model names |
| `GET /api/history` | Stored rows |
| `DELETE /api/history/{id}` and `DELETE /api/history` | Delete one row, or every row |

Settings live in `lab-config.json` under the platform data directory: `$XDG_DATA_HOME/ai-alchemist/` or `~/.local/share/ai-alchemist/` on Linux, and `%LOCALAPPDATA%\ai-alchemist\` on Windows. `AI_ALCHEMIST_DATA_DIR` and `AI_ALCHEMIST_CONFIG` override those paths. The file mode is owner read/write when the operating system allows it.

## How I Built It

I split the work so the page does not know the HTTP shape of Ollama. The browser is static HTML, CSS, and JavaScript. FastAPI serves that page and the API. The Ollama client lives in one adapter. Routes ask that adapter to list models or stream a chat. Adding another provider later means a new class behind the same three operations: probe, list, and stream. This release only registers Ollama.

A playground send is `POST /api/chat` with `"stream": true`. The body is the model name, the messages on screen, and Ollama's `num_predict`, taken from `max_output_tokens` (default 512, allowed range 16 to 4096). There is no `tools` field. The server reads the newline-delimited JSON from Ollama and forwards each text fragment to the browser as a server-sent event. **Stop** aborts that read. Closing the stream does not invent the rest of the sentence.

Compare does not stream. It runs both generations with `asyncio.gather` and returns both results, including a failure on only one side. I did that so a missing tag on the right does not hide a real reply on the left, and so the response has no winner field and no score.

The model list is a parse of `/api/tags`, not a catalog I maintain. A tag is "available" only because its name was in that JSON. The description string is built from `details.family`, `details.parameter_size`, and `details.quantization_level` when those keys exist. If they do not, the card says Ollama listed the model and did not include a description. The size line is the `size` integer converted to megabytes or gigabytes and labeled "reported by Ollama."

Failure is explicit. A connection error, a timeout, a redirect, an HTTP error, a tool-call payload, or an empty answer becomes an error message that ends with "AI Alchemist did not invent a replacement answer." A 404 names the missing tag and prints the `ollama pull` line for me to run myself. A redirect is not followed, so a configured host cannot bounce the prompt to another URL without the request failing. If a provider error echoes the saved bearer token, that string is replaced with `[redacted]` before it reaches the page.

The token itself never goes back to the browser. `GET /api/settings` returns `token_configured: true` or `false`. The value stays in `lab-config.json` and is sent only as `Authorization: Bearer` to the configured host. A host URL that embeds a username or password is rejected. The token belongs in the token field. A turn whose prompt or reply contains that token is not written to SQLite.

History is two gates, not one. The setting `persist_experiments` must be on, and the request must ask to save. The checkbox in the playground and the checkbox in Settings write the same flag. New conversation and Stop do not delete rows. Delete does.

Ghost mode is a class on the document element, remembered in `localStorage` under `ai-alchemist-ghost`. The palette is obsidian `#0B0D10`, emerald `#10B981`, gold `#D4AF37`, and soft white `#F5F7FA`. Motion is a slow drift on the mark, and it is disabled when the browser asks for reduced motion. The text stays light on the dark background.

Tests do not start Ollama. They use a fake provider for the API and `httpx.MockTransport` for the adapter: a successful stream, a dead host, a missing model, a tool call, a redirect that must be requested only once, a token that must not reappear in an error, and history that must not be written until saving is enabled. `python -m pytest` and `python -m ruff check src tests` are the checks. A green test run is not a live generation. The live check is still Ollama, a tag I pulled, and a prompt in the playground.

An earlier revision of this repository was a read-only terminal inspector for Git trees. That program is not what this post describes. It is not in the current tree. Git history still has it. The laboratory does not read that old `config.json`.

## Why Does Open Innovation Matter?

The laboratory is only useful if I can change the model. Ollama is how that change stays practical. I pull a tag whose license I have actually read, I type that name, and the same page talks to it. I am not required to send the prompt to one hosted API, and I am not required to rewrite the interface when I switch from a 1.5B tag to another tag on the same server.

Local inference is a real boundary only when the host address is loopback. That is why the chip and the model cards say "Local" or "Remote" from the host, not from a marketing string. A remote Ollama-compatible server is allowed. It is labeled remote, and the prompt is sent there. Open infrastructure includes that choice. It does not include hiding it.

Open weights are not one license. Apache-2.0 and a research license are different deals, and an Ollama package can add its own terms. Downloadable weights are not automatically open source. The MIT license on this repository does not relicense Ollama or the weights. I read the model card for the tag I pull. The software can stay replaceable even when the weight license is narrow. Saying that out loud is part of using open models honestly.

A local process also does not make a hostile model safe. It removes one mandatory data path. The prompt still goes to whatever host I configured, and the reply is still the model's reply. The page keeps those two facts separate: the chip tells me where the request went, and the answer is labeled as that model's text.

## The Spirit of It

Week 4 asked for a ghost in the machine. I did not want a jump scare, and I did not want a horror skin on a chat box that still calls a vendor when the local service is gone.

The ghost is the model that is actually resident on the computer. Ghost mode is the room it answers from: a dark laboratory, a gold mark, a little motion, and text I can still read. The silence matters as much as the theme. If Ollama is unreachable, the chip says unavailable and the prompt returns the connection error. There is no second voice that fills the pause and pretends the machine spoke.

That is the whole of the spirit I was willing to build. A model can be present. When it is not present, the page should admit it.

## Prize: Best Use of Ollama

I am submitting AI Alchemist for the best use of Ollama. This section is the category I am writing for. It is not a claim that the prize has been awarded.

Ollama is the inference engine, not a sentence in the introduction. Every reply the playground shows comes from `POST /api/chat` on the configured host. Every card on the model page comes from `GET /api/tags`. Compare is two of those chat calls, so two tags I have already installed can answer one prompt. The default host is Ollama's own loopback port. A missing tag produces the `ollama pull` command and does not download the weights. A host that is not loopback is called remote. A host that does not answer is called unavailable, and the page does not invent the rest.

That is the use I wanted from Ollama: run an open-weight model on the machine, see the tag I actually selected, and keep a second tag beside it when I want to look at both answers. The laboratory is the room around that use. Ollama is the machine inside the room.
