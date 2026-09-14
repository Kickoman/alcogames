import time

from fastapi import APIRouter, Depends, HTTPException

from .. import llm_settings, storage
from ..deps import require_admin_token
from ..llm_client import LLMError, enrich_game, parse_game_text
from ..logging_setup import get_logger
from ..models import Game, LLMSettingsIn, LLMSettingsOut, LLMTestOut, ParsedGameFields, ParseRequest

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
)
log = get_logger(stream="internal")


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


def _log_failure(op: str, exc: LLMError, started: float, **extra) -> None:
    current = llm_settings.get_llm_settings()
    log.error(
        "llm_parse_failed",
        op=op,
        duration_ms=_elapsed_ms(started),
        status_code=exc.status_code,
        kind=exc.kind,
        provider=exc.provider or current.provider,
        model=exc.model or current.active_model(),
        error=exc.message,
        **extra,
    )


@router.post("/parse", response_model=ParsedGameFields)
async def parse(data: ParseRequest) -> ParsedGameFields:
    # Calls out to an external API, so it is the slowest and flakiest thing
    # here -- worth its own event with a duration.
    current = llm_settings.get_llm_settings()
    started = time.perf_counter()
    try:
        fields = await parse_game_text(data.text)
    except LLMError as exc:
        _log_failure("parse", exc, started, text_len=len(data.text))
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    # Input text can be a whole scraped page; only its size is logged.
    log.info(
        "llm_parsed",
        op="parse",
        text_len=len(data.text),
        duration_ms=_elapsed_ms(started),
        provider=current.provider,
        model=current.active_model(),
        name=fields.name,
        description_len=len(fields.description),
        tags=",".join(fields.tags),
        minutes=fields.minutes,
    )
    return fields


@router.post("/games/{game_id}/enrich", response_model=Game)
async def enrich(game_id: str) -> Game:
    """Fill summary, minutes, tags and props for a stored game via the LLM and save them."""
    game = storage.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    current = llm_settings.get_llm_settings()
    started = time.perf_counter()
    try:
        meta = await enrich_game(game)
    except LLMError as exc:
        _log_failure("enrich", exc, started, game_id=game.id, text_len=len(game.description))
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    updated = storage.patch_game(game.id, meta.model_dump())
    if updated is None:  # deleted while we waited for the model
        raise HTTPException(status_code=404, detail="Game not found")
    log.info(
        "llm_parsed",
        op="enrich",
        game_id=game.id,
        name=game.name,
        text_len=len(game.description),
        duration_ms=_elapsed_ms(started),
        provider=current.provider,
        model=current.active_model(),
        tags=",".join(updated.tags),
        minutes=updated.minutes,
    )
    return updated


# ---- provider settings ----
def _tail(secret: str) -> str:
    return secret[-4:] if secret else ""


def _settings_out(s: llm_settings.LLMSettings) -> LLMSettingsOut:
    return LLMSettingsOut(
        provider=s.provider,
        ready=s.ready(),
        model=s.active_model(),
        deepseek_key_tail=_tail(s.deepseek_api_key),
        deepseek_base_url=s.deepseek_base_url,
        deepseek_model=s.deepseek_model,
        yandex_key_tail=_tail(s.yandex_api_key),
        yandex_folder_id=s.yandex_folder_id,
        yandex_model=s.yandex_model,
    )


@router.get("/llm-settings", response_model=LLMSettingsOut)
def get_llm_settings_view() -> LLMSettingsOut:
    return _settings_out(llm_settings.get_llm_settings())


@router.put("/llm-settings", response_model=LLMSettingsOut)
def update_llm_settings(payload: LLMSettingsIn) -> LLMSettingsOut:
    changes: dict[str, str | None] = {}
    for field in ("provider", "deepseek_base_url", "deepseek_model", "yandex_folder_id", "yandex_model"):
        value = getattr(payload, field)
        if value is not None:
            changes[field] = value
    for field in llm_settings.SECRET_FIELDS:
        if getattr(payload, f"clear_{field}"):
            changes[field] = None
        elif getattr(payload, field):
            changes[field] = getattr(payload, field)
    s = llm_settings.save(changes)
    # Only field *names* are logged: values include API keys.
    log.info(
        "llm_settings_updated",
        fields=",".join(sorted(changes)),
        provider=s.provider,
        model=s.active_model(),
        ready=s.ready(),
    )
    return _settings_out(s)


@router.post("/llm-settings/test", response_model=LLMTestOut)
async def test_llm_settings() -> LLMTestOut:
    s = llm_settings.get_llm_settings()
    provider = llm_settings.get_provider(s)
    if provider is None:
        log.warning("llm_settings_tested", ok=False, provider=s.provider, model=s.active_model(), kind="not_configured")
        return LLMTestOut(ok=False, detail="not_configured", provider=s.provider, model=s.active_model())
    started = time.perf_counter()
    try:
        detail = await provider.check()
    except LLMError as exc:
        log.warning(
            "llm_settings_tested",
            ok=False,
            provider=provider.name,
            model=provider.model,
            duration_ms=_elapsed_ms(started),
            kind=exc.kind,
            error=exc.message,
        )
        return LLMTestOut(ok=False, detail=f"{exc.kind}: {exc.message}", provider=provider.name, model=provider.model)
    log.info(
        "llm_settings_tested",
        ok=True,
        provider=provider.name,
        model=provider.model,
        duration_ms=_elapsed_ms(started),
    )
    return LLMTestOut(ok=True, detail=detail, provider=provider.name, model=provider.model)
