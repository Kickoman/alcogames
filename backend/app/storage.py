import json
import os
import threading
import uuid
from datetime import datetime, timezone

from .config import settings
from .models import Game, GameCreate, GameUpdate

_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_file() -> None:
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not settings.GAMES_FILE.exists():
        _atomic_write([])


def _read_all() -> list[dict]:
    _ensure_file()
    with open(settings.GAMES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _atomic_write(games: list[dict]) -> None:
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = settings.GAMES_FILE.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, settings.GAMES_FILE)


def get_all_games() -> list[Game]:
    with _lock:
        return [Game(**g) for g in _read_all()]


def create_game(data: GameCreate) -> Game:
    with _lock:
        games = _read_all()
        game = Game(
            id=uuid.uuid4().hex,
            date_added=_now_iso(),
            likes=0,
            **data.model_dump(),
        )
        games.append(game.model_dump())
        _atomic_write(games)
        return game


def update_game(game_id: str, data: GameUpdate) -> Game | None:
    with _lock:
        games = _read_all()
        for i, g in enumerate(games):
            if g["id"] == game_id:
                updated = Game(
                    id=g["id"],
                    date_added=g["date_added"],
                    likes=g["likes"],
                    **data.model_dump(),
                )
                games[i] = updated.model_dump()
                _atomic_write(games)
                return updated
        return None


def delete_game(game_id: str) -> bool:
    with _lock:
        games = _read_all()
        remaining = [g for g in games if g["id"] != game_id]
        if len(remaining) == len(games):
            return False
        _atomic_write(remaining)
        return True


def like_game(game_id: str) -> Game | None:
    with _lock:
        games = _read_all()
        for i, g in enumerate(games):
            if g["id"] == game_id:
                g["likes"] += 1
                games[i] = g
                _atomic_write(games)
                return Game(**g)
        return None


def get_game(game_id: str) -> Game | None:
    with _lock:
        for g in _read_all():
            if g["id"] == game_id:
                return Game(**g)
        return None
