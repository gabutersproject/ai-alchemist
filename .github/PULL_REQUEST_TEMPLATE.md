## What changed

## How to check

- [ ] `python -m pytest`
- [ ] `python -m ruff check src tests`

## Boundaries

- [ ] The change does not execute prompts as shell commands, download a model, or invent a reply when the provider fails.
- [ ] Provider tokens are not returned to the browser, logged, or written into experiment history.
