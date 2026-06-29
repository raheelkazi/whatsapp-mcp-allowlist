# whatsapp-mcp-server/tests/test_lid_resolution.py
import sqlite3
import whatsapp


def _make_contacts_db(tmp_path):
    db = str(tmp_path / "whatsapp.db")
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE whatsmeow_contacts (our_jid TEXT, their_jid TEXT, "
        "first_name TEXT, full_name TEXT, push_name TEXT, business_name TEXT, "
        "redacted_phone TEXT)"
    )
    conn.execute("INSERT INTO whatsmeow_contacts VALUES "
                 "('me','531@lid','','Percy Lima',NULL,NULL,NULL)")        # full_name
    conn.execute("INSERT INTO whatsmeow_contacts VALUES "
                 "('me','659@s.whatsapp.net',NULL,NULL,'Ada',NULL,NULL)")  # push_name
    conn.commit()
    conn.close()
    return db


def test_resolve_prefers_full_name(tmp_path):
    db = _make_contacts_db(tmp_path)
    assert whatsapp.resolve_contact_name("531@lid", db) == "Percy Lima"


def test_resolve_falls_back_to_push_name(tmp_path):
    db = _make_contacts_db(tmp_path)
    assert whatsapp.resolve_contact_name("659@s.whatsapp.net", db) == "Ada"


def test_resolve_unknown_returns_none(tmp_path):
    db = _make_contacts_db(tmp_path)
    assert whatsapp.resolve_contact_name("999@s.whatsapp.net", db) is None


def test_resolve_missing_db_returns_none(tmp_path):
    assert whatsapp.resolve_contact_name("x@lid", str(tmp_path / "nope.db")) is None


def test_get_sender_name_falls_back_to_contact_store(tmp_path, monkeypatch):
    # messages.db chats has no match -> get_sender_name should use the contact store
    msgs = str(tmp_path / "messages.db")
    conn = sqlite3.connect(msgs)
    conn.execute("CREATE TABLE chats (jid TEXT, name TEXT)")
    conn.commit()
    conn.close()
    contacts = _make_contacts_db(tmp_path)
    monkeypatch.setattr(whatsapp, "MESSAGES_DB_PATH", msgs)
    monkeypatch.setattr(whatsapp, "CONTACTS_DB_PATH", contacts)
    whatsapp._CONTACTS_CACHE.clear()  # drop any cached default-path contacts
    assert whatsapp.get_sender_name("531@lid") == "Percy Lima"
