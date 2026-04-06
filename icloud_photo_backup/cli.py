from __future__ import annotations

import argparse
import datetime as dt
import getpass
import importlib
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Optional

from .auth import load_pyicloud_module
from .config import (
    clear_credentials,
    default_config,
    get_password,
    load_config,
    redact_config,
    save_config,
    set_credentials,
)
from .db import (
    get_downloaded_count,
    get_latest_downloaded_created_at,
    get_meta,
    init_db,
    set_meta,
)
from .errors import AuthError, ConfigError, StorageError
from .paths import (
    DEFAULT_DB_NAME,
    config_dir,
    config_file_path,
    ensure_config_layout,
    log_file_path,
    resolve_destination,
    session_dir,
    validate_target_dir,
)
from .sync import run_sync


EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_CONFIG = 2
EXIT_AUTH = 3
EXIT_STORAGE = 4


def parse_after_date(value: Optional[str]) -> Optional[dt.date]:
    """Parse --after value in YYYY-MM-DD format."""
    if value is None:
        return None
    try:
        return dt.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--after must be in YYYY-MM-DD format") from exc


def cmd_init(_: argparse.Namespace) -> int:
    """Initialize config interactively."""
    ensure_config_layout()
    base = default_config()

    username = input("iCloud username: ").strip()
    if not username:
        print("Config error: username is required", file=sys.stderr)
        return EXIT_CONFIG

    password = getpass.getpass("iCloud password: ")
    if not password:
        print("Config error: password is required", file=sys.stderr)
        return EXIT_CONFIG

    use_keychain_raw = input("Use macOS keychain? [Y/n]: ").strip().lower()
    use_keychain = use_keychain_raw in ("", "y", "yes")

    default_destination = input("Default destination (optional): ").strip()
    if default_destination:
        try:
            validate_target_dir(Path(default_destination).expanduser().resolve())
        except Exception as exc:  # noqa: BLE001
            print(f"Config error: {exc}", file=sys.stderr)
            return EXIT_CONFIG
        base["default_destination"] = str(
            Path(default_destination).expanduser().resolve()
        )

    try:
        base = set_credentials(
            base,
            username=username,
            password=password,
            use_keychain=use_keychain,
        )
        save_config(base)
    except Exception as exc:  # noqa: BLE001
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    print(f"Initialized config at {config_file_path()}")
    return EXIT_OK


