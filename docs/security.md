# Security model

AI Alchemist sends prompts to the configured Ollama host and can store them locally. The controls below are in application code.

## Enforced behavior

- The server binds to `127.0.0.1` unless you choose another address. Binding beyond loopback prints a warning.
- Prompts are not passed to a shell. The package does not import `subprocess` or call `os.system`.
- The Ollama payload has no `tools` field. A `tool_calls` reply is an error and is not executed.
- Redirects are refused, so a configured host cannot bounce the prompt to another URL without the request failing.
- The host URL cannot embed a username or password. An optional bearer token is stored in the settings file, sent only to that host, and omitted from API responses.
- Provider error text is scrubbed of the saved token before it is shown.
- A turn whose prompt or reply contains the saved token is not written to SQLite.
- History is off until `persist_experiments` is enabled, and the request must also ask to save.
- Model names are a single token without spaces or shell metacharacters.
- An empty or malformed provider body is an error. The application does not substitute its own paragraph.
- Static pages do not contain the token. Ghost mode stores only a browser flag, not settings.

## What this does not guarantee

- A model can still produce a false sentence. That text is the model's reply.
- A remote `ollama_host` receives whatever you send. The interface calls that remote inference.
- Anyone who can open a non-loopback bind can read history and change the host.
- The SQLite file and the settings file are not encrypted.
- Secret detection for prompts is limited to the configured token string. Other secrets you type can be saved if history is on.
- Stopping a stream closes the read. A provider that has already started work may continue until its own timeout.
- Ollama's own process, and any model you pull, have their own risks.

## Operator checks

`POST /api/settings/test` and `GET /api/provider` report whether Ollama responded, whether the host address is loopback, and how many tags came back. A failed check leaves `model_count` null. It does not claim that zero models are installed when the host could not be reached.
