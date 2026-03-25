from __future__ import annotations

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
