# whatsapp-mcp-server/tests/conftest.py
import importlib
import pytest


@pytest.fixture(autouse=True)
def _isolate_audit_log(tmp_path, monkeypatch):
    """Keep audit writes out of the real audit.log during tests."""
    monkeypatch.setenv("WHATSAPP_AUDIT_LOG", str(tmp_path / "audit.log"))


@pytest.fixture
def main_with_allowlist(tmp_path, monkeypatch):
    """Reload the `main` module with a temp allowlist holding one chat (Mom)."""
    path = tmp_path / "allowed_chats.json"
    path.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom"}]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(path))
    import main
    importlib.reload(main)
    return main
