from fastapi import APIRouter, Depends, HTTPException

from ..deps import require_admin_token
from ..llm_client import LLMError, parse_game_text
from ..models import ParsedGameFields, ParseRequest

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
)


@router.post("/parse", response_model=ParsedGameFields)
async def parse(data: ParseRequest) -> ParsedGameFields:
    try:
        return await parse_game_text(data.text)
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
