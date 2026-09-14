"""LLM providers behind one small interface: turn free-form game text into `ParsedGameFields`.

The app never talks to a vendor directly; `llm_settings` picks the provider from the admin
settings (or env defaults) and the router only sees `LLMProvider`.
"""
from __future__ import annotations

import json
from typing import Protocol

import httpx
from pydantic import ValidationError

from .models import GameMeta, ParsedGameFields

SYSTEM_PROMPT_TEMPLATE = """You are a data extraction assistant for a drinking games catalog website. You will be
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
  "source": string or null - a URL or reference mentioned in the text, otherwise null,
  "summary": string - one short sentence (max 120 characters, Russian, lower-case start is fine)
    that tells what the game is about, for a list of games; not a copy of the rules,
  "minutes": integer - a realistic estimate of how long one round/session takes, in minutes
    (typical values 5-60; guess if the text does not say),
  "tags": array of 1-3 strings, ONLY from this list: {tags},
  "props": string - what players need to bring, comma-separated, lower-case, e.g.
    "колода карт, стаканы"; use "ничего не нужно" when only drinks are required
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
- Always return valid JSON matching exactly this shape, with exactly these 9 keys.
- min_players must be an integer >= 1.
- If player count is not mentioned at all, use min_players=1, max_players=null as a safe
  default; still make a best-effort guess for name/description.
- Do not wrap the JSON in markdown code fences or add any explanatory text outside the JSON.
"""

# Tags are a closed vocabulary so the catalogue stays filterable and consistent.
TAGS = (
    "разговорная",
    "карты",
    "кубики",
    "монеты",
    "реквизит",
    "без реквизита",
    "активная",
    "команды",
    "роли",
    "на внимание",
    "на память",
    "на ловкость",
    "быстрая",
    "долгая",
    "на двоих",
    "большая компания",
    "жёсткая",
)
_TAGS_LIST = ", ".join(f'"{t}"' for t in TAGS)
SYSTEM_PROMPT = SYSTEM_PROMPT_TEMPLATE.replace("{tags}", _TAGS_LIST)

ENRICH_PROMPT = """You are a data extraction assistant for a drinking games catalog website. You will be
given the name and the full rules of a drinking game (in Russian or English). Do NOT rewrite the
rules. Return ONLY a single JSON object with exactly these 4 keys, no commentary, no code fences:

{
  "summary": string - one short sentence (max 120 characters, in the language of the rules)
    that tells what the game is about, for a list of games; not a copy of the rules,
  "minutes": integer - a realistic estimate of how long one round/session takes, in minutes
    (typical values 5-60; guess if the text does not say),
  "tags": array of 1-3 strings, ONLY from this list: {tags},
  "props": string - what players need to bring, comma-separated, lower-case, e.g.
    "колода карт, стаканы"; use "ничего не нужно" when only drinks are required
}
""".replace("{tags}", _TAGS_LIST)


def _enrich_user_text(name: str, description: str, min_players: int, max_players: int | None) -> str:
    players = f"{min_players}+" if max_players is None else f"{min_players}-{max_players}"
    return f"Название: {name}\nИгроки: {players}\n\nПравила:\n{description}"


# Short, deterministic sample used by the admin "Проверить" button: a real round trip
# through the vendor without spending many tokens.
CHECK_TEXT = (
    "Игра «Проверка связи». Для 2-4 игроков. Правила: игроки по очереди называют число "
    "от 1 до 10; кто назвал самое большое, делает глоток."
)

REQUEST_TIMEOUT = 60.0


