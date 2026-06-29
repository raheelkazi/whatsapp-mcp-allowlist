# whatsapp-mcp-server/send_core.py
"""The single guarded send pipeline, shared by the MCP server and the dashboard."""
from allowlist import check_send, AllowlistError


def perform_send(recipient, body, *, allowlist, rate_limiter, read_only, send_fn, now):
    """read-only -> allowlist+mode -> rate-limit -> send_fn(jid, body).

    send_fn returns (success: bool, status: str). Returns {"success", "message"}.
    """
    if read_only:
        return {"success": False, "message": "sends disabled (read-only mode)"}
    try:
        jid = check_send(recipient, allowlist)
    except AllowlistError as e:
        return {"success": False, "message": str(e)}
    allowed, reason = rate_limiter.try_send(now)
    if not allowed:
        return {"success": False, "message": f"rate limited: {reason}"}
    success, status = send_fn(jid, body)
    return {"success": success, "message": status}
