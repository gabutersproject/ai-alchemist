# Changelog

## Unreleased

The public name, the Python package, the console script, the environment variables, and the data directory are all AI Alchemist. Inspection, history, explain, the Ollama client, and the read-only rules behave as they did before this rename. The version number is still 0.1.0.

### Names

| What | Name |
| --- | --- |
| Command | `ai-alchemist` |
| Python package | `ai_alchemist` (`src/ai_alchemist`) |
| Module | `python -m ai_alchemist` |
| Settings class | `AlchemistConfig` |
| Error base class | `AIAlchemistError` |
| Environment variables | `AI_ALCHEMIST_*` |
| Data directory | `ai-alchemist` |

The old `phantomos` command, `PHANTOMOS_*` variables, and `phantomos` data directory are not read. Copy an existing `config.json` into the new data directory if you want to keep those settings.

Command names and flags are unchanged, including `haunt`.
