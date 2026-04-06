import argparse
import datetime as dt
from pathlib import Path

from icloud_photo_backup import cli
from icloud_photo_backup.db import init_db, mark_downloaded, set_meta
from icloud_photo_backup.errors import AuthError, ConfigError, StorageError


def _sync_args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        destination=tmp_path,
        db_path=None,
        dry_run=False,
        limit=None,
        after=None,
        skip_videos=False,
        missing_created_at="skip",
        verbose=False,
    )


def test_cmd_sync_returns_config_exit_on_missing_config(tmp_path: Path, monkeypatch) -> None:
    args = _sync_args(tmp_path)

    def _raise_config() -> dict:
        raise ConfigError("missing")

    monkeypatch.setattr(cli, "_load_required_config", _raise_config)
    assert cli.cmd_sync(args) == cli.EXIT_CONFIG


def test_cmd_sync_returns_auth_exit(tmp_path: Path, monkeypatch) -> None:
    args = _sync_args(tmp_path)
    monkeypatch.setattr(
        cli,
        "_load_required_config",
        lambda: {
            "icloud_username": "me@example.com",
            "db_name": ".ipb.sqlite3",
            "log_file": str(tmp_path / "ipb.log"),
            "default_destination": None,
        },
    )
    monkeypatch.setattr(cli, "get_password", lambda cfg: "secret")

    def _raise_auth(**kwargs):
        raise AuthError("bad login")

    monkeypatch.setattr(cli, "run_sync", _raise_auth)
    assert cli.cmd_sync(args) == cli.EXIT_AUTH


def test_cmd_sync_returns_storage_exit(tmp_path: Path, monkeypatch) -> None:
    args = _sync_args(tmp_path)
    monkeypatch.setattr(
        cli,
        "_load_required_config",
        lambda: {
            "icloud_username": "me@example.com",
            "db_name": ".ipb.sqlite3",
            "log_file": str(tmp_path / "ipb.log"),
            "default_destination": None,
        },
    )
    monkeypatch.setattr(cli, "get_password", lambda cfg: "secret")

    def _raise_storage(**kwargs):
        raise StorageError("disk full")

    monkeypatch.setattr(cli, "run_sync", _raise_storage)
    assert cli.cmd_sync(args) == cli.EXIT_STORAGE


def test_cmd_sync_passes_resolved_destination(tmp_path: Path, monkeypatch) -> None:
    args = _sync_args(tmp_path)
    expected_destination = tmp_path / "resolved"
    captured = {}

    monkeypatch.setattr(
        cli,
        "_load_required_config",
        lambda: {
            "icloud_username": "me@example.com",
            "db_name": ".ipb.sqlite3",
            "log_file": str(tmp_path / "ipb.log"),
            "default_destination": str(tmp_path / "default"),
        },
    )
    monkeypatch.setattr(cli, "get_password", lambda cfg: "secret")
    monkeypatch.setattr(
        cli,
        "resolve_destination",
        lambda cli_destination, default_destination: expected_destination,
    )

    def _run_sync(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(cli, "run_sync", _run_sync)
    assert cli.cmd_sync(args) == 0
    assert captured["target_dir"] == expected_destination
    assert captured["missing_created_at_strategy"] == "skip"


def test_cmd_status_reads_db_meta_and_counts(tmp_path: Path, monkeypatch, capsys) -> None:
    destination = tmp_path / "dest"
    destination.mkdir(parents=True, exist_ok=True)
    db_path = destination / ".ipb.sqlite3"
    conn = init_db(db_path)
    try:
        set_meta(conn, "last_sync_at", "2026-01-01T00:00:00+00:00")
        mark_downloaded(
            conn,
            asset_id="id-1",
            filename="IMG_1.HEIC",
            local_path=destination / "2026" / "01" / "IMG_1.HEIC",
            created_at=dt.datetime(2026, 1, 1),
            file_size=12,
            media_type="photo",
        )
    finally:
        conn.close()

    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {
            "default_destination": str(destination),
            "db_name": ".ipb.sqlite3",
        },
    )
    monkeypatch.setattr(
        cli,
        "resolve_destination",
        lambda cli_destination, default_destination: destination,
    )

    args = argparse.Namespace(destination=None)
    assert cli.cmd_status(args) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "Last sync timestamp: 2026-01-01T00:00:00+00:00" in out
    assert "Total downloaded count: 1" in out


