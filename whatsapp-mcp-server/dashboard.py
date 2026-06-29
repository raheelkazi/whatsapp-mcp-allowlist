# whatsapp-mcp-server/dashboard.py
"""Localhost-only FastAPI dashboard backend. Reuses the allowlist/guard layer."""
import os
import socket

from fastapi import FastAPI

import ratelimit
from allowlist import load_allowlist

ALLOWLIST_PATH = os.environ.get(
    "WHATSAPP_ALLOWLIST_PATH",
    os.path.join(os.path.dirname(__file__), "allowed_chats.json"),
)
READ_ONLY = os.environ.get("WHATSAPP_READ_ONLY", "").strip().lower() in (
    "1", "true", "yes", "on",
)


def _bridge_reachable(host="localhost", port=8080, timeout=0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def create_app() -> FastAPI:
    app = FastAPI(title="WhatsApp Dashboard")
    allowlist = load_allowlist(ALLOWLIST_PATH)  # fail-closed at startup
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

    return app
