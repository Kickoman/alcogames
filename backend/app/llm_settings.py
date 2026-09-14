"""Which LLM provider is active and its credentials: admin-editable, stored in
`data/llm_settings.json`, env values as defaults.

The file holds only overrides, so a field that was never saved keeps following the
environment. It contains API keys, hence mode 0600.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Literal

from pydantic import BaseModel

from .config import settings
from . import llm_providers as providers

ProviderName = Literal["none", "deepseek", "yandex"]
PROVIDER_NAMES: tuple[str, ...] = ("none", "deepseek", "yandex")
SECRET_FIELDS = ("deepseek_api_key", "yandex_api_key")


class LLMSettings(BaseModel):
    provider: ProviderName = "none"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    yandex_api_key: str = ""
    yandex_folder_id: str = ""
    yandex_model: str = "yandexgpt-lite/latest"

    def ready(self) -> bool:
        if self.provider == "deepseek":
            return bool(self.deepseek_api_key)
        if self.provider == "yandex":
            return bool(self.yandex_api_key and self.yandex_folder_id)
        return False

    def active_model(self) -> str:
        if self.provider == "deepseek":
            return self.deepseek_model
        if self.provider == "yandex":
            return self.yandex_model
        return ""


def env_defaults() -> LLMSettings:
    provider = (settings.LLM_PROVIDER or "").strip().lower()
    if provider not in PROVIDER_NAMES:
        # Installations that predate provider settings only had DEEPSEEK_API_KEY;
        # keep them working without touching .env.
        provider = "deepseek" if settings.DEEPSEEK_API_KEY else "none"
    return LLMSettings(
        provider=provider,  # type: ignore[arg-type]
        deepseek_api_key=settings.DEEPSEEK_API_KEY or "",
        deepseek_base_url=settings.DEEPSEEK_BASE_URL,
        deepseek_model=settings.DEEPSEEK_MODEL,
        yandex_api_key=settings.YANDEX_API_KEY or "",
        yandex_folder_id=settings.YANDEX_FOLDER_ID or "",
        yandex_model=settings.YANDEX_MODEL,
    )


_lock = threading.Lock()
_cache: LLMSettings | None = None


def _read_overrides() -> dict:
    path = settings.LLM_SETTINGS_FILE
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _atomic_write(overrides: dict) -> None:
    path = settings.LLM_SETTINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(overrides, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
    os.chmod(path, 0o600)


def _merge(overrides: dict) -> LLMSettings:
    values = env_defaults().model_dump()
    for key, value in overrides.items():
        if key in values and isinstance(value, str):
            values[key] = value
    if values["provider"] not in PROVIDER_NAMES:
        values["provider"] = "none"
    return LLMSettings.model_validate(values)


def get_llm_settings() -> LLMSettings:
    global _cache
    with _lock:
        if _cache is None:
            _cache = _merge(_read_overrides())
        return _cache


def invalidate() -> None:
    global _cache
    with _lock:
        _cache = None


def save(changes: dict[str, str | None]) -> LLMSettings:
    """Persist changed fields. For secrets: "" means keep, None means clear."""
    with _lock:
        overrides = _read_overrides()
        for field, value in changes.items():
            if field not in LLMSettings.model_fields:
                continue
            if field in SECRET_FIELDS and value == "":
                continue
            overrides[field] = "" if value is None else str(value).strip()
        _atomic_write(overrides)
    invalidate()
    return get_llm_settings()


def get_provider(s: LLMSettings | None = None) -> providers.LLMProvider | None:
    s = s or get_llm_settings()
    if not s.ready():
        return None
    if s.provider == "deepseek":
        return providers.DeepSeekProvider(s.deepseek_api_key, s.deepseek_base_url, s.deepseek_model)
    return providers.YandexProvider(s.yandex_api_key, s.yandex_folder_id, s.yandex_model)
