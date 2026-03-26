from __future__ import annotations

import datetime as dt

from icloud_photo_backup import sync


class _FakeStdout:
    def __init__(self, *, tty: bool) -> None:
        self._tty = tty
        self.buffer = ""

    def isatty(self) -> bool:
        return self._tty

    def write(self, text: str) -> int:
        self.buffer += text
        return len(text)

    def flush(self) -> None:
        return None


def test_live_progress_disabled_when_not_tty(monkeypatch) -> None:
    fake_stdout = _FakeStdout(tty=False)
    monkeypatch.setattr(sync.sys, "stdout", fake_stdout)

    progress = sync.LiveSyncProgress(enabled=True)
    progress.render(downloaded_bytes=1024, photos=1, videos=0, skipped=0, failed=0)

    assert fake_stdout.buffer == ""


def test_live_progress_downloaded_bytes_do_not_decrease(monkeypatch) -> None:
    fake_stdout = _FakeStdout(tty=True)
    monkeypatch.setattr(sync.sys, "stdout", fake_stdout)

    progress = sync.LiveSyncProgress(enabled=True)
    progress.render(downloaded_bytes=2048, photos=1, videos=0, skipped=0, failed=0)
    progress.render(downloaded_bytes=1024, photos=1, videos=0, skipped=0, failed=0)

    assert "Downloaded: 2.0 KB" in fake_stdout.buffer
    assert "Downloaded: 1.0 KB" not in fake_stdout.buffer


def test_live_scan_progress_renders_when_tty(monkeypatch) -> None:
    fake_stdout = _FakeStdout(tty=True)
    monkeypatch.setattr(sync.sys, "stdout", fake_stdout)

    progress = sync.LiveScanProgress(enabled=True)
    progress.render(scanned=10, matched=3, cursor=None, force=True)

    assert "Scanning: 10 seen / 3 candidates" in fake_stdout.buffer


def test_effective_after_datetime_prefers_user_after_date() -> None:
    result = sync.effective_after_datetime(
        dt.date(2026, 3, 1),
        "2020-01-01T00:00:00+00:00",
    )
    assert result == dt.datetime(2026, 3, 1, 0, 0, 0)


def test_effective_after_datetime_uses_stored_cursor_when_no_user_after() -> None:
    result = sync.effective_after_datetime(None, "2026-03-01T12:34:56+00:00")
    assert result == dt.datetime(2026, 3, 1, 12, 34, 56, tzinfo=dt.timezone.utc)


class _FakeAsset:
    def __init__(self, created: dt.datetime, filename: str) -> None:
        self.created = created
        self.filename = filename


class _FakeDirection:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeAlbum:
    def __init__(self, assets, direction_value: str = "ASCENDING") -> None:
        self._assets = assets
        self._direction = _FakeDirection(direction_value)

    def __iter__(self):
        return iter(self._assets)


class _FakePhotos:
    def __init__(self, album):
        self.all = album


class _FakeApi:
    def __init__(self, album):
        self.photos = _FakePhotos(album)


def test_iter_assets_respects_after_datetime() -> None:
    assets = [
        _FakeAsset(dt.datetime(2026, 3, 1, 10, 0, 0), "old.jpg"),
        _FakeAsset(dt.datetime(2026, 3, 1, 12, 0, 0), "new.jpg"),
    ]
    api = _FakeApi(_FakeAlbum(assets, "ASCENDING"))

    result = list(
        sync.iter_assets(
            api,
            after=dt.datetime(2026, 3, 1, 11, 0, 0),
            skip_videos=False,
        )
    )
    assert [asset.filename for asset in result] == ["new.jpg"]


def test_iter_assets_skips_missing_created_at_by_default() -> None:
    assets = [
        _FakeAsset(dt.datetime(2026, 3, 1, 12, 0, 0), "dated.jpg"),
        _FakeAsset(None, "unknown.jpg"),  # type: ignore[arg-type]
    ]
    api = _FakeApi(_FakeAlbum(assets, "ASCENDING"))

    result = list(
        sync.iter_assets(
            api,
            after=dt.datetime(2026, 3, 1, 0, 0, 0),
            skip_videos=False,
        )
    )
    assert [asset.filename for asset in result] == ["dated.jpg"]


def test_iter_assets_can_include_missing_created_at_with_flag() -> None:
    assets = [
        _FakeAsset(dt.datetime(2026, 3, 1, 12, 0, 0), "dated.jpg"),
        _FakeAsset(None, "unknown.jpg"),  # type: ignore[arg-type]
    ]
    api = _FakeApi(_FakeAlbum(assets, "ASCENDING"))

    result = list(
        sync.iter_assets(
            api,
            after=dt.datetime(2026, 3, 1, 0, 0, 0),
            skip_videos=False,
            include_missing_created_at=True,
        )
    )
    assert [asset.filename for asset in result] == ["dated.jpg", "unknown.jpg"]


def test_iter_assets_breaks_early_for_descending_album() -> None:
    assets = [
        _FakeAsset(dt.datetime(2026, 3, 2, 9, 0, 0), "recent.jpg"),
        _FakeAsset(dt.datetime(2026, 3, 1, 9, 0, 0), "older.jpg"),
        _FakeAsset(dt.datetime(2026, 3, 3, 9, 0, 0), "should-not-be-reached.jpg"),
    ]
    api = _FakeApi(_FakeAlbum(assets, "DESCENDING"))

    result = list(
        sync.iter_assets(
            api,
            after=dt.datetime(2026, 3, 1, 12, 0, 0),
            skip_videos=False,
        )
    )
    assert [asset.filename for asset in result] == ["recent.jpg"]
