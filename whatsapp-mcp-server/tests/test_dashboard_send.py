# whatsapp-mcp-server/tests/test_dashboard_send.py
import importlib
import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def make(tmp_path, monkeypatch):
    allow = tmp_path / "allowed_chats.json"
    allow.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom","mode":"read+send"}]}')
    log = tmp_path / "audit.log"
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(allow))
    monkeypatch.setenv("WHATSAPP_AUDIT_LOG", str(log))
    import dashboard
    importlib.reload(dashboard)

    def _client(send_fn):
        return TestClient(dashboard.create_app(send_fn=send_fn)), log
    return _client


def test_send_allowed_calls_bridge_and_audits(make):
    calls = []
    client, log = make(lambda jid, body: calls.append((jid, body)) or (True, "sent"))
    r = client.post("/api/send", json={"recipient": "111", "message": "hi"})
    assert r.json()["success"] is True
    assert calls == [("111@s.whatsapp.net", "hi")]
    last = json.loads(open(log).read().splitlines()[-1])
    assert last["tool"] == "dashboard_send" and last["decision"] == "allowed"


def test_send_off_list_blocked_and_audited(make):
    calls = []
    client, log = make(lambda jid, body: calls.append(1) or (True, "sent"))
    r = client.post("/api/send", json={"recipient": "999", "message": "no"})
    assert r.json()["success"] is False
    assert calls == []
    last = json.loads(open(log).read().splitlines()[-1])
    assert last["tool"] == "dashboard_send" and last["decision"] == "denied"
