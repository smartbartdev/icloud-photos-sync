from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .errors import ConfigError
from .paths import config_file_path, ensure_config_layout, log_file_path


KEYCHAIN_SERVICE = "ipb"


def default_config() -> Dict[str, Any]:
    """Return default config values."""
    return {
        "icloud_username": "",
        "use_keychain": False,
        "default_destination": None,
        "db_name": ".ipb.sqlite3",
        "log_file": str(log_file_path()),
    }


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load config.json merged with defaults."""
    cfg_path = path or config_file_path()
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as fh:
        loaded = json.load(fh)

    if not isinstance(loaded, dict):
        raise RuntimeError(f"Invalid config format in {cfg_path}")

    cfg = default_config()
    cfg.update(loaded)
    return cfg


def save_config(config: Dict[str, Any], path: Optional[Path] = None) -> Path:
    """Write config.json to disk."""
    ensure_config_layout()
    cfg_path = path or config_file_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with cfg_path.open("w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
        fh.write("\n")
    return cfg_path


def _load_keyring_module() -> Any:
    try:
        return importlib.import_module("keyring")
    except Exception as exc:  # pragma: no cover
        raise ConfigError("keyring is required when use_keychain=true") from exc


def get_password(config: Dict[str, Any]) -> Optional[str]:
    """Get iCloud password from config or keychain."""
    username = str(config.get("icloud_username") or "")
    if not username:
        return None

    if bool(config.get("use_keychain", False)):
        keyring = _load_keyring_module()
        return keyring.get_password(KEYCHAIN_SERVICE, username)

    password = config.get("icloud_password")
    if password is None:
        return None
    return str(password)


def set_credentials(
    config: Dict[str, Any],
    *,
    username: str,
    password: str,
    use_keychain: bool,
) -> Dict[str, Any]:
    """Update config and secret storage for credentials."""
    updated = dict(config)
    updated["icloud_username"] = username
    updated["use_keychain"] = use_keychain

    if use_keychain:
        keyring = _load_keyring_module()
        keyring.set_password(KEYCHAIN_SERVICE, username, password)
        updated.pop("icloud_password", None)
    else:
        old_username = str(config.get("icloud_username") or "")
        if old_username:
            try:
                keyring = _load_keyring_module()
                keyring.delete_password(KEYCHAIN_SERVICE, old_username)
            except Exception:
                pass
        updated["icloud_password"] = password

    return updated


def clear_credentials(config: Dict[str, Any]) -> Dict[str, Any]:
    """Remove stored credentials from config and keychain."""
    updated = dict(config)
    username = str(updated.get("icloud_username") or "")
    use_keychain = bool(updated.get("use_keychain", False))

    if username and use_keychain:
        try:
            keyring = _load_keyring_module()
            keyring.delete_password(KEYCHAIN_SERVICE, username)
        except Exception:
            pass

    updated["icloud_username"] = ""
    updated["use_keychain"] = False
    updated.pop("icloud_password", None)
    return updated


def redact_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of config with secrets hidden."""
    redacted = dict(config)
    if "icloud_password" in redacted:
        redacted["icloud_password"] = "********"
    return redacted
