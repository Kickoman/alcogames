import json

import httpx
from pydantic import ValidationError

from .config import settings
from .models import ParsedGameFields

SYSTEM_PROMPT = """You are a data extraction assistant for a drinking games catalog website. You will be
given free-form, possibly messy text describing a drinking game (in Russian or English).
Extract the following fields and return ONLY a single JSON object, no extra commentary,
no markdown code fences:

{
  "name": string - the game's name,
  "min_players": integer - minimum number of players required (if the text gives an exact
    number, min and max are equal; if it says "N or more" / "N+", min=N; if the text says
    the game works for any number of players, use 1),
  "max_players": integer or null - maximum number of players (null means "no upper limit",
    use this for "any number of players" or "N or more" descriptions),
  "description": string - the FULL rules of the game, in the same language as the input text,
  "source": string or null - a URL or reference mentioned in the text, otherwise null
}

Rules for "description" - this is the most important part, read carefully:
- Do NOT summarize or shorten the rules. Do NOT compress a detailed rule list into a short
  generic paragraph. The goal is a complete, usable rulebook a player could follow without
  having read the original text - not a blurb or teaser.
- Keep every rule, every enumerated case (e.g. "if you roll a 2, then...", every item of a
  list of actions/penalties/exceptions), every required prop/item, and every special
  condition or exception from the source text. If the source lists outcomes for dice rolls,
  cards, or turns, reproduce each one individually - do not group or generalize them.
- You MAY fix spelling/grammar, remove duplication, and reformat for clarity (e.g. using
  line breaks or a numbered/bulleted list) - but the informational content must be
  preserved in full. When in doubt, keep more detail rather than less.
- Only omit text that is truly not a rule (site navigation, ads, unrelated comments).

Other rules:
- Always return valid JSON matching exactly this shape, with exactly these 5 keys.
- min_players must be an integer >= 1.
- If player count is not mentioned at all, use min_players=1, max_players=null as a safe
  default; still make a best-effort guess for name/description.
- Do not wrap the JSON in markdown code fences or add any explanatory text outside the JSON.
"""


class LLMError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def parse_game_text(text: str) -> ParsedGameFields:
    if not settings.DEEPSEEK_API_KEY:
        raise LLMError("LLM parsing is not configured on this server", status_code=503)

    url = f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach DeepSeek API: {exc}", status_code=502) from exc

    try:
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise LLMError("LLM returned invalid JSON", status_code=502) from exc

    try:
        fields = ParsedGameFields(**parsed)
    except ValidationError as exc:
        raise LLMError(f"LLM output missing/invalid fields: {exc}", status_code=422) from exc

    if fields.max_players is not None and fields.max_players < fields.min_players:
        fields.max_players = fields.min_players

    return fields
