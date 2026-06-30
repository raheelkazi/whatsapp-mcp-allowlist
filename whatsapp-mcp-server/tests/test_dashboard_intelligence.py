# whatsapp-mcp-server/tests/test_dashboard_intelligence.py
import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def make(tmp_path, monkeypatch):
    allow = tmp_path / "allowed_chats.json"
    allow.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom","mode":"read+send"}]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(allow))
    monkeypatch.setenv("WHATSAPP_AUDIT_LOG", str(tmp_path / "audit.log"))
    monkeypatch.setenv("WHATSAPP_DASHBOARD_CACHE", str(tmp_path / "cache.json"))
    import dashboard
    importlib.reload(dashboard)

    def _client(generators):
        # make list_messages return deterministic text for the allowlisted chat
        monkeypatch.setattr(dashboard, "whatsapp_list_messages",
                            lambda **kw: "Mom: did you call the plumber?", raising=False)
        app = dashboard.create_app(generators=generators)
        return TestClient(app)
    return _client


def _gens(text="Summary.", js=None):
    return (lambda s, u: text, lambda s, u: (js if js is not None else []))


def test_summaries_returns_items_and_caches(make):
    client = make(_gens(text="Asked about the plumber."))
    r = client.get("/api/summaries").json()
    assert r["error"] is None
    assert r["items"][0]["summary"] == "Asked about the plumber."
    assert r["generated_at"]
    # second call (no refresh) is served from cache even if generators would differ
    client2_items = client.get("/api/summaries").json()["items"]
    assert client2_items[0]["summary"] == "Asked about the plumber."


def test_suggestions_shape(make):
    client = make(_gens(js=[{"chat_jid": "111@s.whatsapp.net", "draft": "Yes!"}]))
    r = client.get("/api/suggestions").json()
    assert r["items"][0]["draft"] == "Yes!"


def test_reminders_shape(make):
    client = make(_gens(js=[{"kind": "unanswered", "text": "Reply to Mom",
                             "related_chat_jid": "111@s.whatsapp.net"}]))
    r = client.get("/api/reminders").json()
    assert r["items"][0]["kind"] == "unanswered"


def test_unavailable_when_no_generators_and_no_key(make, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = make(None)  # no injected generators; no key → graceful error envelope
    r = client.get("/api/summaries").json()
    assert r["items"] == []
    assert "ANTHROPIC_API_KEY" in r["error"]
