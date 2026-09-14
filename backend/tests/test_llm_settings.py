import json
import os

from app import llm_settings
from app.llm_providers import DeepSeekProvider, YandexProvider


def test_env_defaults_deepseek_when_only_key_set(llm_env):
    llm_env.DEEPSEEK_API_KEY = "sk-old"
    s = llm_settings.get_llm_settings()
    assert s.provider == "deepseek"
    assert s.ready()
    assert s.active_model() == "deepseek-chat"


def test_env_defaults_none_without_key(llm_env):
    s = llm_settings.get_llm_settings()
    assert s.provider == "none"
    assert not s.ready()
    assert llm_settings.get_provider(s) is None


def test_env_provider_explicit(llm_env):
    llm_env.LLM_PROVIDER = "yandex"
    llm_env.YANDEX_API_KEY = "yk"
    llm_env.YANDEX_FOLDER_ID = "b1g"
    s = llm_settings.get_llm_settings()
    assert s.provider == "yandex" and s.ready()
    assert isinstance(llm_settings.get_provider(s), YandexProvider)


def test_save_persists_with_0600(llm_env):
    s = llm_settings.save({"provider": "yandex", "yandex_api_key": " yk ", "yandex_folder_id": "b1g", "bogus": "x"})
    assert s.provider == "yandex" and s.yandex_api_key == "yk" and s.ready()
    path = llm_env.LLM_SETTINGS_FILE
    assert oct(os.stat(path).st_mode & 0o777) == "0o600"
    data = json.loads(path.read_text())
    assert data == {"provider": "yandex", "yandex_api_key": "yk", "yandex_folder_id": "b1g"}


def test_secret_empty_keeps_none_clears(llm_env):
    llm_settings.save({"provider": "deepseek", "deepseek_api_key": "sk-1"})
    assert llm_settings.save({"deepseek_api_key": ""}).deepseek_api_key == "sk-1"
    s = llm_settings.save({"deepseek_api_key": None})
    assert s.deepseek_api_key == "" and not s.ready()


def test_overrides_beat_env_and_cache_is_invalidated(llm_env):
    llm_env.DEEPSEEK_API_KEY = "sk-env"
    assert llm_settings.get_llm_settings().provider == "deepseek"
    llm_settings.save({"provider": "none"})
    s = llm_settings.get_llm_settings()
    assert s.provider == "none"
    assert s.deepseek_api_key == "sk-env"  # unset override keeps following env


def test_get_provider_classes(llm_env):
    llm_settings.save({"provider": "deepseek", "deepseek_api_key": "sk"})
    assert isinstance(llm_settings.get_provider(), DeepSeekProvider)
    llm_settings.save({"provider": "yandex"})
    assert llm_settings.get_provider() is None  # yandex not configured yet


def test_ignores_garbage_provider_in_file(llm_env):
    llm_env.LLM_SETTINGS_FILE.write_text(json.dumps({"provider": "openai"}))
    assert llm_settings.get_llm_settings().provider == "none"
