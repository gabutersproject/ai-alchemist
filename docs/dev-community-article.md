# The ghost in the repository is just a local model

*Draft for DEV Community. This is a project write-up, not a claim that a contest submission has been accepted.*

## The problem

Old repositories are awkward to reopen. The README is short, the last person who understood a function is gone, and pasting the tree into a hosted chat means the code leaves the machine. The goal was a terminal tool that stays useful with the model turned off, and stays honest when the model is not there.

## The inspiration

Hacktoberfest 2026's Week 4 theme has been described as "Ghost in the Machine": something spooky built with open-weight models or open-source AI. PhantomOS takes that literally as a personality, not as a supernatural claim and not as an operating system. The tagline is "The past never leaves the repository."

The assistant is a dry archivist. It can be subtle, normal, cursed, or switched off. The facts do not change when the voice does.

## What it does

PhantomOS is a Python 3.11+ CLI.

- `phantomos inspect` counts files, skips dependency and secret paths, and reads READMEs and manifests.
- `phantomos history` prints real commit hashes, dates, authors, and branch pointers. It does not check anything out.
- `phantomos explain --file` parses Python with `ast` and, for other languages, uses cautious text patterns. It never imports or runs the file.
- `phantomos haunt` is a small command loop. `help`, `scan`, `history`, and `exit` are commands. Everything else is a question. `ls` is not executed.
- `phantomos doctor` and `phantomos model` talk to a local Ollama process. If it is down, they say so. They do not invent an answer and they do not run `ollama pull`.

Repository text is wrapped as untrusted data. A README that says "ignore previous instructions" is evidence, not a new system prompt. The application still will not open a path the operator did not name, and it will not follow a symlink out of the tree.

## Why local open-weight AI matters

Hosted assistants are convenient, and they are also a data path. A private repository should not have to take that path for a first reading. With Ollama, the prompt goes to `127.0.0.1` unless the operator points it somewhere else. The model name is configuration, so it can be replaced. The persona is a prompt plus a few terminal strings, so it can be edited or disabled. The Python is small enough to read.

Open-weight is not a synonym for open-source. The recommended tag is `qwen2.5-coder:3b` because that is a practical coder model for a machine with about 8 GB of RAM. Upstream, that 3B checkpoint is under the Qwen Research License, not Apache-2.0. The fallback tag is `qwen2.5-coder:1.5b`, whose upstream checkpoint is Apache-2.0. PhantomOS uses the fallback only when it is already installed, and it does not download either tag. Anyone pulling a tag still has to read the license that ships with those weights. PhantomOS does not measure RAM and does not pretend the recommendation will feel smooth on every 8 GB laptop.

The useful part is the split: inspection works with no model at all. The model is a commentary layer over evidence the program already collected.

## A working demo

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

phantomos inspect examples/sample_repository --no-ai
phantomos explain examples/sample_repository --file src/catalog.py --no-ai
phantomos doctor
```

`src/catalog.py` in the sample averages brightness by skipping the last reading and still dividing by the full length. With only `--no-ai`, PhantomOS shows the function and says it did not run the file. With Ollama and a pulled model, `phantomos explain` adds a labeled model response underneath that outline.

```bash
ollama pull qwen2.5-coder:3b
phantomos haunt examples/sample_repository
```

Inside the session: `scan`, `explain src/catalog.py`, then a question such as "What does average_brightness do?" `exit` leaves. The repository is unchanged.

## Limitations and lessons

Bounding the prompt is as important as the persona. A 1.5B model will confabulate if you hand it a whole monorepo and ask for certainty. PhantomOS sends a handful of files and tells the model to say when the evidence runs out. That instruction is not a guarantee.

Secret handling has false positives and false negatives. Skipping a file that quotes a private-key header is better than uploading it. Missing a novel token format is still possible.

The horror voice was the easy part. The hard part was refusing to let it speak when the model was down. A canned ghost paragraph would have looked like a feature and would have been a lie. The degraded path prints repository facts and an explicit "AI unavailable" panel.

This draft does not confirm Hacktoberfest eligibility, dates, or submission rules. Check the current official requirements before treating it as an entry.

## License

The application is MIT. Model weights are not covered by that license.
