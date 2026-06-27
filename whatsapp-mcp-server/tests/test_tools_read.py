# whatsapp-mcp-server/tests/test_tools_read.py
import importlib
from dataclasses import dataclass
import pytest


@dataclass
class FakeChat:
    jid: str
    name: str = ""


@pytest.fixture
def main_with_allowlist(tmp_path, monkeypatch):
    path = tmp_path / "allowed_chats.json"
    path.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom"}]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(path))
    import main
    importlib.reload(main)
    return main


def test_list_chats_filters_to_allowlist(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    monkeypatch.setattr(main, "whatsapp_list_chats", lambda **kw: [
        FakeChat("111@s.whatsapp.net", "Mom"),
        FakeChat("999@s.whatsapp.net", "Stranger"),
    ])
    result = main.list_chats()
    assert [c.jid for c in result] == ["111@s.whatsapp.net"]


def test_list_allowed_chats_returns_entries(main_with_allowlist):
    result = main_with_allowlist.list_allowed_chats()
    assert result == [{"jid": "111@s.whatsapp.net", "label": "Mom"}]
