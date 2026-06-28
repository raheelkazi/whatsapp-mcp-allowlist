#!/usr/bin/env python3
"""Admin CLI to curate allowed_chats.json. NOT exposed over MCP.

Searches the full WhatsApp chat database so the user can discover JIDs, then
adds/removes them from the allowlist the MCP server enforces.
"""
import argparse
import json
import os
import sqlite3

DEFAULT_ALLOWLIST = os.path.join(
    os.path.dirname(__file__), "whatsapp-mcp-server", "allowed_chats.json")
DEFAULT_DB = os.path.join(
    os.path.dirname(__file__), "whatsapp-bridge", "store", "messages.db")
DEFAULT_CONTACTS_DB = os.path.join(
    os.path.dirname(__file__), "whatsapp-bridge", "store", "whatsapp.db")


def read_entries(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f).get("chats", [])


def _write_entries(path: str, entries: list) -> None:
    with open(path, "w") as f:
        json.dump({"chats": entries}, f, indent=2)


def add_entry(path: str, jid: str, label: str) -> None:
    entries = [e for e in read_entries(path) if e["jid"] != jid]
    entries.append({"jid": jid, "label": label})
    _write_entries(path, entries)


def remove_entry(path: str, jid: str) -> None:
    _write_entries(path, [e for e in read_entries(path) if e["jid"] != jid])


def search_db(db_path: str, query: str) -> list:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT jid, name FROM chats WHERE name LIKE ? ORDER BY name",
            (f"%{query}%",),
        ).fetchall()
    finally:
        conn.close()
    return [{"jid": jid, "name": name} for jid, name in rows]


def search_contacts_db(db_path: str, query: str) -> list:
    """Search whatsmeow's contact store (whatsapp.db) by any name field.

    Individual contacts' names live here, not in messages.db's chats table,
    so a chat-name search alone misses people you have not yet messaged.
    """
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    like = f"%{query}%"
    try:
        rows = conn.execute(
            "SELECT their_jid, full_name, push_name, first_name, business_name "
            "FROM whatsmeow_contacts "
            "WHERE full_name LIKE ? OR push_name LIKE ? "
            "OR first_name LIKE ? OR business_name LIKE ? "
            "ORDER BY full_name",
            (like, like, like, like),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()
    return [{"jid": jid, "name": full or push or first or biz or ""}
            for jid, full, push, first, biz in rows]


def main(argv=None):
    p = argparse.ArgumentParser(description="Curate the WhatsApp MCP allowlist.")
    p.add_argument("--allowlist", default=DEFAULT_ALLOWLIST)
    p.add_argument("--db", default=DEFAULT_DB)
    p.add_argument("--contacts-db", default=DEFAULT_CONTACTS_DB)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("query")
    a = sub.add_parser("add"); a.add_argument("jid"); a.add_argument("label")
    r = sub.add_parser("remove"); r.add_argument("jid")
    sub.add_parser("list")
    args = p.parse_args(argv)

    if args.cmd == "search":
        seen = set()
        rows = search_db(args.db, args.query) + \
            search_contacts_db(args.contacts_db, args.query)
        for row in rows:
            if row["jid"] in seen:
                continue
            seen.add(row["jid"])
            print(f"{row['jid']}\t{row['name']}")
    elif args.cmd == "add":
        add_entry(args.allowlist, args.jid, args.label)
        print(f"Added {args.label} ({args.jid})")
    elif args.cmd == "remove":
        remove_entry(args.allowlist, args.jid)
        print(f"Removed {args.jid}")
    elif args.cmd == "list":
        for e in read_entries(args.allowlist):
            print(f"{e['jid']}\t{e.get('label','')}")


if __name__ == "__main__":
    main()
