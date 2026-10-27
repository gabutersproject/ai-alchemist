"""Expected failures the CLI can explain without a traceback."""


class PhantomOSError(Exception):
    """Base class for errors the interface can report directly."""

    exit_code = 1


class ConfigError(PhantomOSError):
    """Configuration is missing, unreadable, or invalid."""


class PathSecurityError(PhantomOSError):
    """A path tried to leave the selected repository or was otherwise unsafe."""


class RepositoryError(PhantomOSError):
    """The path cannot be inspected."""


class NotAGitRepositoryError(RepositoryError):
    """The directory exists but is not a Git repository."""


class SecretFileError(PhantomOSError):
    """A requested file looks like credential material and was refused."""

    def __init__(self, relative: str) -> None:
        self.relative = relative
        super().__init__(
            f"Refused to read '{relative}' because it looks like a secret or credential file."
        )


class SensitiveContentError(PhantomOSError):
    """File text appears to contain credential material."""

    def __init__(self, relative: str) -> None:
        self.relative = relative
        super().__init__(
            "Refused to send "
            f"'{relative}' to the model because it appears to contain credential material."
        )


class FileSkippedError(PhantomOSError):
    """The path is inside the repository but is not eligible for analysis."""


class AIUnavailableError(PhantomOSError):
    """The local model is not reachable. This is not an inference result."""

    exit_code = 2


class AIResponseError(PhantomOSError):
    """The model service responded in a way AI Alchemist will not treat as an answer."""
