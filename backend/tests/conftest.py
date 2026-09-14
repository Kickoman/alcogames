import os

os.environ.setdefault("ADMIN_TOKEN", "test-token")

import pytest

from app import llm_settings
from app.config import settings


@pytest.fixture
def llm_env(tmp_path, monkeypatch):
    """Isolated settings file and no provider env defaults."""
    monkeypatch.setattr(settings, "LLM_SETTINGS_FILE", tmp_path / "llm_settings.json")
    monkeypatch.setattr(settings, "LLM_PROVIDER", None)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", None)
    monkeypatch.setattr(settings, "YANDEX_API_KEY", None)
    monkeypatch.setattr(settings, "YANDEX_FOLDER_ID", None)
    llm_settings.invalidate()
    yield settings
    llm_settings.invalidate()
