# Changelog

## 0.2.0

AI Alchemist is now a local laboratory for open-weight models. The previous program in this repository was a read-only terminal inspector for Git repositories. That inspector is no longer in the tree. Git history still has it.

### Laboratory

- Playground with streaming replies, stop, new conversation, and copy.
- Ollama adapter for `/api/tags` and `/api/chat`. Loopback hosts are labeled local. Other hosts are labeled remote.
- Model list built only from the provider payload.
- Side-by-side comparison of two model names, with independent errors and no ranking.
- Optional SQLite experiment history, off until enabled, with delete controls.
- Ghost mode and the emerald and gold laboratory interface.
- Settings for host, optional bearer token, models, output cap, and history.

### Kept from the earlier tree

- MIT license.
- The mark in `docs/assets/mark.svg`, also served from the web interface.
- `docs/dev-community-article.md`, which describes the retired inspector.
- The rule that a provider failure is not replaced with an invented answer, that redirects are not followed, and that tool calls are not executed. Those rules were reimplemented for the laboratory.

### Removed

- The `inspect`, `history`, `explain`, and `haunt` commands.
- Git repository scanning.
- The sample lamp repository under `examples/`.

An older inspector config file is not migrated. Laboratory settings use `lab-config.json`.
