# Lamp Archive

A leftover catalog of brightness readings from a lighting workshop.

This directory is a sample project for PhantomOS. It does not contain its own `.git` directory. If you run PhantomOS from a checkout that already contains this folder, Git commands report that outer work tree, because that is the repository Git itself would use. PhantomOS will not run `git init` for you. Copy the folder somewhere else and initialize Git there when you want the lamp archive to be its own repository.

The interesting detail is in `src/catalog.py`: `average_brightness` walks every reading except the last one, then divides by the full length. That is visible in the source. It is not something PhantomOS has executed.

## Try it

From the PhantomOS checkout:

```bash
phantomos inspect examples/sample_repository --no-ai
phantomos explain examples/sample_repository --file src/catalog.py --no-ai
```

To exercise history, initialize Git in this directory yourself, commit the files, and then run `phantomos history`.
