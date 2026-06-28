# whatsapp-mcp-server/tests/conftest.py
import importlib
import pytest


@pytest.fixture
def main_with_allowlist(tmp_path, monkeypatch):
    """Reload the `main` module with a temp allowlist holding one chat (Mom)."""
    path = tmp_path / "allowed_chats.json"
    path.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom"}]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(path))
    import main
    importlib.reload(main)
    return main
