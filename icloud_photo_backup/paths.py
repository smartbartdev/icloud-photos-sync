from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Any, Optional

from .errors import StorageError


APP_DIR_NAME = "ipb"
DEFAULT_DB_NAME = ".ipb.sqlite3"


def config_dir() -> Path:
    """Return the user config directory for ipb."""
    return Path.home() / ".config" / APP_DIR_NAME


def config_file_path() -> Path:
    """Return path to config.json."""
    return config_dir() / "config.json"


def session_dir() -> Path:
    """Return path to session directory."""
    return config_dir() / "session"


def log_file_path() -> Path:
    """Return default file log path."""
    return config_dir() / "logs" / "ipb.log"


def ensure_config_layout() -> None:
    """Create config directory structure if missing."""
    config_dir().mkdir(parents=True, exist_ok=True)
    (config_dir() / "logs").mkdir(parents=True, exist_ok=True)
    session_dir().mkdir(parents=True, exist_ok=True)


def resolve_destination(cli_destination: Optional[Path], default_destination: Optional[str]) -> Path:
    """Resolve sync destination using CLI arg, config, then cwd."""
    if cli_destination is not None:
        return cli_destination.expanduser().resolve()
    if default_destination:
        return Path(default_destination).expanduser().resolve()
    return Path.cwd().resolve()


def unique_path(dest: Path) -> Path:
    """Return a non-colliding path by appending _N before extension."""
    if not dest.exists():
        return dest

    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def parse_created_at(value: Any) -> Optional[dt.datetime]:
    """Normalize asset created date into a datetime when possible."""
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time.min)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for parser in (
            lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00")),
            lambda s: dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S"),
            lambda s: dt.datetime.strptime(s, "%Y-%m-%d"),
        ):
            try:
                return parser(text)
            except ValueError:
                continue
    return None


def build_output_dir(target_dir: Path, created_at: Optional[dt.datetime]) -> Path:
    """Build date-based output directory from creation date."""
    if created_at is None:
        return target_dir / "unknown_date"
    return target_dir / f"{created_at.year:04d}" / f"{created_at.month:02d}"


def validate_target_dir(target_dir: Path) -> None:
    """Fail fast when destination is invalid or likely unmounted."""
    if str(target_dir).startswith("/Volumes/"):
        parts = target_dir.parts
        if len(parts) >= 3:
            mount_root = Path("/Volumes") / parts[2]
            if not mount_root.exists():
                raise StorageError(
                    f"External drive appears unmounted: {mount_root}. "
                    "Please mount it and retry."
                )

    target_dir.mkdir(parents=True, exist_ok=True)

    if not os.access(target_dir, os.W_OK):
        raise StorageError(f"Destination is not writable: {target_dir}")

    probe = target_dir / ".icloud_sync_write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise StorageError(f"Destination is not writable: {target_dir}") from exc
