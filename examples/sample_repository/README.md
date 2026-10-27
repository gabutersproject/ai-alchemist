# Lamp Archive

A leftover catalog of brightness readings from a lighting workshop.

This directory is a sample project for AI Alchemist. It does not contain its own `.git` directory. If you run AI Alchemist from a checkout that already contains this folder, Git commands report that outer work tree, because that is the repository Git itself would use. AI Alchemist will not run `git init` for you. Copy the folder somewhere else and initialize Git there when you want the lamp archive to be its own repository.

The interesting detail is in `src/catalog.py`: `average_brightness` walks every reading except the last one, then divides by the full length. That is visible in the source. It is not something AI Alchemist has executed.

## Try it

From the AI Alchemist checkout:

```bash
ai-alchemist inspect examples/sample_repository --no-ai
ai-alchemist explain examples/sample_repository --file src/catalog.py --no-ai
```

`phantomos` is the same program. To exercise history, initialize Git in this directory yourself, commit the files, and then run `ai-alchemist history`.
