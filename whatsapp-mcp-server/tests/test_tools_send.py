# whatsapp-mcp-server/tests/test_tools_send.py
# main_with_allowlist fixture is provided by conftest.py
import importlib


def _reload_main(tmp_path, monkeypatch, allowlist_json, **env):
    path = tmp_path / "allowed_chats.json"
    path.write_text(allowlist_json)
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(path))
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import main
    importlib.reload(main)
    return main


_READ_SEND = '{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom","mode":"read+send"}]}'
_READ_ONLY = '{"chats":[{"jid":"111@s.whatsapp.net","label":"Work","mode":"read"}]}'


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


def test_read_only_mode_blocks_all_sends(tmp_path, monkeypatch):
    main = _reload_main(tmp_path, monkeypatch, _READ_SEND, WHATSAPP_READ_ONLY="1")
    calls = []
    monkeypatch.setattr(main, "whatsapp_send_message",
                        lambda r, m: calls.append(1) or (True, "sent"))
    result = main.send_message("111", "hi")
    assert result["success"] is False
    assert "read-only mode" in result["message"]
    assert calls == []  # bridge never called


def test_send_to_read_only_chat_blocked(tmp_path, monkeypatch):
    main = _reload_main(tmp_path, monkeypatch, _READ_ONLY)
    calls = []
    monkeypatch.setattr(main, "whatsapp_send_message",
                        lambda r, m: calls.append(1) or (True, "sent"))
    result = main.send_message("111", "hi")
    assert result["success"] is False
    assert "read-only" in result["message"]
    assert calls == []


def test_rate_limit_blocks_rapid_second_send(tmp_path, monkeypatch):
    main = _reload_main(tmp_path, monkeypatch, _READ_SEND,
                        WHATSAPP_SEND_MIN_INTERVAL_SEC="3600")
    monkeypatch.setattr(main, "whatsapp_send_message", lambda r, m: (True, "sent"))
    first = main.send_message("111", "one")
    second = main.send_message("111", "two")
    assert first["success"] is True
    assert second["success"] is False
    assert "rate limited" in second["message"]
