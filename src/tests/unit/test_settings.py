from config import settings


def test_set_fixed_tools_enabled_is_reflected_by_is_fixed_tools_enabled(monkeypatch):
    monkeypatch.setattr(settings, "_fixed_tools_enabled", True)

    settings.set_fixed_tools_enabled(False)

    assert settings.is_fixed_tools_enabled() is False


def test_set_fixed_tools_enabled_can_be_flipped_back_on(monkeypatch):
    monkeypatch.setattr(settings, "_fixed_tools_enabled", False)

    settings.set_fixed_tools_enabled(True)

    assert settings.is_fixed_tools_enabled() is True
