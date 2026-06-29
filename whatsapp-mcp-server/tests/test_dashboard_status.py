import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "allowed_chats.json"
    path.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom","mode":"read+send"}]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(path))
    monkeypatch.setenv("WHATSAPP_AUDIT_LOG", str(tmp_path / "audit.log"))
    import dashboard
    importlib.reload(dashboard)
    return TestClient(dashboard.create_app())


def test_status_shape(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"bridge_reachable", "read_only", "rate_limit"}
    assert body["read_only"] is False
    assert body["rate_limit"]["max_per_hour"] == 30
