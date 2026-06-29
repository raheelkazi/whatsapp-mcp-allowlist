# whatsapp-mcp-server/audit.py
"""Append-only audit log of every MCP tool call (reads, sends, and blocks).

One JSON line per call. Logging is best-effort: a write failure must never break
a tool call.
"""
import functools
import inspect
import json
import os
from datetime import datetime, timezone

# argument names, in priority order, that identify the "target" of a tool call
_TARGET_ARGS = ("recipient", "chat_jid", "jid", "message_id", "query")


def audit_path() -> str:
    return os.environ.get(
        "WHATSAPP_AUDIT_LOG", os.path.join(os.path.dirname(__file__), "audit.log")
    )


def log_event(event: dict, path: str | None = None) -> None:
    record = {"ts": datetime.now(timezone.utc).isoformat(), **event}
    try:
        with open(path or audit_path(), "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # best-effort: never break the tool call on a logging failure


def classify(result) -> tuple[str, str | None]:
    """Infer (decision, reason) from a tool's return value."""
    if isinstance(result, dict) and ("error" in result or result.get("success") is False):
        msg = str(result.get("error") or result.get("message") or "").lower()
        if "rate limit" in msg:
            reason = "rate_limited"
        elif "read-only mode" in msg:
            reason = "read_only_mode"
        elif "read-only" in msg:
            reason = "read_only"
        elif "allowlist" in msg:
            reason = "not_in_allowlist"
        else:
            reason = "error"
        return "denied", reason
    return "allowed", None


def audited(func):
    """Decorator: log each call of an MCP tool with its target and outcome."""
    sig = inspect.signature(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        try:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            params = bound.arguments
        except TypeError:
            params = {}
        target = next((params[k] for k in _TARGET_ARGS if params.get(k)), None)
        decision, reason = classify(result)
        log_event({"tool": func.__name__, "target": target,
                   "decision": decision, "reason": reason})
        return result

    return wrapper
