# AI Alchemist: The Ghost Living Inside Your Code

*Draft for the Week 4 submission. The command is `ai-alchemist`. Suggested tags if you publish it: `devchallenge`, `hf26challenge`. This draft does not say the entry has been accepted.*

---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26)*

## What I Built

AI Alchemist is a read-only terminal assistant for opening a repository you have not touched in a long time. The tagline is "Transform Ideas Into Intelligence."

Week 4 asked for something spooky, or something that keeps a story from disappearing, built around open-source AI. I read that as the feeling of `git log` on a project whose author has moved on. The functions are still there. The reason they look the way they do is not. A hosted chat can guess, and it can also take the tree with it.

AI Alchemist splits that job in two.

GhostShell (`ai-alchemist haunt`) is the haunted session: a dry archivist that can be subtle, normal, cursed, or switched off. DeadCode (`inspect`, `history`, `explain`) is the investigator. It counts files, reads manifests, and prints real commit hashes, dates, and authors. The voice never supplies a hash the repository did not already have.

It is not an operating system, and it does not pretend to speak to the dead. If Ollama is down, the facts still print. The program says the model is unavailable. It does not invent a ghost paragraph and call it an answer.

## Demo

There is no hosted URL. AI Alchemist is a local CLI, and inference stays on the machine. This transcript is from Linux, with color turned off, against the sample lamp archive in the repo. Ollama was not contacted.

```text
ai-alchemist inspect examples/sample_repository --no-ai --personality normal
```

```text
Local inspection. Not a model response.
I only read what the repository left behind.
The repository has awakened. 1 Markdown file was discovered. 1 other eligible
source file had a different extension.
Eligible source files       2
Languages by extension      Markdown 1, Python 1
project.name = lamp-archive
```

When two extensions tie, the sentence names the one that sorts first. The table still lists both. The number is a count from the walk, not a line written into the theme.

```text
ai-alchemist explain examples/sample_repository --file src/catalog.py --no-ai --personality subtle
```

```text
Local inspection. Not a model response.
Static reading only. The file was not run.
File: src/catalog.py
Definitions:
  - function average_brightness (line 4)
  - function darkest (line 14)
```

`average_brightness` walks every reading except the last one, then divides by the full length. The outline shows that. The file is not imported and not executed.

With a local model the same command adds a section labeled as a model response, under the facts. Without one:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

ai-alchemist inspect examples/sample_repository --no-ai
ai-alchemist explain examples/sample_repository --file src/catalog.py --no-ai
ai-alchemist history examples/sample_repository --no-ai
ai-alchemist doctor
```

`ai-alchemist doctor` exits 2 when Git or Ollama is missing. It prints the `ollama pull` line and does not run it.

A screen recording was not made for this draft. If you want a moving demo before you publish, record the three commands above in a terminal. Twenty seconds is enough.

## Code

{% github gabutersproject/ai-alchemist %}

[github.com/gabutersproject/ai-alchemist](https://github.com/gabutersproject/ai-alchemist)

The application is MIT. The model weights are not. Upstream Qwen2.5-Coder 3B is under the Qwen Research License. The 1.5B checkpoint is Apache-2.0. An Ollama tag can differ from those snapshots, so the model card on the tag you pull is the one that counts.

## How I Built It

The open piece is local inference through [Ollama](https://ollama.com/). The recommended tag is `qwen2.5-coder:3b`, aimed at a laptop with about 8 GB of RAM and no GPU. The fallback is `qwen2.5-coder:1.5b`, and only if that tag is already installed. AI Alchemist does not download weights, does not send an API key, and does not call a commercial model API. The default host is `http://127.0.0.1:11434`. Point it somewhere else and the tool warns you.

The program is Python 3.11 or newer. Typer parses the commands. Rich draws the terminal. GitPython reads commits and asks `check-ignore`. Pydantic checks the config before it is saved. Nothing in that list is a CUDA package.

The path that matters:

1. The scanner walks the directory you named. It does not follow a symlink or a Windows junction out of that directory. It skips `.git`, virtualenvs, `node_modules`, build outputs, and obvious secret names such as `.env` and private keys. Secret detection is a heuristic. It will miss a novel token format.
2. Python files get an `ast` outline. Other languages get a cautious text pattern, labeled as approximate. Nothing is imported.
3. A small slice of that evidence is wrapped in `<untrusted_repository_data>` and sent to Ollama, one request at a time, with a cap on generated tokens. Repository text cannot close the wrapper by repeating the delimiter. A `tool_calls` reply is rejected. The model has no shell.
4. If the request times out, the JSON is garbage, or the service refuses the connection, you get the error and the facts you already had. There is no canned completion.

`ai-alchemist haunt` is not a system shell. `help`, `scan`, `history`, `explain`, and `exit` are commands. Any other line is a question. `ls` is not executed.

A coding agent in Cursor did a large part of the implementation, with the read-only rules written down first. The tests use a fake Ollama client. They do not need a running model. On the machine where the suite last ran, Ruff was clean and pytest reported 71 passed.

## Why Does Open Innovation Matter?

A forgotten repository is often a private one. The first reading should not require uploading it to a service that can change its price, its retention policy, or its mind.

A closed API could have written a spookier paragraph. It could not have done three things this tool needed:

- Run the inspection when the network, the key, or the vendor is gone. `inspect` and `history --no-ai` never call a model.
- Swap the model by changing one config value. The scanner does not know the tokenizer, the lab, or the context window. A 3B tag and a 1.5B tag are both just local names. The 3B weights are research-licensed, which is a reason to say so in the README instead of hiding behind the word "open."
- Show the policy as ordinary Python. The refusal to follow `..`, the refusal to run `core.fsmonitor` from a hostile `.git/config`, and the refusal to treat a README as a new system prompt are in the repository. You can read the function. You do not have to trust a paragraph in a privacy policy.

Local inference is not a magic circle. A hostile repository can still try to confuse the model. A non-loopback host receives whatever you choose to send. Open weights are not the same thing as an OSI license. What the open path bought here is a first reading that stays on the laptop, and a failure mode that admits the model is missing.

## The Spirit of It

The sample in the repo is a lamp catalog from a workshop that closed. Brightness was stored as plain integers. Nobody wrote down the unit. `average_brightness` drops the last reading and still divides by the full length.

That is the ghost I wanted. Not a jump scare. A small mistake that outlived the person who would have explained it. AI Alchemist can point at line 4. It cannot tell you whether the off-by-one was a rush or a belief about how the mean should work. The commit message is the only intent on record, and even that is just the message.

When the model is silent, the line on screen is still a count from disk: one Markdown file, one Python file, nothing awakened that was not there. The past stays in the repository. The tool does not get to invent the rest.
