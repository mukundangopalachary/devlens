class DevLensError(Exception):
    """Base application error."""


class StaticAnalysisError(DevLensError):
    """Raised when static analysis fails for a file."""
