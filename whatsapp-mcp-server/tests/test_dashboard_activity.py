# whatsapp-mcp-server/tests/test_dashboard_activity.py
import importlib
import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    allow = tmp_path / "allowed_chats.json"
    allow.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom","mode":"read+send"}]}')
    log = tmp_path / "audit.log"
    log.write_text(
        json.dumps({"ts": "t1", "tool": "list_chats", "decision": "allowed"}) + "\n"
        + "broken line not json\n"
        + json.dumps({"ts": "t2", "tool": "send_message", "decision": "denied", "reason": "rate_limited"}) + "\n"
    )
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(allow))
    monkeypatch.setenv("WHATSAPP_AUDIT_LOG", str(log))
    import dashboard
    importlib.reload(dashboard)
    return TestClient(dashboard.create_app())


def test_activity_newest_first_skips_malformed(client):
    rows = client.get("/api/activity?limit=10").json()
    assert [r["tool"] for r in rows] == ["send_message", "list_chats"]  # newest first, broken skipped


def test_activity_missing_file_returns_empty(tmp_path, monkeypatch):
    allow = tmp_path / "allowed_chats.json"
    allow.write_text('{"chats":[]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(allow))
    monkeypatch.setenv("WHATSAPP_AUDIT_LOG", str(tmp_path / "nope.log"))
    import dashboard, importlib
    importlib.reload(dashboard)
    client = TestClient(dashboard.create_app())
    assert client.get("/api/activity").json() == []
