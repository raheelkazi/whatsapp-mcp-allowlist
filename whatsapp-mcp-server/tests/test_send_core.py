# whatsapp-mcp-server/tests/test_send_core.py
from send_core import perform_send
from ratelimit import RateLimiter

ALLOW = {"111@s.whatsapp.net": {"label": "Mom", "mode": "read+send"}}
READONLY_CHAT = {"111@s.whatsapp.net": {"label": "Work", "mode": "read"}}


def _ok_send(jid, body):
    return (True, f"Message sent to {jid}")


def test_read_only_blocks_before_anything():
    calls = []
    r = perform_send("111", "hi", allowlist=ALLOW, rate_limiter=RateLimiter(0, 30),
                     read_only=True, send_fn=lambda j, b: calls.append(1) or (True, "x"),
                     now=100.0)
    assert r["success"] is False and "read-only mode" in r["message"]
    assert calls == []


def test_off_list_blocked():
    calls = []
    r = perform_send("999", "hi", allowlist=ALLOW, rate_limiter=RateLimiter(0, 30),
                     read_only=False, send_fn=lambda j, b: calls.append(1) or (True, "x"),
                     now=100.0)
    assert r["success"] is False and "allowlist" in r["message"]
    assert calls == []


def test_read_only_chat_blocked():
    r = perform_send("111", "hi", allowlist=READONLY_CHAT, rate_limiter=RateLimiter(0, 30),
                     read_only=False, send_fn=_ok_send, now=100.0)
    assert r["success"] is False and "read-only" in r["message"]


def test_rate_limited():
    rl = RateLimiter(min_interval_sec=3600, max_per_hour=30)
    first = perform_send("111", "a", allowlist=ALLOW, rate_limiter=rl, read_only=False,
                         send_fn=_ok_send, now=100.0)
    second = perform_send("111", "b", allowlist=ALLOW, rate_limiter=rl, read_only=False,
                          send_fn=_ok_send, now=101.0)
    assert first["success"] is True
    assert second["success"] is False and "rate limited" in second["message"]


def test_success_passes_normalized_jid_to_send_fn():
    seen = {}
    r = perform_send("111", "hi", allowlist=ALLOW, rate_limiter=RateLimiter(0, 30),
                     read_only=False,
                     send_fn=lambda j, b: (seen.update(jid=j, body=b) or (True, "sent")),
                     now=100.0)
    assert seen == {"jid": "111@s.whatsapp.net", "body": "hi"}
    assert r == {"success": True, "message": "sent"}
