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
