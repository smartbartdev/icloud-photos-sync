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


def _print_2fa_help() -> None:
    print(
        "If you do not receive a 2FA push notification, you can generate a code "
        "from another trusted Apple device and paste it here."
    )


def _select_trusted_device(api: Any) -> Optional[dict[str, Any]]:
    trusted_devices = getattr(api, "trusted_devices", None)
    if not trusted_devices:
        return None

    print("No code yet? Request one from a trusted device:")
    for index, device in enumerate(trusted_devices, start=1):
        label = (
            str(device.get("deviceName") or "").strip()
            or str(device.get("phoneNumber") or "").strip()
            or str(device.get("id") or "unknown")
        )
        print(f"  {index}) {label}")

    raw_choice = input(
        "Select device number to request code "
        "(or press Enter to skip): "
    ).strip()
    if not raw_choice:
        return None

    try:
        choice = int(raw_choice)
    except ValueError as exc:
        raise AuthError("Invalid trusted-device selection.") from exc

    if choice < 1 or choice > len(trusted_devices):
        raise AuthError("Trusted-device selection is out of range.")
    return trusted_devices[choice - 1]


def _validate_with_best_method(api: Any, code: str, device: Optional[dict[str, Any]]) -> bool:
    if device is not None and hasattr(api, "validate_verification_code"):
        return bool(api.validate_verification_code(device, code))
    if hasattr(api, "validate_2fa_code"):
        return bool(api.validate_2fa_code(code))
    if device is not None and hasattr(api, "validate_verification_code"):
        return bool(api.validate_verification_code(device, code))
    raise AuthError("This iCloud client does not support 2FA code validation.")


def _run_2fa_flow(api: Any, logger: logging.Logger) -> None:
    logger.info("Two-factor authentication required.")
    _print_2fa_help()

    code = input("Enter the 2FA code (or press Enter for help): ").strip()
    device = None

    if not code:
        device = _select_trusted_device(api)
        if device is not None:
            send_verification_code = getattr(api, "send_verification_code", None)
            if not callable(send_verification_code):
                raise AuthError("Unable to request a verification code for this account.")
            try:
                requested = bool(send_verification_code(device))
            except Exception as exc:  # noqa: BLE001
                raise AuthError(f"Failed requesting verification code: {exc}") from exc
            if not requested:
                raise AuthError("Failed requesting verification code from trusted device.")

        code = input("Enter the verification code: ").strip()

    if not code:
        raise AuthError("No 2FA code entered.")

    if not _validate_with_best_method(api, code, device):
        raise AuthError("Invalid 2FA code.")


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
        _run_2fa_flow(api, logger)

        if not api.is_trusted_session:
            logger.info("Requesting trusted session...")
            try:
                api.trust_session()
            except Exception:
                logger.info("Could not mark this session as trusted; continuing.")

    logger.info("Authenticated successfully.")
    return api
