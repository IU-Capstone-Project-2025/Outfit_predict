from app.core.config import settings


def test_settings_env(monkeypatch):
    monkeypatch.setenv("ENV_TEST_VAR", "test")
    assert settings.ENV_TEST_VAR == "test"