def cmd_restore(args: argparse.Namespace) -> int:
    """Restore ipb initialization from an existing backup destination."""
    try:
        ensure_config_layout()
        cfg = load_config() if config_file_path().exists() else default_config()

        destination = (
            args.destination.expanduser().resolve()
            if args.destination
            else Path.cwd().resolve()
        )
        if not destination.exists() or not destination.is_dir():
            print(
                f"Storage error: backup directory not found: {destination}",
                file=sys.stderr,
            )
            return EXIT_STORAGE

        validate_target_dir(destination)
        db_name = str(cfg.get("db_name") or DEFAULT_DB_NAME)
        db_path = destination / db_name
        if not db_path.exists():
            print(
                f"Storage error: ipb manifest not found at {db_path}",
                file=sys.stderr,
            )
            return EXIT_STORAGE

        cfg["default_destination"] = str(destination)

        if not str(cfg.get("icloud_username") or ""):
            username = input("iCloud username: ").strip()
            if not username:
                print("Config error: username is required", file=sys.stderr)
                return EXIT_CONFIG

            password = getpass.getpass("iCloud password: ")
            if not password:
                print("Config error: password is required", file=sys.stderr)
                return EXIT_CONFIG

            use_keychain_raw = input("Use macOS keychain? [Y/n]: ").strip().lower()
            use_keychain = use_keychain_raw in ("", "y", "yes")
            cfg = set_credentials(
                cfg,
                username=username,
                password=password,
                use_keychain=use_keychain,
            )

        save_config(cfg)

        conn = init_db(db_path)
        try:
            current_cursor = get_meta(conn, "last_downloaded_created_at")
            if current_cursor is None:
                latest_created_at = get_latest_downloaded_created_at(conn)
                if latest_created_at is not None:
                    set_meta(conn, "last_downloaded_created_at", latest_created_at)
                    print(
                        "Restored cursor: "
                        f"last_downloaded_created_at={latest_created_at}"
                    )
        finally:
            conn.close()

        print(f"Restored backup initialization for {destination}")
        print(f"Config saved at {config_file_path()}")
        return EXIT_OK
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    except StorageError as exc:
        print(f"Storage error: {exc}", file=sys.stderr)
        return EXIT_STORAGE
    except Exception as exc:  # noqa: BLE001
        print(f"Runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME


def _load_required_config() -> dict:
    try:
        cfg = load_config()
    except FileNotFoundError as exc:
        raise ConfigError("Config not found. Run: ipb init") from exc
    if not str(cfg.get("icloud_username") or ""):
        raise ConfigError("Missing icloud_username in config. Run: ipb init")
    return cfg


def cmd_sync(args: argparse.Namespace) -> int:
    """Run incremental sync."""
    try:
        cfg = _load_required_config()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    except Exception as exc:  # noqa: BLE001
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    try:
        destination = resolve_destination(args.destination, cfg.get("default_destination"))
        db_name = str(cfg.get("db_name") or DEFAULT_DB_NAME)
        db_path = (
            args.db_path.expanduser().resolve()
            if args.db_path is not None
            else destination / db_name
        )
        password = get_password(cfg)
        username = str(cfg.get("icloud_username") or "")
        return run_sync(
            target_dir=destination,
            db_path=db_path,
            dry_run=args.dry_run,
            limit=args.limit,
            verbose=args.verbose,
            after=args.after,
            skip_videos=args.skip_videos,
            missing_created_at_strategy=args.missing_created_at,
            username=username,
            password=password,
            app_log_file=Path(str(cfg.get("log_file") or log_file_path())).expanduser(),
        )
    except sqlite3.OperationalError as exc:
        print(f"Storage error: {exc}", file=sys.stderr)
        return EXIT_STORAGE
    except AuthError as exc:
        print(f"Auth error: {exc}", file=sys.stderr)
        return EXIT_AUTH
    except StorageError as exc:
        print(f"Storage error: {exc}", file=sys.stderr)
        return EXIT_STORAGE
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    except Exception as exc:  # noqa: BLE001
        print(f"Runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME


def cmd_config_show(_: argparse.Namespace) -> int:
    """Display config with redacted secrets."""
    try:
        cfg = redact_config(load_config())
    except FileNotFoundError:
        print("Config error: config not found. Run: ipb init", file=sys.stderr)
        return EXIT_CONFIG
    except Exception as exc:  # noqa: BLE001
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    for key in (
        "icloud_username",
        "icloud_password",
        "use_keychain",
        "default_destination",
        "db_name",
        "log_file",
    ):
        if key in cfg:
            print(f"{key}: {cfg[key]}")
    return EXIT_OK


def _doctor_line(ok: bool, label: str, detail: str = "") -> bool:
    status = "OK" if ok else "FAIL"
    suffix = f" ({detail})" if detail else ""
    print(f"[{status}] {label}{suffix}")
    return ok


def cmd_doctor(_: argparse.Namespace) -> int:
    """Run local environment checks."""
    all_ok = True

    ensure_config_layout()
    all_ok &= _doctor_line(config_dir().exists(), "config directory", str(config_dir()))

    cfg_exists = config_file_path().exists()
    all_ok &= _doctor_line(cfg_exists, "config file", str(config_file_path()))

    if cfg_exists:
        try:
            cfg = load_config()
            _doctor_line(True, "config readable")
        except Exception as exc:  # noqa: BLE001
            all_ok = False
            _doctor_line(False, "config readable", str(exc))
            cfg = default_config()
    else:
        cfg = default_config()

    try:
        module = load_pyicloud_module()
        _doctor_line(True, "pyicloud installed", module.__name__)
    except Exception as exc:  # noqa: BLE001
        all_ok = False
        _doctor_line(False, "pyicloud installed", str(exc))

    try:
        sqlite3.connect(":memory:").close()
        _doctor_line(True, "sqlite available")
    except Exception as exc:  # noqa: BLE001
        all_ok = False
        _doctor_line(False, "sqlite available", str(exc))

    destination = resolve_destination(None, cfg.get("default_destination"))
    try:
        validate_target_dir(destination)
        _doctor_line(True, "destination writable", str(destination))
    except Exception as exc:  # noqa: BLE001
        all_ok = False
        _doctor_line(False, "destination writable", str(exc))

    if bool(cfg.get("use_keychain", False)):
        try:
            importlib.import_module("keyring")
            _doctor_line(True, "keyring available")
        except Exception:
            all_ok = False
            _doctor_line(False, "keyring available")

    return EXIT_OK if all_ok else EXIT_RUNTIME


def cmd_login(_: argparse.Namespace) -> int:
    """Overwrite credential settings."""
    try:
        cfg = load_config()
    except FileNotFoundError:
        cfg = default_config()

    username = input("iCloud username: ").strip()
    if not username:
        print("Config error: username is required", file=sys.stderr)
        return EXIT_CONFIG
    password = getpass.getpass("iCloud password: ")
    if not password:
        print("Config error: password is required", file=sys.stderr)
        return EXIT_CONFIG
    use_keychain_raw = input("Use macOS keychain? [Y/n]: ").strip().lower()
    use_keychain = use_keychain_raw in ("", "y", "yes")

    try:
        cfg = set_credentials(
            cfg,
            username=username,
            password=password,
            use_keychain=use_keychain,
        )
        save_config(cfg)
    except Exception as exc:  # noqa: BLE001
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    print("Login credentials updated.")
    return EXIT_OK


def cmd_logout(_: argparse.Namespace) -> int:
    """Clear credentials and local session files."""
    try:
        cfg = load_config()
    except FileNotFoundError:
        print("Config not found; nothing to logout.")
        return EXIT_OK

    cfg = clear_credentials(cfg)
    save_config(cfg)

    sess = session_dir()
    if sess.exists():
        shutil.rmtree(sess)
    sess.mkdir(parents=True, exist_ok=True)

    print("Logged out. Credentials and session files removed.")
    return EXIT_OK


def cmd_status(args: argparse.Namespace) -> int:
    """Print config and last sync status."""
    try:
        cfg = load_config()
    except FileNotFoundError:
        print("Config error: config not found. Run: ipb init", file=sys.stderr)
        return EXIT_CONFIG
    except Exception as exc:  # noqa: BLE001
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    destination = resolve_destination(args.destination, cfg.get("default_destination"))
    db_name = str(cfg.get("db_name") or DEFAULT_DB_NAME)
    db_path = destination / db_name

    last_sync = None
    last_downloaded_created_at = None
    total_downloaded = 0
    if db_path.exists():
        conn = init_db(db_path)
        try:
            last_sync = get_meta(conn, "last_sync_at")
            last_downloaded_created_at = get_meta(conn, "last_downloaded_created_at")
            if last_downloaded_created_at is None:
                last_downloaded_created_at = get_latest_downloaded_created_at(conn)
            total_downloaded = get_downloaded_count(conn)
        finally:
            conn.close()

    print(f"Config path: {config_file_path()}")
    print(f"Default destination: {cfg.get('default_destination')}")
    print(f"DB path: {db_path}")
    print(f"Last sync timestamp: {last_sync}")
    print(f"Last downloaded created_at: {last_downloaded_created_at}")
    print(f"Total downloaded count: {total_downloaded}")
    return EXIT_OK


def cmd_cursor_rebuild(args: argparse.Namespace) -> int:
    """Rebuild incremental cursor from existing downloaded assets."""
    try:
        cfg = load_config()
    except FileNotFoundError:
        print("Config error: config not found. Run: ipb init", file=sys.stderr)
        return EXIT_CONFIG
    except Exception as exc:  # noqa: BLE001
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    destination = resolve_destination(args.destination, cfg.get("default_destination"))
    db_name = str(cfg.get("db_name") or DEFAULT_DB_NAME)
    db_path = destination / db_name

    if not db_path.exists():
        print(f"Storage error: database not found at {db_path}", file=sys.stderr)
        return EXIT_STORAGE

    conn = init_db(db_path)
    try:
        latest_created_at = get_latest_downloaded_created_at(conn)
        if latest_created_at is None:
            print("No downloaded assets with created_at found; cursor not updated.")
            return EXIT_OK

        set_meta(conn, "last_downloaded_created_at", latest_created_at)
        print(f"Rebuilt cursor: last_downloaded_created_at={latest_created_at}")
        return EXIT_OK
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    """Build ipb command parser."""
    parser = argparse.ArgumentParser(prog="ipb", description="iCloud photo backup CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Interactive setup")
    init_parser.set_defaults(func=cmd_init)

    restore_parser = subparsers.add_parser(
        "restore",
        help="Restore initialization from existing backup",
    )
    restore_parser.add_argument(
        "destination",
        nargs="?",
        type=Path,
        help="Existing backup destination (defaults to cwd)",
    )
    restore_parser.set_defaults(func=cmd_restore)

    sync_parser = subparsers.add_parser("sync", help="Incremental sync")
    sync_parser.add_argument("destination", nargs="?", type=Path, help="Destination root")
    sync_parser.add_argument("--dry-run", action="store_true")
    sync_parser.add_argument("--limit", type=int, default=None)
    sync_parser.add_argument("--after", type=parse_after_date, default=None)
    sync_parser.add_argument("--skip-videos", action="store_true")
    sync_parser.add_argument(
        "--missing-created-at",
        choices=("skip", "download"),
        default="skip",
        help=(
            "How to handle assets with missing created_at when using cursor/--after "
            "(default: skip)"
        ),
    )
    sync_parser.add_argument("--verbose", action="store_true")
    sync_parser.add_argument("--db-path", type=Path, default=None)
    sync_parser.set_defaults(func=cmd_sync)

    config_parser = subparsers.add_parser("config", help="Config operations")
    config_sub = config_parser.add_subparsers(dest="config_command", required=True)
    config_show = config_sub.add_parser("show", help="Show config")
    config_show.set_defaults(func=cmd_config_show)

    doctor_parser = subparsers.add_parser("doctor", help="Environment checks")
    doctor_parser.set_defaults(func=cmd_doctor)

    login_parser = subparsers.add_parser("login", help="Update credentials")
    login_parser.set_defaults(func=cmd_login)

    logout_parser = subparsers.add_parser("logout", help="Clear credentials and sessions")
    logout_parser.set_defaults(func=cmd_logout)

    status_parser = subparsers.add_parser("status", help="Show sync status")
    status_parser.add_argument("destination", nargs="?", type=Path, help="Destination override")
    status_parser.set_defaults(func=cmd_status)

    cursor_parser = subparsers.add_parser("cursor", help="Cursor utilities")
    cursor_sub = cursor_parser.add_subparsers(dest="cursor_command", required=True)
    cursor_rebuild = cursor_sub.add_parser(
        "rebuild",
        help="Rebuild incremental cursor from database",
    )
    cursor_rebuild.add_argument(
        "destination",
        nargs="?",
        type=Path,
        help="Destination override",
    )
    cursor_rebuild.set_defaults(func=cmd_cursor_rebuild)

    return parser


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    if hasattr(args, "limit") and args.limit is not None and args.limit <= 0:
        parser.error("--limit must be a positive integer")

    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("Interrupted.")
        return 130
