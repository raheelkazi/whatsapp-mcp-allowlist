# whatsapp-mcp-server/tests/test_integration_db.py
"""Integration tests that exercise the real bridge (no mock on whatsapp.*).

These tests create a temporary SQLite database matching the real schema and
verify that the MCP tools interact with it correctly end-to-end.
"""
import importlib
import sqlite3
import sys
import os

import pytest

# Ensure the server package root is on sys.path for direct imports.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import whatsapp  # noqa: E402 – must come after sys.path manipulation


@pytest.fixture
def temp_db(tmp_path):
    """Build a minimal SQLite database that matches the real bridge schema."""
    db_path = tmp_path / "messages.db"
    conn = sqlite3.connect(str(db_path))
    # Schema mirrors what whatsapp.py queries:
    # chats: jid, name  (last_message_time needed by list_chats but not list_messages)
    conn.execute("""
        CREATE TABLE chats (
            jid TEXT PRIMARY KEY,
            name TEXT,
            last_message_time TEXT
        )
    """)
    # messages: id, timestamp, sender, chat_jid, content, is_from_me, media_type
    conn.execute("""
        CREATE TABLE messages (
            id TEXT,
            timestamp TEXT,
            sender TEXT,
            chat_jid TEXT,
            content TEXT,
            is_from_me INTEGER,
            media_type TEXT
        )
    """)
    conn.execute(
        "INSERT INTO chats VALUES (?, ?, ?)",
        ("111@s.whatsapp.net", "Mom", "2024-01-01T10:00:00"),
    )
    conn.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "msg-integration-1",
            "2024-01-01T10:00:00",
            "111@s.whatsapp.net",
            "111@s.whatsapp.net",
            "Hello from Mom",
            0,
            None,
        ),
    )
    conn.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "msg-integration-2",
            "2024-01-01T10:01:00",
            "me",
            "111@s.whatsapp.net",
            "Hi Mom!",
            1,
            None,
        ),
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def main_with_real_db(tmp_path, temp_db, monkeypatch):
    """Reload main with a real DB and a temp allowlist (no bridge mocks)."""
    allowlist_path = tmp_path / "allowed_chats.json"
    allowlist_path.write_text('{"chats":[{"jid":"111@s.whatsapp.net","label":"Mom"}]}')
    monkeypatch.setenv("WHATSAPP_ALLOWLIST_PATH", str(allowlist_path))
    # Redirect the bridge's DB path to our temp database.
    monkeypatch.setattr(whatsapp, "MESSAGES_DB_PATH", str(temp_db))
    import main
    importlib.reload(main)
    return main


# ---------------------------------------------------------------------------
# list_messages integration
# ---------------------------------------------------------------------------


def test_list_messages_integration_returns_string_with_content(main_with_real_db):
    """Real bridge returns a formatted string; tool must return it verbatim."""
    main = main_with_real_db
    result = main.list_messages(chat_jid="111@s.whatsapp.net", include_context=False)
    assert isinstance(result, str), (
        f"Expected str, got {type(result).__name__!r}: {result!r}"
    )
    assert "Hello from Mom" in result, (
        f"Inserted message content not found in result: {result!r}"
    )


def test_list_messages_integration_no_chat_jid_returns_error(main_with_real_db):
    """chat_jid=None must return an error dict without hitting the DB."""
    main = main_with_real_db
    result = main.list_messages(chat_jid=None, include_context=False)
    assert isinstance(result, dict)
    assert "error" in result


def test_list_messages_integration_off_list_returns_error(main_with_real_db):
    """Off-list chat_jid must return an error dict without hitting the DB."""
    main = main_with_real_db
    result = main.list_messages(chat_jid="999@s.whatsapp.net", include_context=False)
    assert isinstance(result, dict)
    assert "error" in result
