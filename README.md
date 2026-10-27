# AI Alchemist

![AI Alchemist mark](docs/assets/mark.svg)

**Transform Ideas Into Intelligence.**

Where AI meets the art of transformation.

AI Alchemist is a read-only terminal assistant for developers who want to look through an old repository without uploading it. It keeps recorded facts separate from optional local model commentary, and it still works when you decline the model.

The interactive session is `ai-alchemist haunt`. The investigation commands are `inspect`, `history`, and `explain`.

It is a developer tool. It is not an operating system, and it does not claim to talk to anything supernatural.

Local inference uses [Ollama](https://ollama.com/). There is no commercial model API. If Ollama is not running, inspection and history still work. AI Alchemist will say that the model is unavailable instead of inventing an answer.

This repository was first presented as PhantomOS. The public name is now AI Alchemist. The import package, configuration directory, and environment variables still use `phantomos` so an existing checkout keeps working. See [Compatibility](#compatibility).
