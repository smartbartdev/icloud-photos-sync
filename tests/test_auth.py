import logging

import pytest

from icloud_photo_backup import auth
from icloud_photo_backup.errors import AuthError


def test_load_pyicloud_module_uses_primary_name(monkeypatch) -> None:
    class _Module:
        __name__ = "pyicloud"

    monkeypatch.setattr(auth.importlib, "import_module", lambda name: _Module())
    module = auth.load_pyicloud_module()
    assert module.__name__ == "pyicloud"


def test_load_pyicloud_module_falls_back_to_pyicloud_ipd(monkeypatch) -> None:
    class _FallbackModule:
        __name__ = "pyicloud_ipd"

    def _import_module(name: str):
        if name == "pyicloud":
            raise ModuleNotFoundError("pyicloud")
        if name == "pyicloud_ipd":
            return _FallbackModule()
        raise ImportError(name)

    monkeypatch.setattr(auth.importlib, "import_module", _import_module)
    module = auth.load_pyicloud_module()
    assert module.__name__ == "pyicloud_ipd"


def test_login_icloud_reports_brew_reinstall_hint(monkeypatch) -> None:
    logger = logging.getLogger("test")
    monkeypatch.setattr(auth, "load_pyicloud_module", lambda: (_ for _ in ()).throw(AuthError("broken")))

    with pytest.raises(AuthError) as exc_info:
        auth.login_icloud("me@example.com", "secret", logger)

    assert "brew reinstall smartbartdev/tap/ipb" in str(exc_info.value)


def test_login_icloud_2fa_can_request_code_from_trusted_device(monkeypatch) -> None:
    logger = logging.getLogger("test")

    class _Api:
        requires_2fa = True
        is_trusted_session = True
        trusted_devices = [{"deviceName": "MacBook Pro", "id": "dev-1"}]

        def send_verification_code(self, device):
            return device["id"] == "dev-1"

        def validate_verification_code(self, device, code: str):
            return device["id"] == "dev-1" and code == "123456"

    class _Module:
        class PyiCloudService:  # noqa: D106
            def __new__(cls, username: str, password: str):
                return _Api()

    monkeypatch.setattr(auth, "load_pyicloud_module", lambda: _Module())
    inputs = iter(["", "1", "123456"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    api = auth.login_icloud("me@example.com", "secret", logger)
    assert isinstance(api, _Api)


def test_login_icloud_2fa_invalid_device_selection_fails(monkeypatch) -> None:
    logger = logging.getLogger("test")

    class _Api:
        requires_2fa = True
        is_trusted_session = True
        trusted_devices = [{"deviceName": "MacBook Pro", "id": "dev-1"}]

        def send_verification_code(self, device):
            return True

        def validate_verification_code(self, device, code: str):
            return True

    class _Module:
        class PyiCloudService:  # noqa: D106
            def __new__(cls, username: str, password: str):
                return _Api()

    monkeypatch.setattr(auth, "load_pyicloud_module", lambda: _Module())
    inputs = iter(["", "9"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    with pytest.raises(AuthError) as exc_info:
        auth.login_icloud("me@example.com", "secret", logger)

    assert "out of range" in str(exc_info.value)
