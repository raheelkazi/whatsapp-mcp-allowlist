# whatsapp-mcp-server/tests/test_dashboard_cors.py
import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    allow = tmp_path / "allowed_chats.json"
    allow.write_text('{"chats":[]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(allow))
    monkeypatch.setenv("WHATSAPP_AUDIT_LOG", str(tmp_path / "audit.log"))
    import dashboard
    importlib.reload(dashboard)
    return TestClient(dashboard.create_app())


def test_cors_allows_vite_origin(client):
    r = client.get("/api/status", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_disallowed_origin(client):
    r = client.get("/api/status", headers={"Origin": "http://evil.example"})
    acao = r.headers.get("access-control-allow-origin")
    assert acao != "http://evil.example", (
        "Disallowed origin must not be echoed in access-control-allow-origin"
    )
