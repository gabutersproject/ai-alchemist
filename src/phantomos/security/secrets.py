"""Recognizers for files that must never enter a model prompt."""

import re
from pathlib import Path

_EXAMPLE_SUFFIXES = (".example", ".sample", ".template", ".dist", ".example.txt")
_SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.staging",
    ".env.testing",
    ".netrc",
    ".npmrc",
    ".pypirc",
    ".pgpass",
    ".htpasswd",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials.json",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
    "service-account.json",
    "serviceaccount.json",
}
_SECRET_SUFFIXES = (
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".kdbx",
    ".keystore",
    ".jks",
    ".ppk",
)
_PRIVATE_KEY_MARKERS = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "-----BEGIN PGP PRIVATE KEY BLOCK-----",
    "-----BEGIN DSA PRIVATE KEY-----",
    "-----BEGIN EC PRIVATE KEY-----",
)
_ACCESS_KEY_ID = re.compile(r"AKIA[0-9A-Z]{16}")


def is_secret_path(path: Path) -> bool:
    """Return True for obvious credential filenames and sensitive directories.

    Placeholder files such as `.env.example` are allowed. Real `.env` files are not.
    """
    name = path.name.lower()
    if any(name.endswith(suffix) for suffix in _EXAMPLE_SUFFIXES):
        return False
    parts = {part.lower() for part in path.parts}
    if ".ssh" in parts or ".gnupg" in parts:
        return True
    if ".aws" in parts and name in {"credentials", "config"}:
        return True
    if name.startswith(".env"):
        return True
    if name in _SECRET_NAMES:
        return True
    return name.endswith(_SECRET_SUFFIXES)


def content_looks_sensitive(text: str) -> bool:
    """Detect credential material inside an otherwise ordinary text file.

    The match itself is never returned, so callers cannot accidentally log it.
    """
    if any(marker in text for marker in _PRIVATE_KEY_MARKERS):
        return True
    lowered = text.lower()
    if "aws_secret_access_key" in lowered:
        return True
    if "xoxb-" in text or "xoxp-" in text or "ghp_" in text:
        return True
    return _ACCESS_KEY_ID.search(text) is not None
