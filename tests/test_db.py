import datetime as dt
from pathlib import Path

from icloud_photo_backup.db import (
    get_downloaded_count,
    get_meta,
    init_db,
    is_downloaded,
    mark_downloaded,
    set_meta,
)


def test_meta_roundtrip(tmp_path: Path) -> None:
    conn = init_db(tmp_path / ".ipb.sqlite3")
    try:
        set_meta(conn, "last_sync_at", "2026-01-01T00:00:00+00:00")
        assert get_meta(conn, "last_sync_at") == "2026-01-01T00:00:00+00:00"
    finally:
        conn.close()


def test_mark_downloaded_increments_count(tmp_path: Path) -> None:
    conn = init_db(tmp_path / ".ipb.sqlite3")
    try:
        assert get_downloaded_count(conn) == 0
        assert is_downloaded(conn, "id-1") is False
        mark_downloaded(
            conn,
            asset_id="id-1",
            filename="IMG_1.HEIC",
            local_path=tmp_path / "2024" / "01" / "IMG_1.HEIC",
            created_at=dt.datetime(2024, 1, 1),
            file_size=10,
            media_type="photo",
        )
        assert is_downloaded(conn, "id-1") is True
        assert get_downloaded_count(conn) == 1
    finally:
        conn.close()
