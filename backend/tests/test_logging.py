"""The http_request line carries the client's User-Agent and the site it came from, and no secrets."""
import io
import json
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logging_setup import LOGGED_TEXT, RequestLogMiddleware, setup_logging


@pytest.fixture
def lines(monkeypatch):
    """Capture stdout log lines. structlog writes to the sys.stdout it was configured with, so reconfigure."""
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    setup_logging()
    yield lambda: [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
    setup_logging()


@pytest.fixture
def client(lines):
    # A fresh app per test: the middleware's logger binds to the stdout of its first request.
    app = FastAPI()

    @app.get("/games/{game_id}")
    def game(game_id: int):
        return {"id": game_id}

    app.add_middleware(RequestLogMiddleware)
    return TestClient(app)


def requests_logged(lines) -> list[dict]:
    return [event for event in lines() if event["stream"] == "http_request"]


def test_request_line_has_user_agent_and_foreign_referrer(client, lines):
    client.get("/games/7", headers={"user-agent": "Mozilla/5.0 (Linux)", "referer": "https://t.me/somechat"})
    [event] = requests_logged(lines)
    assert event["http_path"] == "/games/{game_id}"
    assert event["user_agent"] == "Mozilla/5.0 (Linux)"
    assert event["referrer_host"] == "t.me"


def test_own_pages_and_broken_referrers_are_left_out(client, lines):
    client.get("/games/7", headers={"referer": "http://testserver/admin.html"})
    client.get("/games/7", headers={"referer": "http://[::1"})
    client.get("/games/7")
    assert [("referrer_host" in event) for event in requests_logged(lines)] == [False, False, False]


def test_user_agent_is_cut_and_admin_token_never_logged(client, lines):
    client.get("/games/7", headers={"user-agent": "x" * 1000, "x-admin-token": "secret-token-123"})
    [event] = requests_logged(lines)
    assert event["user_agent"] == "x" * LOGGED_TEXT
    assert "secret-token-123" not in json.dumps(lines())
