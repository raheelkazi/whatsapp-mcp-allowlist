import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import manage_allowlist as m


def test_add_then_read_roundtrips(tmp_path):
    path = str(tmp_path / "allowed_chats.json")
    m.add_entry(path, "111@s.whatsapp.net", "Mom")
    assert m.read_entries(path) == [{"jid": "111@s.whatsapp.net", "label": "Mom"}]


def test_add_is_idempotent_on_jid(tmp_path):
    path = str(tmp_path / "allowed_chats.json")
    m.add_entry(path, "111@s.whatsapp.net", "Mom")
    m.add_entry(path, "111@s.whatsapp.net", "Mom Updated")
    entries = m.read_entries(path)
    assert len(entries) == 1
    assert entries[0]["label"] == "Mom Updated"


def test_remove_entry(tmp_path):
    path = str(tmp_path / "allowed_chats.json")
    m.add_entry(path, "111@s.whatsapp.net", "Mom")
    m.add_entry(path, "222@g.us", "Family")
    m.remove_entry(path, "111@s.whatsapp.net")
    assert m.read_entries(path) == [{"jid": "222@g.us", "label": "Family"}]


def test_read_missing_file_returns_empty(tmp_path):
    assert m.read_entries(str(tmp_path / "nope.json")) == []


def test_search_db_returns_all_matches(tmp_path):
    db = str(tmp_path / "messages.db")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE chats (jid TEXT, name TEXT)")
    conn.execute("INSERT INTO chats VALUES ('111@s.whatsapp.net','Mom')")
    conn.execute("INSERT INTO chats VALUES ('999@s.whatsapp.net','Mob Boss')")
    conn.commit()
    conn.close()
    results = m.search_db(db, "Mo")
    assert {r["jid"] for r in results} == {"111@s.whatsapp.net", "999@s.whatsapp.net"}
