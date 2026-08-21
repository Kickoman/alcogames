import time

from fastapi import APIRouter, Depends, HTTPException

from ..deps import require_admin_token
from ..llm_client import LLMError, parse_game_text
from ..logging_setup import get_logger
from ..models import ParsedGameFields, ParseRequest

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
)
log = get_logger(stream="internal")


@router.post("/parse", response_model=ParsedGameFields)
async def parse(data: ParseRequest) -> ParsedGameFields:
    # Calls out to an external API, so it is the slowest and flakiest thing
    # here -- worth its own event with a duration.
    started = time.perf_counter()
    try:
        fields = await parse_game_text(data.text)
    except LLMError as exc:
        log.error(
            "llm_parse_failed",
            text_len=len(data.text),
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            status_code=exc.status_code,
            error=exc.message,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    # Input text can be a whole scraped page; only its size is logged.
    log.info(
        "llm_parsed",
        text_len=len(data.text),
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        name=fields.name,
        description_len=len(fields.description),
    )
    return fields
