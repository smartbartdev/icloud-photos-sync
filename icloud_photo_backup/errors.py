from __future__ import annotations


class IPBError(Exception):
    """Base class for expected ipb application errors."""


class ConfigError(IPBError):
    """Raised for configuration-related failures."""


class AuthError(IPBError):
    """Raised for iCloud authentication failures."""


class StorageError(IPBError):
    """Raised for destination and DB storage failures."""
