# whatsapp-mcp-server/tests/test_dashboard_allowlist.py
import importlib
import sqlite3
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    allow = tmp_path / "allowed_chats.json"
    allow.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom","mode":"read+send"}]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(allow))
    monkeypatch.setenv("WHATSAPP_AUDIT_LOG", str(tmp_path / "audit.log"))
    # contacts + chats DBs for search
    msgs = tmp_path / "messages.db"
    c = sqlite3.connect(msgs)
    c.execute("CREATE TABLE chats (jid TEXT, name TEXT)")
    c.execute("INSERT INTO chats VALUES ('222@g.us','Family Group')")
    c.commit(); c.close()
    wa = tmp_path / "whatsapp.db"
    c = sqlite3.connect(wa)
    c.execute("CREATE TABLE whatsmeow_contacts (our_jid TEXT, their_jid TEXT, first_name TEXT, full_name TEXT, push_name TEXT, business_name TEXT, redacted_phone TEXT)")
    c.execute("INSERT INTO whatsmeow_contacts VALUES ('me','333@s.whatsapp.net','','Family Doctor',NULL,NULL,NULL)")
    c.commit(); c.close()
    monkeypatch.setenv("WHATSAPP_DB", str(msgs))
    monkeypatch.setenv("WHATSAPP_CONTACTS_DB", str(wa))
    import dashboard
    importlib.reload(dashboard)
    return dashboard, str(allow)


def test_list_allowlist(ctx):
    dashboard, _ = ctx
    client = TestClient(dashboard.create_app())
    r = client.get("/api/allowlist")
    assert r.json() == [{"jid": "111@s.whatsapp.net", "label": "Mom", "mode": "read+send"}]


def test_add_and_remove(ctx):
    dashboard, _ = ctx
    client = TestClient(dashboard.create_app())
    client.post("/api/allowlist", json={"jid": "222@g.us", "label": "Fam", "mode": "read"})
    jids = {e["jid"]: e for e in client.get("/api/allowlist").json()}
    assert jids["222@g.us"]["mode"] == "read"
    client.delete("/api/allowlist/222@g.us")
    assert "222@g.us" not in {e["jid"] for e in client.get("/api/allowlist").json()}


def test_add_invalid_mode_400(ctx):
    dashboard, _ = ctx
    client = TestClient(dashboard.create_app())
    r = client.post("/api/allowlist", json={"jid": "x@g.us", "label": "X", "mode": "bogus"})
    assert r.status_code == 400


def test_contacts_search_merges_sources(ctx):
    dashboard, _ = ctx
    client = TestClient(dashboard.create_app())
    jids = {row["jid"] for row in client.get("/api/contacts/search?q=Family").json()}
    assert "222@g.us" in jids        # from chats
    assert "333@s.whatsapp.net" in jids  # from contact store


@pytest.fixture
def ctx_missing_dbs(tmp_path, monkeypatch):
    """Fixture where both bridge DBs do not exist (bridge never run)."""
    allow = tmp_path / "allowed_chats.json"
    allow.write_text('{"chats":[]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(allow))
    monkeypatch.setenv("WHATSAPP_AUDIT_LOG", str(tmp_path / "audit.log"))
    monkeypatch.setenv("WHATSAPP_DB", str(tmp_path / "nonexistent_messages.db"))
    monkeypatch.setenv("WHATSAPP_CONTACTS_DB", str(tmp_path / "nonexistent_whatsapp.db"))
    import dashboard
    importlib.reload(dashboard)
    return dashboard


def test_contacts_search_missing_dbs_returns_empty(ctx_missing_dbs):
    """contacts/search must return 200 [] when bridge DBs don't exist yet."""
    client = TestClient(ctx_missing_dbs.create_app())
    r = client.get("/api/contacts/search?q=anything")
    assert r.status_code == 200
    assert r.json() == []
