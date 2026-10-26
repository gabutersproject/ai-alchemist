"""Atmosphere, kept apart from repository facts.

These strings may set a tone. They must not introduce hashes, dates, authors,
files, or findings. Callers interpolate evidence themselves.
"""

_INTRO = {
    "off": (
        "PhantomOS\n"
        "Read-only repository assistant. Inspection and Git history work without a model.\n"
        "Commands: help, status, scan, history, explain, model, personality, repo, memory, exit.\n"
        "Any other line is a question. It is not a shell command.\n"
        "The past never leaves the repository."
    ),
    "subtle": (
        "PhantomOS is listening. The archive is read-only, and it can be read with no model.\n"
        "Commands: help, status, scan, history, explain, model, personality, repo, memory, exit.\n"
        "Any other line is a question. It is not a shell command.\n"
        "The past never leaves the repository."
    ),
    "normal": (
        "Another explorer enters the archive.\n"
        "Some code refuses to rest.\n"
        "I can read what was left behind without a model. I cannot change it.\n"
        "Commands: help, status, scan, history, explain, model, personality, repo, memory, exit.\n"
        "Any other line is a question for the local model, never a shell command."
    ),
    "cursed": (
        "You opened the archive. The archive noticed.\n"
        "Some code refuses to rest.\n"
        "I will answer from the files, not from the dark, and I can do that with the model silent.\n"
        "Commands: help, status, scan, history, explain, model, personality, repo, memory, exit.\n"
        "Any other line is a question. It is not a shell command."
    ),
}

_PREFIX = {
    "off": {
        "facts": "",
        "history": "",
        "explain": "",
        "oldest": "",
        "newest": "",
        "ai_missing": "",
    },
    "subtle": {
        "facts": "The directory has been read. Nothing was changed.",
        "history": "Commit metadata follows. Nothing was rewritten.",
        "explain": "Static reading only. The file was not run.",
        "oldest": "Oldest recorded commit.",
        "newest": "Newest recorded commit.",
        "ai_missing": "The local model is not available. Repository facts still stand.",
    },
    "normal": {
        "facts": "I only read what the repository left behind.",
        "history": "These are the surviving traces. Even ghosts need evidence.",
        "explain": "This file has been sleeping here. I read it. I did not wake it by running it.",
        "oldest": "The oldest surviving trace in this repository is below. Even ghosts need evidence.",
        "newest": "The newest recorded trace is below.",
        "ai_missing": "The voice that interprets the archive is silent. The records are still here.",
    },
    "cursed": {
        "facts": "I walked the directories. I touched nothing.",
        "history": "Old commits rustle like paper. I will not invent a date.",
        "explain": "The function is still on the page. I will not pretend I ran it.",
        "oldest": "The oldest surviving trace is below. I will not invent a hash, a date, or a motive.",
        "newest": "The newest trace is below. Recency is not a verdict.",
        "ai_missing": "The interpreter is gone. Do not mistake silence for an answer.",
    },
}


def intro_text(personality: str) -> str:
    """Opening lines for the interactive shell."""
    return _INTRO.get(personality, _INTRO["normal"])


def narration(personality: str, key: str) -> str:
    """A short lead-in. Empty when narration is off or the key is unknown."""
    table = _PREFIX.get(personality, _PREFIX["normal"])
    return table.get(key, "")


def discovery_line(personality: str, languages: dict[str, int]) -> str:
    """One sentence from extension counts. The counts are supplied by the scanner."""
    if personality == "off":
        return ""
    if not languages:
        return "No eligible source files were discovered."
    ordered = sorted(languages.items(), key=lambda item: (-item[1], item[0].lower()))
    name, count = ordered[0]
    noun = "file" if count == 1 else "files"
    verb = "was" if count == 1 else "were"
    others = sum(item_count for _, item_count in ordered[1:])
    if personality == "subtle":
        line = f"{count} {name} {noun} {verb} found by extension. The files were not executed."
    else:
        line = f"The repository has awakened. {count} {name} {noun} {verb} discovered."
        if personality == "cursed":
            line += " I will not invent the rest."
    if others:
        extra = "file" if others == 1 else "files"
        line += f" {others} other eligible source {extra} had a different extension."
    return line
