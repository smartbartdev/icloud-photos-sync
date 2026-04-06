from __future__ import annotations

import getpass
import importlib
import logging
from types import ModuleType
from typing import Any, Optional

from .errors import AuthError


def load_pyicloud_module() -> ModuleType:
    """Load a supported iCloud client module."""
    candidates = ("pyicloud", "pyicloud_ipd")
    errors: list[str] = []

    for module_name in candidates:
        try:
            return importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{module_name}: {exc}")

    details = "; ".join(errors)
    raise AuthError(
        "No supported iCloud client module found. "
        "Install/repair dependency: pip install pyicloud. "
        f"Details: {details}"
    )


def login_icloud(username: str, password: Optional[str], logger: logging.Logger) -> Any:
    """Authenticate to iCloud and handle interactive 2FA when required."""
    if not username:
        raise AuthError("Missing iCloud username.")

    if not password:
        password = getpass.getpass("Enter iCloud password: ")

    logger.info("Logging into iCloud...")

    try:
        pyicloud_module = load_pyicloud_module()
        PyiCloudService = getattr(pyicloud_module, "PyiCloudService")
    except Exception as exc:  # pragma: no cover - import failure path
        raise AuthError(
            "Unable to load iCloud client. "
            "If installed via Homebrew, run: brew reinstall smartbartdev/tap/ipb"
        ) from exc

    try:
        api = PyiCloudService(username, password)
    except Exception as exc:  # noqa: BLE001
        raise AuthError(f"Unable to authenticate to iCloud: {exc}") from exc

    if getattr(api, "requires_2fa", False):
        logger.info("Two-factor authentication required.")
        code = input("Enter the 2FA code: ").strip()
        if not code:
            raise AuthError("No 2FA code entered.")

        if not api.validate_2fa_code(code):
            raise AuthError("Invalid 2FA code.")

        if not api.is_trusted_session:
            logger.info("Requesting trusted session...")
            try:
                api.trust_session()
            except Exception:
                logger.info("Could not mark this session as trusted; continuing.")

    logger.info("Authenticated successfully.")
    return api
