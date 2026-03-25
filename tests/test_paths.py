from pathlib import Path

from icloud_photo_backup.paths import build_output_dir, resolve_destination, unique_path


def test_unique_path_collision(tmp_path: Path) -> None:
    existing = tmp_path / "IMG_1234.JPG"
    existing.write_bytes(b"x")
    result = unique_path(existing)
    assert result.name == "IMG_1234_1.JPG"


def test_build_output_dir_unknown_date(tmp_path: Path) -> None:
    assert build_output_dir(tmp_path, None) == tmp_path / "unknown_date"


def test_resolve_destination_uses_cwd_when_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert resolve_destination(None, None) == tmp_path
