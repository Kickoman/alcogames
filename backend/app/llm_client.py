"""Facade used by the router: picks the configured provider and parses the text."""
from .llm_providers import SYSTEM_PROMPT, LLMError  # noqa: F401  (re-exported)
from . import llm_settings
from .models import Game, GameMeta, ParsedGameFields


def _require_provider():
    s = llm_settings.get_llm_settings()
    provider = llm_settings.get_provider(s)
    if provider is None:
        raise LLMError(
            "LLM parsing is not configured on this server",
            status_code=503,
            kind="not_configured",
            provider=s.provider,
            model=s.active_model(),
        )
    return provider


async def parse_game_text(text: str) -> ParsedGameFields:
    return await _require_provider().parse(text)


async def enrich_game(game: Game) -> GameMeta:
    """Summary, duration, tags and props for an already stored game."""
    return await _require_provider().enrich(game.name, game.description, game.min_players, game.max_players)
