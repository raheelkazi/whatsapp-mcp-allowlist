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
    # Basic shape: first call populates data and generated_at
    client = make(_gens(text="Asked about the plumber."))
    r = client.get("/api/summaries").json()
    assert r["error"] is None
    assert r["items"][0]["summary"] == "Asked about the plumber."
    assert r["generated_at"]


def test_summaries_caches_between_apps_and_refresh_bypasses_cache(make):
    # Build client A with "A summary" generators and populate the on-disk cache.
    client_a = make(_gens(text="A summary."))
    r1 = client_a.get("/api/summaries").json()
    assert r1["error"] is None
    assert r1["items"][0]["summary"] == "A summary."
    generated_at_1 = r1["generated_at"]

    # Build a NEW client with "B summary" generators — same cache path on disk.
    # Without ?refresh=1 the cached A value must still be served.
    client_b = make(_gens(text="B summary."))
    r2 = client_b.get("/api/summaries").json()
    assert r2["items"][0]["summary"] == "A summary.", "cache must return old value without refresh"
    assert r2["generated_at"] == generated_at_1

    # With ?refresh=1 the new generators run and B summary is stored and returned.
    r3 = client_b.get("/api/summaries?refresh=1").json()
    assert r3["items"][0]["summary"] == "B summary."
    assert r3["generated_at"] != generated_at_1, "generated_at must change after refresh"


def test_section_returns_error_envelope_on_generator_exception(make):
    """Generators that raise at call-time must never produce a 500; return HTTP-200 error envelope."""
    def raising(s, u):
        raise RuntimeError("boom")

    client = make((raising, raising))
    r = client.get("/api/summaries")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["error"] is not None
    assert "boom" in body["error"]


def test_allowlist_edit_invalidates_cache(make):
    # After an allowlist add, the previously-cached intelligence sections must be
    # dropped so the next load recomputes for the new chat set (not stale results).
    import os
    import dashcache
    client = make(_gens(text="A summary."))
    client.get("/api/summaries")  # populate the cache
    cache_path = os.environ["WHATSAPP_DASHBOARD_CACHE"]
    assert dashcache.get_section(cache_path, "summaries") is not None  # cached now

    r = client.post("/api/allowlist",
                    json={"jid": "999@s.whatsapp.net", "label": "New", "mode": "read"})
    assert r.status_code == 200
    assert dashcache.get_section(cache_path, "summaries") is None  # cache invalidated


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


def test_fetch_guard_refuses_off_allowlist_jid(make, monkeypatch):
    # Defense in depth: even if a caller hands _fetch an off-list jid, it must
    # return "" and never read that chat via list_messages.
    import dashboard
    fetched = []
    monkeypatch.setattr(dashboard, "whatsapp_list_messages",
                        lambda **kw: fetched.append(kw.get("chat_jid")) or "leaked!",
                        raising=False)
    probe = {}

    def fake_summarize(allowlist, fetch_fn, gen_text):
        probe["off"] = fetch_fn("999@off.list")      # off the allowlist
        probe["on"] = fetch_fn("111@s.whatsapp.net")  # on the allowlist
        return []

    monkeypatch.setattr(dashboard.intelligence, "summarize", fake_summarize)
    client = dashboard.create_app(generators=_gens())
    client = TestClient(client)
    client.get("/api/summaries")
    assert probe["off"] == ""                 # guard returned empty, no read
    assert probe["on"] == "leaked!"           # allowlisted chat still readable
    assert fetched == ["111@s.whatsapp.net"]  # list_messages never hit for off-list jid
