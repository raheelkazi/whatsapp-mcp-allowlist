# whatsapp-mcp-server/tests/test_allowlist.py
import json
import pytest
from allowlist import load_allowlist, is_allowed, AllowlistError


def write(tmp_path, obj):
    p = tmp_path / "allowed_chats.json"
    p.write_text(json.dumps(obj))
    return str(p)


def test_load_returns_jid_to_label_map(tmp_path):
    path = write(tmp_path, {"chats": [
        {"jid": "111@s.whatsapp.net", "label": "Mom"},
        {"jid": "222@g.us", "label": "Family"},
    ]})
    assert load_allowlist(path) == {
        "111@s.whatsapp.net": "Mom",
        "222@g.us": "Family",
    }


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
