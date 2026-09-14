import asyncio
import json

import httpx
import pytest

from app.llm_providers import ENRICH_PROMPT, SYSTEM_PROMPT, DeepSeekProvider, LLMError, YandexProvider

GOOD = {"name": "Царь горы", "min_players": 4, "max_players": 2, "description": "Правила", "source": None}


def run(coro):
    return asyncio.run(coro)


def deepseek_reply(content: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json={"choices": [{"message": {"content": content}}]})


def yandex_reply(text: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json={"result": {"alternatives": [{"message": {"role": "assistant", "text": text}}]}})


def test_deepseek_success_and_clamp():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return deepseek_reply(json.dumps(GOOD))

    p = DeepSeekProvider("sk-test", "https://api.deepseek.com/", "deepseek-chat", transport=httpx.MockTransport(handler))
    fields = run(p.parse("text"))
    assert seen["url"] == "https://api.deepseek.com/chat/completions"
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["messages"][0]["content"] == SYSTEM_PROMPT
    assert fields.name == "Царь горы"
    assert fields.max_players == 4  # clamped up to min_players


@pytest.mark.parametrize("status,kind", [(401, "auth"), (403, "auth"), (429, "quota"), (500, "bad_response")])
def test_deepseek_http_error_kinds(status, kind):
    p = DeepSeekProvider("k", transport=httpx.MockTransport(lambda r: httpx.Response(status, json={"error": {"message": "nope"}})))
    with pytest.raises(LLMError) as exc:
        run(p.parse("text"))
    assert exc.value.kind == kind
    assert exc.value.status_code == 502
    assert exc.value.provider == "deepseek"
    assert "nope" in exc.value.message


def test_deepseek_invalid_json():
    p = DeepSeekProvider("k", transport=httpx.MockTransport(lambda r: deepseek_reply("{\"broken\": ")))
    with pytest.raises(LLMError) as exc:
        run(p.parse("text"))
    assert exc.value.kind == "bad_response"
    assert exc.value.status_code == 502


def test_yandex_success():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return yandex_reply(json.dumps(GOOD))

    p = YandexProvider("yk", "b1gtest", "yandexgpt-lite/latest", transport=httpx.MockTransport(handler))
    fields = run(p.parse("text"))
    assert seen["url"] == "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    assert seen["auth"] == "Api-Key yk"
    body = seen["body"]
    assert body["modelUri"] == "gpt://b1gtest/yandexgpt-lite/latest"
    assert body["jsonObject"] is True
    assert body["completionOptions"]["maxTokens"] == "4000"
    assert body["messages"][0] == {"role": "system", "text": SYSTEM_PROMPT}
    assert body["messages"][1] == {"role": "user", "text": "text"}
    assert fields.name == "Царь горы"


@pytest.mark.parametrize(
    "status,body,kind,msg",
    [
        (401, {"message": "bad key"}, "auth", "bad key"),
        (403, {"error": {"message": "denied"}}, "auth", "denied"),
        (429, {"message": "slow down"}, "quota", "slow down"),
        (500, {"message": "boom"}, "bad_response", "boom"),
    ],
)
def test_yandex_http_error_kinds(status, body, kind, msg):
    p = YandexProvider("k", "f", transport=httpx.MockTransport(lambda r: httpx.Response(status, json=body)))
    with pytest.raises(LLMError) as exc:
        run(p.parse("text"))
    assert exc.value.kind == kind
    assert exc.value.provider == "yandex"
    assert f"HTTP {status}: {msg}" == exc.value.message


def test_yandex_fenced_json_is_stripped():
    p = YandexProvider("k", "f", transport=httpx.MockTransport(lambda r: yandex_reply("```json\n" + json.dumps(GOOD) + "\n```")))
    assert run(p.parse("text")).name == "Царь горы"


def test_yandex_invalid_json():
    p = YandexProvider("k", "f", transport=httpx.MockTransport(lambda r: yandex_reply("{oops")))
    with pytest.raises(LLMError) as exc:
        run(p.parse("text"))
    assert exc.value.kind == "bad_response"


def test_missing_fields_is_422():
    p = YandexProvider("k", "f", transport=httpx.MockTransport(lambda r: yandex_reply(json.dumps({"name": "x"}))))
    with pytest.raises(LLMError) as exc:
        run(p.parse("text"))
    assert exc.value.status_code == 422
    assert exc.value.kind == "bad_response"


def test_network_error_kind():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    p = YandexProvider("k", "f", transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError) as exc:
        run(p.parse("text"))
    assert exc.value.kind == "network"
    assert exc.value.status_code == 502


def test_check_reports_model():
    p = YandexProvider("k", "f", "yandexgpt-lite/latest", transport=httpx.MockTransport(lambda r: yandex_reply(json.dumps(GOOD))))
    assert run(p.check()) == "ok: gpt://f/yandexgpt-lite/latest → «Царь горы»"


def test_parse_keeps_metadata_and_drops_unknown_tags():
    reply = dict(GOOD, summary="кидай кубик и пей", minutes="20 мин", tags=["Кубики", "неведомый", "быстрая"], props="кубик")
    p = YandexProvider("k", "f", transport=httpx.MockTransport(lambda r: yandex_reply(json.dumps(reply))))
    fields = run(p.parse("text"))
    assert fields.summary == "кидай кубик и пей"
    assert fields.minutes == 20
    assert fields.tags == ["кубики", "быстрая"]
    assert fields.props == "кубик"


def test_enrich_uses_enrich_prompt_and_returns_meta():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return deepseek_reply(json.dumps({"summary": "коротко", "minutes": 15, "tags": ["карты"], "props": "колода"}))

    p = DeepSeekProvider("k", transport=httpx.MockTransport(handler))
    meta = run(p.enrich("Кольцо", "правила...", 3, None))
    assert seen["body"]["messages"][0]["content"] == ENRICH_PROMPT
    assert "Название: Кольцо" in seen["body"]["messages"][1]["content"]
    assert "Игроки: 3+" in seen["body"]["messages"][1]["content"]
    assert meta.model_dump() == {"summary": "коротко", "minutes": 15, "tags": ["карты"], "props": "колода"}


def test_refusal_prose_is_reported_as_refused():
    p = YandexProvider("k", "f", transport=httpx.MockTransport(lambda r: yandex_reply("Я не могу обсуждать эту тему.")))
    with pytest.raises(LLMError) as exc:
        run(p.enrich("X", "d", 2, None))
    assert exc.value.kind == "refused"
    assert exc.value.status_code == 422
    assert "Я не могу обсуждать" in exc.value.message
