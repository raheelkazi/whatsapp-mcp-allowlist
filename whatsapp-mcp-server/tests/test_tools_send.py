# whatsapp-mcp-server/tests/test_tools_send.py
import importlib
import pytest


@pytest.fixture
def main_with_allowlist(tmp_path, monkeypatch):
    path = tmp_path / "allowed_chats.json"
    path.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom"}]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(path))
    import main
    importlib.reload(main)
    return main


def test_send_to_allowed_recipient_calls_bridge(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    calls = []
    monkeypatch.setattr(main, "whatsapp_send_message",
                        lambda recipient, message: calls.append((recipient, message)) or (True, "sent"))
    result = main.send_message("111", "hi mom")
    assert calls == [("111@s.whatsapp.net", "hi mom")]
    assert result["success"] is True


def test_send_to_unlisted_recipient_is_blocked(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    calls = []
    monkeypatch.setattr(main, "whatsapp_send_message",
                        lambda recipient, message: calls.append(1) or (True, "sent"))
    result = main.send_message("999", "should not go")
    assert result["success"] is False
    assert calls == []  # bridge never called


def test_send_file_to_allowed_recipient_calls_bridge(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    calls = []
    monkeypatch.setattr(main, "whatsapp_send_file",
                        lambda recipient, media_path: calls.append((recipient, media_path)) or (True, "sent"))
    result = main.send_file("111", "/tmp/x.jpg")
    assert calls == [("111@s.whatsapp.net", "/tmp/x.jpg")]
    assert result["success"] is True


def test_send_file_to_unlisted_recipient_is_blocked(main_with_allowlist, monkeypatch):
    main = main_with_allowlist
    calls = []
    monkeypatch.setattr(main, "whatsapp_send_file",
                        lambda recipient, media_path: calls.append(1) or (True, "sent"))
    result = main.send_file("999", "/tmp/x.jpg")
    assert result["success"] is False
    assert calls == []  # bridge never called


def test_send_audio_message_removed(main_with_allowlist):
    assert not hasattr(main_with_allowlist, "send_audio_message")
