from __future__ import annotations

import datetime as dt
from pathlib import Path

from icloud_photo_backup import sync
from icloud_photo_backup.db import get_meta, init_db


class _FakeLogger:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def info(self, message: str, *args) -> None:  # noqa: ANN002
        return None

    def warning(self, message: str, *args) -> None:  # noqa: ANN002
        self.warnings.append(message % args if args else message)

    def error(self, message: str, *args) -> None:  # noqa: ANN002
        return None


class _FakeAsset:
    def __init__(self, asset_id: str, filename: str, created: dt.datetime) -> None:
        self.id = asset_id
        self.filename = filename
        self.created = created


def _configure_sync_mocks(monkeypatch, assets: list[_FakeAsset], logger: _FakeLogger) -> None:
    monkeypatch.setattr(sync, "validate_target_dir", lambda destination: None)
    monkeypatch.setattr(sync, "setup_logging", lambda app_log_file, verbose: logger)
    monkeypatch.setattr(sync, "login_icloud", lambda username, password, logger: object())
    monkeypatch.setattr(
        sync,
        "iter_assets",
        lambda api, after, skip_videos, include_missing_created_at, on_scan: iter(assets),
    )
    monkeypatch.setattr(
        sync,
        "download_asset",
        lambda asset, output_dir, filename: (output_dir / filename, 123),
    )


def test_run_sync_does_not_move_cursor_when_only_future_dates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    logger = _FakeLogger()
    assets = [
        _FakeAsset(
            asset_id="future-1",
            filename="IMG_FUTURE.HEIC",
            created=dt.datetime(2100, 1, 1, tzinfo=dt.timezone.utc),
        )
    ]
    _configure_sync_mocks(monkeypatch, assets, logger)

    target_dir = tmp_path / "dest"
    db_path = target_dir / ".ipb.sqlite3"
    exit_code = sync.run_sync(
        target_dir=target_dir,
        db_path=db_path,
        dry_run=False,
        limit=None,
        verbose=False,
        after=None,
        skip_videos=False,
        missing_created_at_strategy="skip",
        username="me@example.com",
        password="secret",
        app_log_file=tmp_path / "ipb.log",
    )

    assert exit_code == 0
    conn = init_db(db_path)
    try:
        assert get_meta(conn, "last_downloaded_created_at") is None
    finally:
        conn.close()

    assert any("future timestamp" in warning for warning in logger.warnings)
    assert any("Cursor unchanged" in warning for warning in logger.warnings)


def test_run_sync_cursor_uses_latest_non_future_date(
    tmp_path: Path,
    monkeypatch,
) -> None:
    logger = _FakeLogger()
    assets = [
        _FakeAsset(
            asset_id="future-1",
            filename="IMG_FUTURE.HEIC",
            created=dt.datetime(2100, 1, 1, tzinfo=dt.timezone.utc),
        ),
        _FakeAsset(
            asset_id="normal-1",
            filename="IMG_NORMAL.HEIC",
            created=dt.datetime(2025, 12, 31, 12, 30, tzinfo=dt.timezone.utc),
        ),
    ]
    _configure_sync_mocks(monkeypatch, assets, logger)

    target_dir = tmp_path / "dest"
    db_path = target_dir / ".ipb.sqlite3"
    exit_code = sync.run_sync(
        target_dir=target_dir,
        db_path=db_path,
        dry_run=False,
        limit=None,
        verbose=False,
        after=None,
        skip_videos=False,
        missing_created_at_strategy="skip",
        username="me@example.com",
        password="secret",
        app_log_file=tmp_path / "ipb.log",
    )

    assert exit_code == 0
    conn = init_db(db_path)
    try:
        assert (
            get_meta(conn, "last_downloaded_created_at")
            == "2025-12-31T12:30:00+00:00"
        )
    finally:
        conn.close()
