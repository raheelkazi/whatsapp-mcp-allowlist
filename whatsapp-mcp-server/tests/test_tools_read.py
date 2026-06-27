# whatsapp-mcp-server/tests/test_tools_read.py
import importlib
from dataclasses import dataclass, field
from typing import List
import pytest


@dataclass
class FakeChat:
    jid: str
    name: str = ""


@dataclass
class FakeMsg:
    chat_jid: str


@dataclass
class FakeContact:
    jid: str


@dataclass
class FakeMessage:
    chat_jid: str


@dataclass
class FakeContext:
    message: FakeMessage
    before: List[FakeMsg] = field(default_factory=list)
    after: List[FakeMsg] = field(default_factory=list)


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


# ---------------------------------------------------------------------------
# get_chat
# ---------------------------------------------------------------------------

def test_get_chat_off_list_returns_error(main_with_allowlist):
    result = main_with_allowlist.get_chat("999@s.whatsapp.net")
    assert "error" in result


def test_get_chat_allowed_returns_bridge_result(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    monkeypatch.setattr(main, "whatsapp_get_chat", lambda jid, include_last_message: {"jid": jid, "name": "Mom"})
    result = main.get_chat("111@s.whatsapp.net")
    assert result == {"jid": "111@s.whatsapp.net", "name": "Mom"}


# ---------------------------------------------------------------------------
# list_messages
# ---------------------------------------------------------------------------

def test_list_messages_off_list_chat_jid_returns_error_without_calling_bridge(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    called = []
    monkeypatch.setattr(main, "whatsapp_list_messages", lambda **kw: called.append(1) or [])
    result = main.list_messages(chat_jid="999@s.whatsapp.net")
    assert "error" in result
    assert called == [], "bridge must not be called for off-list chat_jid"


def test_list_messages_no_chat_jid_filters_to_allowlisted(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    monkeypatch.setattr(main, "whatsapp_list_messages", lambda **kw: [
        FakeMsg("111@s.whatsapp.net"),
        FakeMsg("999@s.whatsapp.net"),
    ])
    result = main.list_messages()
    assert all(m.chat_jid == "111@s.whatsapp.net" for m in result)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# get_message_context
# ---------------------------------------------------------------------------

def test_get_message_context_off_list_returns_error(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    monkeypatch.setattr(
        main,
        "whatsapp_get_message_context",
        lambda msg_id, before, after: FakeContext(message=FakeMessage("999@s.whatsapp.net")),
    )
    result = main.get_message_context("msg-1")
    assert "error" in result


def test_get_message_context_none_returns_error(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    monkeypatch.setattr(main, "whatsapp_get_message_context", lambda *a: None)
    result = main.get_message_context("msg-x")
    assert "error" in result


def test_get_message_context_allowed_filters_before_after(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    ctx = FakeContext(
        message=FakeMessage("111@s.whatsapp.net"),
        before=[FakeMsg("111@s.whatsapp.net"), FakeMsg("999@s.whatsapp.net")],
        after=[FakeMsg("999@s.whatsapp.net"), FakeMsg("111@s.whatsapp.net")],
    )
    monkeypatch.setattr(main, "whatsapp_get_message_context", lambda *a: ctx)
    result = main.get_message_context("msg-2")
    assert all(m.chat_jid == "111@s.whatsapp.net" for m in result.before)
    assert all(m.chat_jid == "111@s.whatsapp.net" for m in result.after)
    assert len(result.before) == 1
    assert len(result.after) == 1


# ---------------------------------------------------------------------------
# search_contacts
# ---------------------------------------------------------------------------

def test_search_contacts_filters_to_allowlisted(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    monkeypatch.setattr(main, "whatsapp_search_contacts", lambda query: [
        FakeContact("111@s.whatsapp.net"),
        FakeContact("999@s.whatsapp.net"),
    ])
    result = main.search_contacts("Mom")
    assert [c.jid for c in result] == ["111@s.whatsapp.net"]


# ---------------------------------------------------------------------------
# download_media
# ---------------------------------------------------------------------------

def test_download_media_off_list_returns_error_without_calling_bridge(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    called = []
    monkeypatch.setattr(main, "whatsapp_download_media", lambda *a: called.append(1) or {})
    result = main.download_media("msg-1", "999@s.whatsapp.net")
    assert "error" in result
    assert called == [], "bridge must not be called for off-list chat_jid"


def test_download_media_allowed_calls_bridge(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    bridge_result = {"file_path": "/tmp/media.jpg"}
    monkeypatch.setattr(main, "whatsapp_download_media", lambda msg_id, chat_jid: bridge_result)
    result = main.download_media("msg-1", "111@s.whatsapp.net")
    assert result is bridge_result
