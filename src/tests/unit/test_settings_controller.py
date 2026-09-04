from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.controllers.settings_controller import router
from config import settings

_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)


def test_get_fixed_tools_enabled_reports_current_state(monkeypatch):
    monkeypatch.setattr(settings, "_fixed_tools_enabled", True)

    response = client.get("/settings/fixed-tools-enabled")

    assert response.status_code == 200
    assert response.json() == {"fixed_tools_enabled": True}


def test_put_fixed_tools_enabled_flips_the_runtime_setting(monkeypatch):
    monkeypatch.setattr(settings, "_fixed_tools_enabled", True)

    response = client.put("/settings/fixed-tools-enabled", json={"fixed_tools_enabled": False})

    assert response.status_code == 200
    assert response.json() == {"fixed_tools_enabled": False}
    assert settings.is_fixed_tools_enabled() is False
