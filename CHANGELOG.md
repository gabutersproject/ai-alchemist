# Changelog

## Unreleased

Branding only. Inspection, history, explain, the Ollama client, and the read-only rules behave as they did before this rename. The version number is still 0.1.0. This file is not a release announcement.

### Identity

- The public name is AI Alchemist.
- The tagline is "Transform Ideas Into Intelligence."
- The secondary line is "Where AI Meets the Art of Transformation."
- The distribution name in `pyproject.toml` is `ai-alchemist`.
- A new console script, `ai-alchemist`, calls `phantomos.cli:app`.
- The terminal banner and Rich accent colors use the emerald and gold mark. The mark is `docs/assets/mark.svg`.
- Help text, doctor output, model errors, and the system prompt address the assistant as AI Alchemist.

### Documentation

- `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `docs/architecture.md`, `docs/security.md`, and the sample repository README use the new name.
- `docs/dev-community-article.md` stays a historical PhantomOS draft, with a note at the top.

### Compatibility

- The `phantomos` command remains installed.
- `python -m phantomos` remains the module entry point.
- The import package remains `phantomos`. `PhantomOSError` was not renamed.
- Environment variables remain `PHANTOMOS_*`. No `AI_ALCHEMIST_*` names were added.
- The config and database directory remains `phantomos` under the platform data directory.
- Command names and flags are unchanged, including `haunt`.

No config migration is required. Removing the `phantomos` command later would be a separate change.
