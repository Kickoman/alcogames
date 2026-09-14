import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.ADMIN_TOKEN: str | None = os.environ.get("ADMIN_TOKEN")

        # LLM provider settings. All of these are only *defaults*: the live
        # configuration is edited in the admin panel and stored in
        # LLM_SETTINGS_FILE (see llm_settings.py).
        self.LLM_PROVIDER: str | None = os.environ.get("LLM_PROVIDER")
        self.DEEPSEEK_API_KEY: str | None = os.environ.get("DEEPSEEK_API_KEY")
        self.DEEPSEEK_BASE_URL: str = os.environ.get(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
        )
        self.DEEPSEEK_MODEL: str = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        self.YANDEX_API_KEY: str | None = os.environ.get("YANDEX_API_KEY")
        self.YANDEX_FOLDER_ID: str | None = os.environ.get("YANDEX_FOLDER_ID")
        self.YANDEX_MODEL: str = os.environ.get("YANDEX_MODEL", "yandexgpt-lite/latest")

        self.DATA_DIR: Path = Path(os.environ.get("DATA_DIR", "./data")).resolve()
        self.GAMES_FILE: Path = self.DATA_DIR / "games.json"
        self.LLM_SETTINGS_FILE: Path = self.DATA_DIR / "llm_settings.json"

        project_root = Path(__file__).resolve().parent.parent.parent
        self.FRONTEND_DIR: Path = Path(
            os.environ.get("FRONTEND_DIR", str(project_root / "frontend"))
        ).resolve()


settings = Settings()
