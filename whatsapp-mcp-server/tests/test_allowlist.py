# whatsapp-mcp-server/tests/test_allowlist.py
import json
import pytest
from allowlist import (
    load_allowlist, is_allowed, can_send, AllowlistError,
    normalize_recipient, check_send,
)


def write(tmp_path, obj):
    p = tmp_path / "allowed_chats.json"
    p.write_text(json.dumps(obj))
    return str(p)


def test_load_returns_jid_to_entry_map(tmp_path):
    path = write(tmp_path, {"chats": [
        {"jid": "111@s.whatsapp.net", "label": "Mom", "mode": "read+send"},
        {"jid": "222@g.us", "label": "Family", "mode": "read"},
    ]})
    assert load_allowlist(path) == {
        "111@s.whatsapp.net": {"label": "Mom", "mode": "read+send"},
        "222@g.us": {"label": "Family", "mode": "read"},
    }


def test_load_entry_without_mode_defaults_to_read_send(tmp_path):
    # backward compat: pre-existing entries have no "mode"
    path = write(tmp_path, {"chats": [{"jid": "111@s.whatsapp.net", "label": "Mom"}]})
    al = load_allowlist(path)
    assert al["111@s.whatsapp.net"] == {"label": "Mom", "mode": "read+send"}


def test_load_invalid_mode_fails_closed(tmp_path):
    path = write(tmp_path, {"chats": [
        {"jid": "111@s.whatsapp.net", "label": "Mom", "mode": "write-only"},
    ]})
    with pytest.raises(AllowlistError):
        load_allowlist(path)


def test_missing_file_fails_closed(tmp_path):
    with pytest.raises(AllowlistError):
        load_allowlist(str(tmp_path / "nope.json"))


def test_malformed_json_fails_closed(tmp_path):
    p = tmp_path / "allowed_chats.json"
    p.write_text("{not json")
    with pytest.raises(AllowlistError):
        load_allowlist(str(p))


def test_wrong_shape_fails_closed(tmp_path):
    path = write(tmp_path, {"chats": [{"label": "no jid"}]})
    with pytest.raises(AllowlistError):
        load_allowlist(path)


def test_empty_allowlist_is_valid_but_allows_nothing(tmp_path):
    path = write(tmp_path, {"chats": []})
    al = load_allowlist(path)
    assert al == {}
    assert is_allowed("111@s.whatsapp.net", al) is False


def test_is_allowed_membership():
    al = {"111@s.whatsapp.net": "Mom"}
    assert is_allowed("111@s.whatsapp.net", al) is True
    assert is_allowed("999@s.whatsapp.net", al) is False


def test_normalize_bare_phone_becomes_user_jid():
    assert normalize_recipient("1234567890") == "1234567890@s.whatsapp.net"


def test_normalize_passes_through_existing_jid():
    assert normalize_recipient("111@s.whatsapp.net") == "111@s.whatsapp.net"
    assert normalize_recipient("222@g.us") == "222@g.us"


def test_normalize_rejects_garbage():
    with pytest.raises(AllowlistError):
        normalize_recipient("not a number")


def test_can_send_respects_mode():
    al = {
        "111@s.whatsapp.net": {"label": "Mom", "mode": "read+send"},
        "222@g.us": {"label": "Work", "mode": "read"},
    }
    assert can_send("111@s.whatsapp.net", al) is True
    assert can_send("222@g.us", al) is False        # read-only
    assert can_send("999@s.whatsapp.net", al) is False  # off-list


def test_check_send_allows_read_send_target():
    al = {"1234567890@s.whatsapp.net": {"label": "Mom", "mode": "read+send"}}
    assert check_send("1234567890", al) == "1234567890@s.whatsapp.net"


def test_check_send_rejects_read_only_target():
    al = {"1234567890@s.whatsapp.net": {"label": "Work", "mode": "read"}}
    with pytest.raises(AllowlistError, match="read-only"):
        check_send("1234567890", al)


def test_check_send_rejects_unlisted_target():
    al = {"1234567890@s.whatsapp.net": {"label": "Mom", "mode": "read+send"}}
    with pytest.raises(AllowlistError):
        check_send("999@s.whatsapp.net", al)


def test_normalize_strips_phone_formatting():
    assert normalize_recipient("+1 234-567-8900") == "12345678900@s.whatsapp.net"


def test_normalize_rejects_malformed_jid():
    with pytest.raises(AllowlistError):
        normalize_recipient("foo@bar.baz")


def test_normalize_rejects_unicode_digits():
    with pytest.raises(AllowlistError):
        normalize_recipient("١٢٣")


def test_check_send_rejects_garbage_input():
    with pytest.raises(AllowlistError):
        check_send("not a number", {"111@s.whatsapp.net": "Mom"})


from dataclasses import dataclass
from allowlist import filter_chats, filter_messages, filter_contacts


@dataclass
class FakeChat:
    jid: str


@dataclass
class FakeMessage:
    chat_jid: str


@dataclass
class FakeContact:
    jid: str


def test_filter_chats_keeps_only_allowed():
    al = {"111@s.whatsapp.net": "Mom"}
    chats = [FakeChat("111@s.whatsapp.net"), FakeChat("999@s.whatsapp.net")]
    assert filter_chats(chats, al) == [FakeChat("111@s.whatsapp.net")]


def test_filter_messages_keeps_only_allowed_chat():
    al = {"111@s.whatsapp.net": "Mom"}
    msgs = [FakeMessage("111@s.whatsapp.net"), FakeMessage("999@s.whatsapp.net")]
    assert filter_messages(msgs, al) == [FakeMessage("111@s.whatsapp.net")]


def test_filter_contacts_keeps_only_allowed():
    al = {"111@s.whatsapp.net": "Mom"}
    contacts = [FakeContact("111@s.whatsapp.net"), FakeContact("999@s.whatsapp.net")]
    assert filter_contacts(contacts, al) == [FakeContact("111@s.whatsapp.net")]


def test_filters_handle_empty_allowlist():
    assert filter_chats([FakeChat("111@s.whatsapp.net")], {}) == []


def test_filter_messages_handles_empty_allowlist():
    assert filter_messages([FakeMessage("111@s.whatsapp.net")], {}) == []


def test_filter_contacts_handles_empty_allowlist():
    assert filter_contacts([FakeContact("111@s.whatsapp.net")], {}) == []
