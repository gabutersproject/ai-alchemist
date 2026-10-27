"""Errors the laboratory can show without pretending to be a model reply."""


class LabError(Exception):
    """A failure of configuration, validation, or the provider connection."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