def test_cmd_doctor_reports_ok_when_checks_pass(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(cli, "ensure_config_layout", lambda: None)
    monkeypatch.setattr(cli, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(cli, "config_file_path", lambda: config_path)
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {"default_destination": str(tmp_path), "use_keychain": False},
    )
    monkeypatch.setattr(
        cli,
        "resolve_destination",
        lambda cli_destination, default_destination: tmp_path,
    )
    monkeypatch.setattr(cli, "validate_target_dir", lambda destination: None)

    def _import_module(name: str):
        if name == "pyicloud":
            class _Module:
                __name__ = "pyicloud"

            return _Module()
        raise ImportError(name)

    monkeypatch.setattr(cli.importlib, "import_module", _import_module)
    assert cli.cmd_doctor(argparse.Namespace()) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "[OK] pyicloud installed" in out
    assert "[OK] destination writable" in out


def test_main_routes_sync_subcommand(tmp_path: Path, monkeypatch) -> None:
    called = {"value": False}

    def _cmd_sync(args: argparse.Namespace) -> int:
        called["value"] = True
        return 0

    monkeypatch.setattr(cli, "cmd_sync", _cmd_sync)
    monkeypatch.setattr(cli.sys, "argv", ["ipb", "sync", str(tmp_path), "--dry-run"])
    assert cli.main() == 0
    assert called["value"] is True


def test_main_routes_restore_subcommand(tmp_path: Path, monkeypatch) -> None:
    called = {"value": False}

    def _cmd_restore(args: argparse.Namespace) -> int:
        called["value"] = True
        return 0

    monkeypatch.setattr(cli, "cmd_restore", _cmd_restore)
    monkeypatch.setattr(cli.sys, "argv", ["ipb", "restore", str(tmp_path)])
    assert cli.main() == 0
    assert called["value"] is True


def test_cmd_cursor_rebuild_sets_meta_from_existing_rows(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    destination = tmp_path / "dest"
    destination.mkdir(parents=True, exist_ok=True)
    db_path = destination / ".ipb.sqlite3"
    conn = init_db(db_path)
    try:
        mark_downloaded(
            conn,
            asset_id="id-1",
            filename="IMG_1.HEIC",
            local_path=destination / "2026" / "01" / "IMG_1.HEIC",
            created_at=dt.datetime(2026, 1, 2, 3, 4, 5),
            file_size=20,
            media_type="photo",
        )
    finally:
        conn.close()

    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {"default_destination": str(destination), "db_name": ".ipb.sqlite3"},
    )
    monkeypatch.setattr(
        cli,
        "resolve_destination",
        lambda cli_destination, default_destination: destination,
    )

    args = argparse.Namespace(destination=None)
    assert cli.cmd_cursor_rebuild(args) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "Rebuilt cursor: last_downloaded_created_at=2026-01-02T03:04:05" in out


def test_cmd_cursor_rebuild_handles_missing_db(tmp_path: Path, monkeypatch) -> None:
    destination = tmp_path / "dest"
    destination.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: {"default_destination": str(destination), "db_name": ".ipb.sqlite3"},
    )
    monkeypatch.setattr(
        cli,
        "resolve_destination",
        lambda cli_destination, default_destination: destination,
    )

    args = argparse.Namespace(destination=None)
    assert cli.cmd_cursor_rebuild(args) == cli.EXIT_STORAGE


def test_cmd_restore_bootstraps_config_and_cursor(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    destination = tmp_path / "dest"
    destination.mkdir(parents=True, exist_ok=True)
    db_path = destination / ".ipb.sqlite3"
    conn = init_db(db_path)
    try:
        mark_downloaded(
            conn,
            asset_id="id-restore-1",
            filename="IMG_1234.HEIC",
            local_path=destination / "2026" / "02" / "IMG_1234.HEIC",
            created_at=dt.datetime(2026, 2, 3, 4, 5, 6),
            file_size=100,
            media_type="photo",
        )
    finally:
        conn.close()

    config_path = tmp_path / "config.json"
    saved_cfg: dict = {}

    monkeypatch.setattr(cli, "config_file_path", lambda: config_path)
    monkeypatch.setattr(cli, "ensure_config_layout", lambda: None)
    monkeypatch.setattr(cli, "validate_target_dir", lambda destination: None)
    monkeypatch.setattr(
        cli,
        "save_config",
        lambda cfg: saved_cfg.update(cfg) or config_path,
    )
    monkeypatch.setattr(
        cli,
        "set_credentials",
        lambda cfg, *, username, password, use_keychain: {
            **cfg,
            "icloud_username": username,
            "icloud_password": password,
            "use_keychain": use_keychain,
        },
    )

    inputs = iter(["me@example.com", "y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "secret")

    args = argparse.Namespace(destination=destination)
    assert cli.cmd_restore(args) == cli.EXIT_OK

    assert saved_cfg["default_destination"] == str(destination)
    assert saved_cfg["icloud_username"] == "me@example.com"
    out = capsys.readouterr().out
    assert "Restored cursor: last_downloaded_created_at=2026-02-03T04:05:06" in out


def test_cmd_restore_fails_when_backup_manifest_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    destination = tmp_path / "dest"
    destination.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cli, "config_file_path", lambda: tmp_path / "config.json")
    monkeypatch.setattr(cli, "ensure_config_layout", lambda: None)
    monkeypatch.setattr(cli, "validate_target_dir", lambda destination: None)

    args = argparse.Namespace(destination=destination)
    assert cli.cmd_restore(args) == cli.EXIT_STORAGE
