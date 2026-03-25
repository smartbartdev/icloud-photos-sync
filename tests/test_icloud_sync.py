import datetime as dt
from pathlib import Path

from icloud_sync import build_output_dir, init_db, is_downloaded, mark_downloaded, unique_path


def test_unique_path_returns_original_when_unused(tmp_path: Path) -> None:
    candidate = tmp_path / "IMG_1001.JPG"
    assert unique_path(candidate) == candidate


def test_unique_path_appends_suffix_for_collisions(tmp_path: Path) -> None:
    base = tmp_path / "IMG_1001.JPG"
    base.write_bytes(b"x")
    (tmp_path / "IMG_1001_1.JPG").write_bytes(b"x")

    result = unique_path(base)
    assert result.name == "IMG_1001_2.JPG"


def test_build_output_dir_uses_year_month(tmp_path: Path) -> None:
    created = dt.datetime(2024, 11, 5, 8, 30, 0)
    out = build_output_dir(tmp_path, created)
    assert out == tmp_path / "2024" / "11"


def test_build_output_dir_unknown_date(tmp_path: Path) -> None:
    out = build_output_dir(tmp_path, None)
    assert out == tmp_path / "unknown_date"


def test_db_insert_and_lookup(tmp_path: Path) -> None:
    db_path = tmp_path / ".icloud_sync.sqlite3"
    conn = init_db(db_path)

    try:
        assert is_downloaded(conn, "asset-1") is False

        destination_file = tmp_path / "2024" / "11" / "IMG_2002.HEIC"
        mark_downloaded(
            conn,
            asset_id="asset-1",
            filename="IMG_2002.HEIC",
            local_path=destination_file,
            created_at=dt.datetime(2024, 11, 5, 8, 30, 0),
            file_size=1234,
        )

        assert is_downloaded(conn, "asset-1") is True
    finally:
        conn.close()
