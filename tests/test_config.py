from pathlib import Path

from icloud_photo_backup.config import load_config, redact_config, save_config


def test_save_and_load_config(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    written = {
        "icloud_username": "me@example.com",
        "icloud_password": "secret",
        "use_keychain": False,
    }
    save_config(written, path=cfg_path)

    loaded = load_config(path=cfg_path)
    assert loaded["icloud_username"] == "me@example.com"
    assert loaded["icloud_password"] == "secret"


def test_redact_config_hides_password() -> None:
    redacted = redact_config({"icloud_password": "secret"})
    assert redacted["icloud_password"] == "********"
