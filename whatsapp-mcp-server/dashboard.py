# whatsapp-mcp-server/dashboard.py
"""Localhost-only FastAPI dashboard backend. Reuses the allowlist/guard layer."""
import json
import os
import socket
import sqlite3
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import manage_allowlist
import ratelimit
from allowlist import load_allowlist, VALID_MODES
from audit import audit_path, log_event, classify
from send_core import perform_send
import intelligence
import dashcache
from whatsapp import list_messages as whatsapp_list_messages

BRIDGE_SEND_URL = os.environ.get("WHATSAPP_BRIDGE_SEND_URL", "http://localhost:8080/api/send")


def bridge_send(jid, body):
    try:
        resp = requests.post(BRIDGE_SEND_URL, json={"recipient": jid, "message": body}, timeout=10)
        ok = resp.status_code == 200
        return ok, (resp.text if not ok else f"Message sent to {jid}")
    except requests.RequestException as e:
        return False, f"bridge error: {e}"

ALLOWLIST_PATH = os.environ.get(
    "WHATSAPP_ALLOWLIST_PATH",
    os.path.join(os.path.dirname(__file__), "allowed_chats.json"),
)
READ_ONLY = os.environ.get("WHATSAPP_READ_ONLY", "").strip().lower() in (
    "1", "true", "yes", "on",
)
DB_PATH = os.environ.get(
    "WHATSAPP_DB",
    os.path.join(os.path.dirname(__file__), "..", "whatsapp-bridge", "store", "messages.db"),
)
CONTACTS_DB_PATH = os.environ.get(
    "WHATSAPP_CONTACTS_DB",
    os.path.join(os.path.dirname(__file__), "..", "whatsapp-bridge", "store", "whatsapp.db"),
)
DASHBOARD_CACHE = os.environ.get(
    "WHATSAPP_DASHBOARD_CACHE",
    os.path.join(os.path.dirname(__file__), "dashboard_cache.json"),
)


def _safe(fn, path, q):
    """Call fn(path, q) and return [] if the DB is missing or unreadable."""
    try:
        return fn(path, q)
    except sqlite3.Error:
        return []


def _bridge_reachable(host="localhost", port=8080, timeout=0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def create_app(send_fn=bridge_send, generators=None) -> FastAPI:
    app = FastAPI(title="WhatsApp Dashboard")
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    allowlist = load_allowlist(ALLOWLIST_PATH)  # fail-closed at startup
    # NOTE: each process (dashboard + MCP server) holds its own in-process rate
    # limiter, so running both concurrently can allow up to 2× the configured
    # send rate.  A shared limiter (e.g. via Redis or a socket) is future work.
    rate_limiter = ratelimit.from_env()
    app.state.allowlist = allowlist
    app.state.rate_limiter = rate_limiter

    @app.get("/api/status")
    def status():
        return {
            "bridge_reachable": _bridge_reachable(),
            "read_only": READ_ONLY,
            "rate_limit": {
                "min_interval_sec": rate_limiter.min_interval_sec,
                "max_per_hour": rate_limiter.max_per_hour,
            },
        }

    class AllowEntry(BaseModel):
        jid: str
        label: str
        mode: str = "read+send"

    def _reload():
        app.state.allowlist = load_allowlist(ALLOWLIST_PATH)

    @app.get("/api/allowlist")
    def list_allowlist():
        return [{"jid": jid, "label": v["label"], "mode": v["mode"]}
                for jid, v in app.state.allowlist.items()]

    @app.post("/api/allowlist")
    def add_allowlist(entry: AllowEntry):
        if entry.mode not in VALID_MODES:
            raise HTTPException(status_code=400, detail=f"mode must be one of {VALID_MODES}")
        manage_allowlist.add_entry(ALLOWLIST_PATH, entry.jid, entry.label, entry.mode)
        _reload()
        return {"ok": True}

    @app.delete("/api/allowlist/{jid:path}")
    def remove_allowlist(jid: str):
        manage_allowlist.remove_entry(ALLOWLIST_PATH, jid)
        _reload()
        return {"ok": True}

    @app.get("/api/contacts/search")
    def contacts_search(q: str):
        seen, out = set(), []
        for row in (_safe(manage_allowlist.search_db, DB_PATH, q)
                    + _safe(manage_allowlist.search_contacts_db, CONTACTS_DB_PATH, q)):
            if row["jid"] in seen:
                continue
            seen.add(row["jid"])
            out.append(row)
        return out

    @app.get("/api/activity")
    def activity(limit: int = 100):
        path = audit_path()
        if not os.path.exists(path):
            return []
        with open(path) as f:
            lines = f.read().splitlines()
        rows = []
        for line in reversed(lines):       # newest first
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(rows) >= limit:
                break
        return rows

    class SendBody(BaseModel):
        recipient: str
        message: str

    @app.post("/api/send")
    def send(body: SendBody):
        result = perform_send(body.recipient, body.message, allowlist=app.state.allowlist,
                              rate_limiter=app.state.rate_limiter, read_only=READ_ONLY,
                              send_fn=send_fn, now=time.time())
        decision, reason = classify(result)
        log_event({"tool": "dashboard_send", "target": body.recipient,
                   "decision": decision, "reason": reason})
        return result

    def _fetch(jid):
        out = whatsapp_list_messages(chat_jid=jid, include_context=False, limit=40)
        return out if isinstance(out, str) else ""

    def _get_generators():
        if generators is not None:
            return generators
        return intelligence.make_generators()  # may raise IntelligenceUnavailable

    def _section(name, compute, refresh):
        if not refresh:
            cached = dashcache.get_section(DASHBOARD_CACHE, name)
            if cached is not None:
                return {"items": cached["data"], "generated_at": cached["generated_at"],
                        "error": None}
        try:
            gen_text, gen_json = _get_generators()
        except intelligence.IntelligenceUnavailable as e:
            return {"items": [], "generated_at": None, "error": str(e) +
                    " — set ANTHROPIC_API_KEY"}
        data = compute(gen_text, gen_json)
        stored = dashcache.put_section(DASHBOARD_CACHE, name, data)
        return {"items": data, "generated_at": stored["generated_at"], "error": None}

    @app.get("/api/summaries")
    def summaries(refresh: int = 0):
        return _section("summaries",
                        lambda gt, gj: intelligence.summarize(app.state.allowlist, _fetch, gt),
                        refresh)

    @app.get("/api/suggestions")
    def suggestions(refresh: int = 0):
        return _section("suggestions",
                        lambda gt, gj: intelligence.suggest(app.state.allowlist, _fetch, gj),
                        refresh)

    @app.get("/api/reminders")
    def reminders_ep(refresh: int = 0):
        return _section("reminders",
                        lambda gt, gj: intelligence.reminders(app.state.allowlist, _fetch, gj),
                        refresh)

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
