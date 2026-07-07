import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.ADMIN_TOKEN: str | None = os.environ.get("ADMIN_TOKEN")
        self.DEEPSEEK_API_KEY: str | None = os.environ.get("DEEPSEEK_API_KEY")
        self.DEEPSEEK_BASE_URL: str = os.environ.get(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
        )
        self.DEEPSEEK_MODEL: str = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        self.DATA_DIR: Path = Path(os.environ.get("DATA_DIR", "./data")).resolve()
        self.GAMES_FILE: Path = self.DATA_DIR / "games.json"

        project_root = Path(__file__).resolve().parent.parent.parent
        self.FRONTEND_DIR: Path = Path(
            os.environ.get("FRONTEND_DIR", str(project_root / "frontend"))
        ).resolve()


settings = Settings()
