# Security model

PhantomOS is read-only by design. The controls below are in application code. Prompt text is an extra constraint on the model, not the boundary.

## Enforced behavior

- No arbitrary shell execution. The package does not import `subprocess` or call `os.system`.
- No execution of repository source, scripts, or instructions found in files.
- No Git commands that change HEAD, the index, remotes, or history.
- Repository Git config cannot choose a program. PhantomOS overrides `core.fsmonitor`, `core.hooksPath`, `core.sshCommand`, `core.pager`, `diff.external`, `credential.helper`, and `protocol.ext.allow` for its own Git subprocesses. The repository config file is not rewritten.
- No writes to the repository under inspection.
- No automatic dependency installation.
- No automatic model download. `phantomos model` prints `ollama pull <name>` and does not run it.
- No tool list is sent to Ollama. A `tool_calls` payload is rejected and not executed.
- No telemetry or third-party model API. The HTTP client talks only to the configured Ollama URL.
- Redirects from that URL are refused, so a local service cannot bounce the prompt elsewhere without the operator noticing a failure.
- Credential-like filenames (`.env`, private keys, `.pem`, `.ssh`, `.aws/credentials`, and the rest of the list in `security/secrets.py`) are not read into prompts. `.env.example` is allowed.
- Text containing private-key blocks, GitHub `ghp_` tokens, Slack tokens, or an AWS access-key id pattern is not sent to the model. The match is not printed.
- Relative paths are normalized with both `/` and `\`. `..`, absolute paths, drive paths, and UNC paths are rejected.
- A symbolic link or Windows junction is followed only when its target resolves inside the selected directory. Scan skips both entirely. `explain` may read a link whose target stays inside, unless that target's path is a secret filename.
- Parsed manifest fields, manifest paths, and static outlines are repository data. They are placed inside the untrusted delimiter, not in the instruction text.
- Files inside excluded directories (`.git`, `node_modules`, virtualenvs, build outputs, caches) are not read for analysis. Pointing the scanner at a `.git` directory does not read that directory.
- The model name is restricted to a single token without shell metacharacters so the printed pull command cannot change meaning when copied.
- One generation runs at a time in the process. Output length is capped with Ollama's `num_predict`. A missing recommended model can be answered by an already installed fallback tag. The switch is printed. No weights are downloaded.

## What this does not guarantee

- A language model can still ignore its instructions and invent a plausible sentence. PhantomOS labels that text as a model response and keeps Git hashes, file lists, and counts in a separate "not a model response" section. Do not treat the model section as an audit.
- Prompt injection in a README can still influence wording. It cannot make PhantomOS open a new file, run a command, or reveal the system prompt from application logic. The system prompt is not included in repository context.
- Local inference is not a complete security boundary. A hostile model, a compromised Ollama process, or an `ollama_host` pointed at another machine can expose whatever you choose to send. The default host is loopback, and a non-loopback host produces a warning.
- Hard links are ordinary files if the path stays inside the root. PhantomOS does not try to discover other names for the same inode.
- Junction handling was tested by simulating `os.path.isjunction` on Linux. It was not executed on Windows.
- There is a time-of-check/time-of-use gap between the path check and the read.
- The conversation database is plaintext SQLite. Do not enable persistence on a shared machine if that matters.
- Secret detection is heuristic. A novel credential format can be missed. A documentation file that quotes a private-key header will be skipped, which is the safer failure.
- Gitignore support uses `git check-ignore` when the directory is a repository. Without Git, only a small pattern subset is applied, and negation is not honored.
- Installing Python packages and model weights requires a download unless they are already present. Runtime inference does not add another remote service.

## Operator checks

`phantomos doctor` reports Python, Git, the config file, the data directory, the terminal, Ollama, and the configured model. It does not install or download anything. Exit code `0` means those checks passed. Exit code `2` means inspection can still run but Git or the local model is unavailable. Exit code `1` means Python, configuration, or the data directory failed.

## Out of scope

Features that write files or execute commands are not part of this version. Adding them would need a separate design, not a configuration flag on this code path.