class LLMError(Exception):
    """kind: not_configured | auth | quota | network | bad_response | refused."""

    def __init__(
        self,
        message: str,
        status_code: int = 502,
        kind: str = "bad_response",
        provider: str = "",
        model: str = "",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.kind = kind
        self.provider = provider
        self.model = model


class LLMProvider(Protocol):
    name: str
    model: str

    async def complete(self, system: str, user: str) -> str: ...

    async def parse(self, text: str) -> ParsedGameFields: ...

    async def enrich(self, name: str, description: str, min_players: int, max_players: int | None) -> GameMeta: ...

    async def check(self) -> str: ...


class _BaseProvider:
    """Shared parse/enrich/check on top of a vendor-specific `complete`."""

    name = ""
    model = ""

    async def complete(self, system: str, user: str) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    async def parse(self, text: str) -> ParsedGameFields:
        return _to_fields(await self.complete(SYSTEM_PROMPT, text), self.name, self.model)

    async def enrich(self, name: str, description: str, min_players: int, max_players: int | None) -> GameMeta:
        user = _enrich_user_text(name, description, min_players, max_players)
        return _to_meta(await self.complete(ENRICH_PROMPT, user), self.name, self.model)

    def _label(self) -> str:
        return self.model

    async def check(self) -> str:
        return _check_result(self._label(), await self.parse(CHECK_TEXT))


def _kind_for_status(status: int) -> str:
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "quota"
    return "bad_response"


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        text = text[first_newline + 1 :] if first_newline != -1 else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _error_message(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:300]
    if isinstance(body, dict):
        msg = body.get("message")
        if not msg and isinstance(body.get("error"), dict):
            msg = body["error"].get("message")
        if not msg and isinstance(body.get("detail"), str):
            msg = body["detail"]
        if msg:
            return str(msg)[:300]
    return resp.text[:300]


def _to_model(raw: str, model_cls, provider: str, model: str):
    text = _strip_fences(raw)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        if not text.startswith("{"):
            # Vendor safety filters answer with prose instead of JSON, e.g. YandexGPT's
            # "Я не могу обсуждать эту тему". Say so, rather than blaming the format.
            raise LLMError(
                f"Модель отказалась обрабатывать этот текст: «{text[:120]}». "
                "Попробуйте другого провайдера или заполните поля вручную.",
                422,
                "refused",
                provider,
                model,
            ) from exc
        raise LLMError("LLM returned invalid JSON", 502, "bad_response", provider, model) from exc
    if not isinstance(parsed, dict):
        raise LLMError("LLM returned invalid JSON", 502, "bad_response", provider, model)
    # Unknown tags are dropped rather than failing the whole answer.
    if isinstance(parsed.get("tags"), list):
        parsed["tags"] = [t for t in parsed["tags"] if isinstance(t, str) and t.strip().lower() in TAGS]
    try:
        return model_cls(**parsed)
    except (ValidationError, TypeError) as exc:
        raise LLMError(
            f"LLM output missing/invalid fields: {exc}", 422, "bad_response", provider, model
        ) from exc


def _to_fields(raw: str, provider: str, model: str) -> ParsedGameFields:
    fields = _to_model(raw, ParsedGameFields, provider, model)
    if fields.max_players is not None and fields.max_players < fields.min_players:
        fields.max_players = fields.min_players
    return fields


def _to_meta(raw: str, provider: str, model: str) -> GameMeta:
    return _to_model(raw, GameMeta, provider, model)


async def _post_json(
    url: str,
    headers: dict[str, str],
    body: dict,
    transport: httpx.AsyncBaseTransport | None,
    provider: str,
    model: str,
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, transport=transport) as client:
            resp = await client.post(url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise LLMError(
            f"Could not reach {provider} API: {type(exc).__name__}: {exc}",
            502,
            "network",
            provider,
            model,
        ) from exc
    if resp.status_code >= 400:
        raise LLMError(
            f"HTTP {resp.status_code}: {_error_message(resp)}",
            502,
            _kind_for_status(resp.status_code),
            provider,
            model,
        )
    try:
        data = resp.json()
    except ValueError as exc:
        raise LLMError("LLM returned invalid JSON", 502, "bad_response", provider, model) from exc
    if not isinstance(data, dict):
        raise LLMError("LLM returned invalid JSON", 502, "bad_response", provider, model)
    return data


def _check_result(model: str, fields: ParsedGameFields) -> str:
    return f"ok: {model} → «{fields.name}»"


# ---------------------------------------------------------------------------
# DeepSeek (OpenAI-compatible chat completions)
# ---------------------------------------------------------------------------
class DeepSeekProvider(_BaseProvider):
    name = "deepseek"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._transport = transport

    async def complete(self, system: str, user: str) -> str:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        data = await _post_json(
            f"{self.base_url}/chat/completions",
            {"Authorization": f"Bearer {self.api_key}"},
            body,
            self._transport,
            self.name,
            self.model,
        )
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM returned invalid JSON", 502, "bad_response", self.name, self.model) from exc


# ---------------------------------------------------------------------------
# Yandex Cloud AI Studio (YandexGPT, Text Generation API)
# ---------------------------------------------------------------------------
YANDEX_COMPLETION_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
YANDEX_MAX_TOKENS = 4000  # full rulebooks can be long; the API takes it as a string


class YandexProvider(_BaseProvider):
    name = "yandex"

    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model: str = "yandexgpt-lite/latest",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.folder_id = folder_id
        self.model = model
        self.model_uri = f"gpt://{folder_id}/{model}"
        self._transport = transport

    async def complete(self, system: str, user: str) -> str:
        body = {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": 0.2,
                "maxTokens": str(YANDEX_MAX_TOKENS),
            },
            "messages": [
                {"role": "system", "text": system},
                {"role": "user", "text": user},
            ],
            # Generic JSON mode: ParsedGameFields has nullable ints (anyOf in JSON Schema),
            # which the strict jsonSchema mode may reject. Validation happens on our side.
            "jsonObject": True,
        }
        data = await _post_json(
            YANDEX_COMPLETION_URL,
            {"Authorization": f"Api-Key {self.api_key}"},
            body,
            self._transport,
            self.name,
            self.model,
        )
        try:
            return str(data["result"]["alternatives"][0]["message"]["text"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM returned invalid JSON", 502, "bad_response", self.name, self.model) from exc

    def _label(self) -> str:
        return self.model_uri
