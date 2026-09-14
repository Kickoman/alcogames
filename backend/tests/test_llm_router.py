import pytest
from fastapi.testclient import TestClient

from app import llm_settings
from app.llm_providers import LLMError
from app.main import app
from app.models import GameCreate, GameMeta, ParsedGameFields
from app import storage

H = {"X-Admin-Token": "test-token"}


@pytest.fixture
def client(llm_env, tmp_path, monkeypatch):
    monkeypatch.setattr(llm_env, "DATA_DIR", tmp_path)
    monkeypatch.setattr(llm_env, "GAMES_FILE", tmp_path / "games.json")
    return TestClient(app)


class FakeProvider:
    name = "yandex"
    model = "fake"

    def __init__(self, fail: LLMError | None = None):
        self.fail = fail

    async def parse(self, text):
        if self.fail:
            raise self.fail
        return ParsedGameFields(name="Игра", min_players=2, max_players=None, description="Правила")

    async def check(self):
        if self.fail:
            raise self.fail
        return "ok: fake → «Игра»"

    async def enrich(self, name, description, min_players, max_players):
        if self.fail:
            raise self.fail
        return GameMeta(summary="коротко о " + name, minutes=25, tags=["карты", "быстрая"], props="колода")


def test_requires_token(client):
    assert client.get("/api/admin/llm-settings").status_code == 401


def test_get_masks_keys(client):
    llm_settings.save({"provider": "yandex", "yandex_api_key": "AQVN-secret-1234", "yandex_folder_id": "b1g"})
    r = client.get("/api/admin/llm-settings", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "yandex" and body["ready"] is True
    assert body["yandex_key_tail"] == "1234"
    assert "AQVN-secret" not in r.text


def test_put_updates_and_clears(client):
    r = client.put("/api/admin/llm-settings", headers=H, json={"provider": "deepseek", "deepseek_api_key": "sk-abcd", "deepseek_model": "deepseek-chat"})
    assert r.status_code == 200 and r.json()["ready"] is True and r.json()["deepseek_key_tail"] == "abcd"
    r = client.put("/api/admin/llm-settings", headers=H, json={"deepseek_api_key": ""})
    assert r.json()["deepseek_key_tail"] == "abcd"
    r = client.put("/api/admin/llm-settings", headers=H, json={"clear_deepseek_api_key": True})
    assert r.json()["deepseek_key_tail"] == "" and r.json()["ready"] is False


def test_put_rejects_unknown_provider(client):
    assert client.put("/api/admin/llm-settings", headers=H, json={"provider": "openai"}).status_code == 422


def test_test_not_configured(client):
    r = client.post("/api/admin/llm-settings/test", headers=H)
    assert r.status_code == 200 and r.json() == {"ok": False, "detail": "not_configured", "provider": "none", "model": ""}


def test_test_success(client, monkeypatch):
    monkeypatch.setattr(llm_settings, "get_provider", lambda s=None: FakeProvider())
    r = client.post("/api/admin/llm-settings/test", headers=H)
    assert r.json() == {"ok": True, "detail": "ok: fake → «Игра»", "provider": "yandex", "model": "fake"}


def test_test_failure_reports_kind(client, monkeypatch):
    monkeypatch.setattr(llm_settings, "get_provider", lambda s=None: FakeProvider(LLMError("HTTP 403: denied", 502, "auth", "yandex", "fake")))
    r = client.post("/api/admin/llm-settings/test", headers=H)
    assert r.json()["ok"] is False and r.json()["detail"] == "auth: HTTP 403: denied"


def test_parse_503_when_none(client):
    r = client.post("/api/admin/parse", headers=H, json={"text": "some game"})
    assert r.status_code == 503


def test_parse_uses_provider(client, monkeypatch):
    monkeypatch.setattr(llm_settings, "get_provider", lambda s=None: FakeProvider())
    r = client.post("/api/admin/parse", headers=H, json={"text": "some game"})
    assert r.status_code == 200 and r.json()["name"] == "Игра" and r.json()["max_players"] is None


def test_enrich_saves_metadata(client, monkeypatch):
    monkeypatch.setattr(llm_settings, "get_provider", lambda s=None: FakeProvider())
    game = storage.create_game(GameCreate(name="Кольцо", min_players=3, max_players=None, description="правила"))
    r = client.post(f"/api/admin/games/{game.id}/enrich", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["summary"] == "коротко о Кольцо" and body["minutes"] == 25 and body["tags"] == ["карты", "быстрая"]
    assert body["likes"] == 0 and body["description"] == "правила"
    stored = storage.get_game(game.id)
    assert stored.props == "колода"
    assert client.get("/api/games").json()[0]["tags"] == ["карты", "быстрая"]


def test_enrich_404_and_503(client, monkeypatch):
    assert client.post("/api/admin/games/nope/enrich", headers=H).status_code == 404
    game = storage.create_game(GameCreate(name="X", min_players=2, description="d"))
    assert client.post(f"/api/admin/games/{game.id}/enrich", headers=H).status_code == 503
